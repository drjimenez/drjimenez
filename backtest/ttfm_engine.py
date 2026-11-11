"""
ttfm_engine.py — Motor de señales + simulador barra a barra del Modelo Fractal (TTFM),
fiel a docs/SPEC.md y a pine/ttfm_strategy.pine.

Resumen de reglas (ver SPEC):
  * Las velas HTF se construyen a partir de las LTF (como el Pine con timeframe.change):
    C1 = penúltima HTF cerrada, C2 = última HTF cerrada, C3 = HTF en curso.
  * Setup alcista: C2.low < C1.low y C2.close > C1.low. Bajista: C2.high > C1.high y C2.close < C1.high.
    Si C2 cumple ambas (vela "outside" que barre los dos lados) el setup se considera ambiguo y se descarta.
  * CISD LTF (alcista): nivel = apertura de la primera vela de la serie de velas bajistas
    consecutivas más reciente; se confirma con el primer cierre por encima del nivel (el nivel se
    consume). Simétrico para bajista.
  * Orden de evaluación en cada vela LTF de C3: invalidación (low < C2.low en long) → expiración
    (barsInC3 > maxEntryBars, 1ª vela de C3 = 1; 0 = sin límite) → objetivo alcanzado antes del CISD → CISD.
  * En la vela de confirmación: entrada al cierre. SL = extremo de C2 ∓ slBufferATR·ATR14(LTF),
    TP = extremo opuesto de C2. Si RR < minRR la señal se omite pero el setup sigue activo
    (otro CISD posterior puede valer). Máximo un trade por setup HTF.
  * Si llega la señal válida con una posición ya abierta, la señal se consume sin entrar
    (igual que la estrategia Pine con el guard strategy.position_size == 0).
  * La 1ª vela HTF del histórico (posiblemente parcial) se descarta, como f_htfCandle del indicador.
  * Un trade por setup, una posición a la vez. SL primero si SL y TP en la misma vela.
  * Costes: comisión 0.04% por lado + slippage 0.02% por lado. Riesgo 1% del equity (compuesto).
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict

import numpy as np
import pandas as pd

PROFILES = {
    # nombre: (regla HTF, regla LTF)
    "intradia_4H_15m": ("4h", "15min"),
    "swing_1D_1H": ("1D", "1h"),
}


@dataclass
class Params:
    minRR: float = 1.0
    slBufferATR: float = 0.1
    atrLen: int = 14
    maxEntryBars: int = 12       # 0 = sin límite (toda la vela C3); 1ª vela de C3 = 1
    timeExitBars: int = 0        # 0 = sin salida por tiempo
    risk: float = 0.01           # 1% del equity
    commission: float = 0.0004   # 0.04% por lado
    slippage: float = 0.0002     # 0.02% por lado
    initial_capital: float = 10_000.0
    maxLeverage: float = 20.0    # tope de nocional/equity (evita tamaños absurdos con SL muy cortos)
    start: str | None = None     # filtro de fecha para entradas (UTC)
    end: str | None = None


def atr_rma(h, l, c, n):
    """ATR de Wilder (equivalente a ta.atr de Pine)."""
    prev_c = np.r_[np.nan, c[:-1]]
    tr = np.nanmax(np.vstack([h - l, np.abs(h - prev_c), np.abs(l - prev_c)]), axis=0)
    tr[0] = h[0] - l[0]
    out = np.full_like(tr, np.nan)
    if len(tr) < n:
        return out
    out[n - 1] = tr[:n].mean()
    a = 1.0 / n
    for i in range(n, len(tr)):
        out[i] = out[i - 1] + a * (tr[i] - out[i - 1])
    return out


def run(ltf: pd.DataFrame, htf_rule: str, params: Params | None = None, symbol: str = "",
        check: bool = True):
    """Simula la estrategia sobre un DataFrame LTF (index UTC = apertura de vela).

    Devuelve (trades: DataFrame, equity: Series indexada por cierre de vela LTF, signals: DataFrame).
    """
    p = params or Params()
    if ltf.empty:
        return pd.DataFrame(), pd.Series(dtype=float), pd.DataFrame()
    t = ltf.index
    ltf_delta = (t[1:] - t[:-1]).min()
    o, h, l, c = (ltf[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    atr = atr_rma(h, l, c, p.atrLen)
    htf_start = t.floor(htf_rule)
    htf_id = htf_start.asi8  # vela HTF a la que pertenece cada vela LTF (alineada a 00:00 UTC)
    n = len(ltf)
    t_start = pd.Timestamp(p.start, tz="UTC") if p.start else t[0]
    t_end = pd.Timestamp(p.end, tz="UTC") if p.end else t[-1] + ltf_delta

    # --- estado HTF (construcción manual, igual que el Pine) ---
    cur = None            # [o, h, l, c, id, start] vela HTF en formación
    started = False
    c2 = None             # última HTF cerrada
    c1 = None             # penúltima HTF cerrada
    # --- estado setup ---
    setup_dir = 0
    setup = {}
    bars_in_c3 = 0
    # --- estado CISD ---
    bull_level = np.nan   # apertura de la 1ª vela de la serie bajista más reciente
    bear_level = np.nan   # apertura de la 1ª vela de la serie alcista más reciente
    prev_bear = prev_bull = False
    # --- estado cuenta ---
    cash = p.initial_capital
    pos = None
    trades, signals = [], []
    eq = np.empty(n)

    def close_pos(i, raw_px, reason):
        nonlocal cash, pos
        d = pos["dir"]
        fill = raw_px * (1 - d * p.slippage)
        comm = p.commission * pos["qty"] * fill
        pnl = d * pos["qty"] * (fill - pos["entry_fill"]) - pos["comm_in"] - comm
        cash += d * pos["qty"] * (fill - pos["entry_fill"]) - comm  # comm_in ya descontada al entrar
        tr = dict(symbol=symbol, direction="long" if d == 1 else "short",
                  setup_time=pos["setup_time"], entry_time=pos["entry_time"], entry_price=pos["entry_price"],
                  entry_fill=pos["entry_fill"], sl=pos["sl"], tp=pos["tp"], qty=pos["qty"],
                  planned_rr=pos["rr"], exit_time=t[i] + ltf_delta, exit_price=raw_px, exit_fill=fill,
                  exit_reason=reason, exit_bar_low=l[i], exit_bar_high=h[i],
                  pnl=pnl, risk_usd=pos["risk_usd"], r_multiple=pnl / pos["risk_usd"],
                  equity_before=pos["equity_before"], equity_after=cash,
                  bars_held=i - pos["i"], lev_capped=pos["lev_capped"])
        trades.append(tr)
        pos = None

    for i in range(n):
        # ---------- 1) Construcción HTF ----------
        new_htf = cur is None or htf_id[i] != cur[4]
        if new_htf:
            if cur is not None:
                if started:   # la 1ª vela HTF observada puede ser parcial: se descarta (igual que el indicador)
                    c1, c2 = c2, cur
                started = True
            cur = [o[i], h[i], l[i], c[i], htf_id[i], htf_start[i]]
            bars_in_c3 = 0
            setup_dir = 0
            if c1 is not None and c2 is not None:
                bull = c2[2] < c1[2] and c2[3] > c1[2]
                bear = c2[1] > c1[1] and c2[3] < c1[1]
                if bull != bear:  # descarta ambiguas (barre ambos lados)
                    setup_dir = 1 if bull else -1
                    setup = dict(c2h=c2[1], c2l=c2[2], c2_start=c2[5], c1_start=c1[5], c3_start=htf_start[i],
                                 c3_first_bar=t[i])
        else:
            cur[1] = max(cur[1], h[i]); cur[2] = min(cur[2], l[i]); cur[3] = c[i]
        bars_in_c3 += 1

        # ---------- 2) Gestión de la posición abierta (órdenes stop/limit desde la vela siguiente) ----------
        if pos is not None and i > pos["i"]:
            d, sl, tp = pos["dir"], pos["sl"], pos["tp"]
            if d == 1:
                if o[i] <= sl:   close_pos(i, o[i], "SL_gap")
                elif l[i] <= sl: close_pos(i, sl, "SL")        # SL primero si ambos se tocan
                elif o[i] >= tp: close_pos(i, o[i], "TP_gap")
                elif h[i] >= tp: close_pos(i, tp, "TP")
            else:
                if o[i] >= sl:   close_pos(i, o[i], "SL_gap")
                elif h[i] >= sl: close_pos(i, sl, "SL")
                elif o[i] <= tp: close_pos(i, o[i], "TP_gap")
                elif l[i] <= tp: close_pos(i, tp, "TP")
            if pos is not None and p.timeExitBars > 0 and i - pos["i"] >= p.timeExitBars:
                close_pos(i, c[i], "TIME")

        # ---------- 3) CISD en LTF ----------
        bull_cisd = (not np.isnan(bull_level)) and c[i] > bull_level
        bear_cisd = (not np.isnan(bear_level)) and c[i] < bear_level
        if bull_cisd:
            bull_level = np.nan
        if bear_cisd:
            bear_level = np.nan
        is_bear, is_bull = c[i] < o[i], c[i] > o[i]
        if is_bear and not prev_bear:
            bull_level = o[i]
        if is_bull and not prev_bull:
            bear_level = o[i]
        prev_bear, prev_bull = is_bear, is_bull

        # ---------- 4) Lógica del setup durante C3 (mismo orden que f_setupEngine del indicador) ----------
        if setup_dir != 0:
            d = setup_dir
            ext = setup["c2l"] if d == 1 else setup["c2h"]   # extremo barrido (SL)
            tgt = setup["c2h"] if d == 1 else setup["c2l"]   # objetivo (TP)
            broke = l[i] < ext if d == 1 else h[i] > ext
            reached = h[i] >= tgt if d == 1 else l[i] <= tgt
            if broke:                                                    # 1) invalidación
                setup_dir = 0
            elif p.maxEntryBars > 0 and bars_in_c3 > p.maxEntryBars:     # 2) expiración
                setup_dir = 0
            elif reached:                                                # 3) objetivo antes del CISD
                setup_dir = 0
            elif bull_cisd if d == 1 else bear_cisd:                     # 4) CISD
                entry = c[i]
                sl = ext - d * p.slBufferATR * atr[i] if not np.isnan(atr[i]) else np.nan
                tp = tgt
                dist = d * (entry - sl)
                rr = d * (tp - entry) / dist if dist > 0 else np.nan
                ok = bool(not np.isnan(rr) and rr >= p.minRR)
                in_window = t_start <= t[i] < t_end
                sig = dict(symbol=symbol, time=t[i], close_time=t[i] + ltf_delta, dir=d, entry=entry, sl=sl,
                           tp=tp, rr=rr, taken=ok, entered=bool(ok and pos is None and in_window), **setup)
                signals.append(sig)
                if ok:
                    setup_dir = 0   # señal emitida: un solo trade por setup HTF
                # si R:R < minRR la señal se omite y el setup sigue activo (esperando otro CISD)
                if sig["entered"]:
                    equity = cash
                    risk_usd = equity * p.risk
                    qty = risk_usd / dist
                    capped = False
                    if qty * entry > p.maxLeverage * equity:
                        qty = p.maxLeverage * equity / entry
                        capped = True
                    fill = entry * (1 + d * p.slippage)
                    comm_in = p.commission * qty * fill
                    cash -= comm_in
                    pos = dict(dir=d, i=i, qty=qty, entry_price=entry, entry_fill=fill, sl=sl, tp=tp, rr=rr,
                               comm_in=comm_in, risk_usd=risk_usd, equity_before=equity,
                               entry_time=t[i] + ltf_delta, setup_time=setup["c3_start"], lev_capped=capped)

        # ---------- 5) Equity mark-to-market al cierre ----------
        eq[i] = cash + (pos["dir"] * pos["qty"] * (c[i] - pos["entry_fill"]) if pos else 0.0)

    if pos is not None:
        close_pos(n - 1, c[n - 1], "EOD")
        eq[n - 1] = cash

    trades = pd.DataFrame(trades)
    signals = pd.DataFrame(signals)
    equity = pd.Series(eq, index=t + ltf_delta, name=symbol)
    if check:
        sanity_checks(ltf, htf_rule, trades, signals, ltf_delta)
    return trades, equity, signals


def sanity_checks(ltf, htf_rule, trades, signals, ltf_delta):
    """Asserts de no look-ahead y coherencia de precios."""
    if signals.empty:
        return
    htf = ltf.resample(htf_rule, origin="epoch", label="left", closed="left").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last"}).dropna()
    htf_len = pd.Timedelta(htf_rule)
    for s in signals.itertuples():
        c2_start, c3_start = s.c2_start, s.c3_start
        # C2 y C1 ya cerradas antes de la señal (no look-ahead)
        assert c2_start + htf_len <= c3_start <= s.time, "C2 no cerrada al evaluar la señal"
        assert s.c1_start < c2_start and c3_start <= s.c3_first_bar
        # La vela de confirmación pertenece a C3 y cierra dentro de C3
        assert s.close_time <= c3_start + htf_len, "Entrada fuera de C3"
        # Los extremos de C2 coinciden con un resample independiente
        assert np.isclose(htf.loc[c2_start, "high"], s.c2h) and np.isclose(htf.loc[c2_start, "low"], s.c2l)
        # Precio de entrada = cierre de la vela de confirmación
        assert np.isclose(ltf.loc[s.time, "close"], s.entry)
    if trades.empty:
        return
    for tr in trades.itertuples():
        assert tr.entry_time < tr.exit_time or tr.exit_reason == "EOD"
        assert tr.exit_bar_low - 1e-9 <= tr.exit_price <= tr.exit_bar_high + 1e-9, "Salida fuera de rango"
        bar = ltf.loc[tr.entry_time - ltf_delta]
        assert bar.low - 1e-9 <= tr.entry_price <= bar.high + 1e-9
        if tr.direction == "long":
            assert tr.sl < tr.entry_price < tr.tp
        else:
            assert tr.tp < tr.entry_price < tr.sl
        if tr.exit_reason == "SL":
            assert tr.r_multiple < 0
    # no hay solapamiento de posiciones
    if len(trades) > 1:
        assert (trades.entry_time.iloc[1:].values >= trades.exit_time.iloc[:-1].values).all(), "Posiciones solapadas"
