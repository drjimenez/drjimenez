"""
engine.py — Extracción de eventos ORB y simulación de reglas con niveles Fibonacci.

Definiciones (todas en velas de 1 minuto):

* Rango de apertura (OR): máximo (H) y mínimo (L) de las N primeras velas desde la apertura
  local de la sesión. R = H − L.
* Ruptura: la PRIMERA vela posterior al OR cuyo CIERRE queda por encima de H (alcista) o por
  debajo de L (bajista), dentro del horizonte de la sesión. Si no hay cierre fuera: 'none'.
* Coordenada normalizada x (orientada en la dirección de la ruptura):
      ruptura alcista: x = (precio − H) / R        ruptura bajista: x = (L − precio) / R
  x > 0 es extensión a favor; x = 0 es el nivel roto; x = −0.5 la mitad del rango; x = −1 el
  extremo opuesto. Así, los retrocesos Fibonacci son x = −nivel y las extensiones x = +nivel.
* Retroceso a un nivel L_f: alguna vela posterior a la de ruptura tiene x_adverso ≤ −L_f.
* Extensión E: alguna vela posterior a la de ruptura tiene x_favorable ≥ E.

Para cada evento se guardan los minutos (desde la vela de ruptura) hasta el primer toque de
cada nivel de retroceso y de extensión. Con esas columnas se puede calcular en la base de datos
cualquier probabilidad del tipo "¿llega a la extensión E antes de retroceder al nivel F?".
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

import config as C


def _lvl(x: float) -> str:
    return f"{int(round(x * 1000)):04d}"


@dataclass
class Path:
    """Trayectoria normalizada tras la vela de ruptura (excluida)."""
    fav: np.ndarray     # extremo favorable (x del high en largo / del low en corto)
    adv: np.ndarray     # extremo adverso
    close: np.ndarray   # cierre
    break_x: float      # x del cierre de la vela de ruptura (precio de entrada 'break')
    price: float        # precio de referencia (para convertir costes en bp a unidades de R)
    range_pts: float


def session_days(session: str, start: str | None = None, end: str | None = None):
    hol = C.HOLIDAYS.get(session, set())
    d = date.fromisoformat(start or C.START)
    e = date.fromisoformat(end or C.END)
    while d <= e:
        if d.weekday() < 5 and d.isoformat() not in hol:
            yield d
        d += timedelta(days=1)


def _utc_minute(d: date, hhmm: str, tz: str) -> np.datetime64:
    hh, mm = map(int, hhmm.split(":"))
    loc = datetime.combine(d, time(hh, mm), tzinfo=ZoneInfo(tz))
    return np.datetime64(loc.astimezone(ZoneInfo("UTC")).replace(tzinfo=None), "m")


def _first(mask: np.ndarray) -> int:
    idx = np.flatnonzero(mask)
    return int(idx[0]) if idx.size else -1


def _arrays(bars: pd.DataFrame):
    t = bars.index.tz_convert("UTC").tz_localize(None).values.astype("datetime64[m]")
    return (t, bars["open"].to_numpy(float), bars["high"].to_numpy(float),
            bars["low"].to_numpy(float), bars["close"].to_numpy(float))


def classify_trend(net: float, rng: float) -> tuple[str, float]:
    """alza / baja / rango según la eficiencia net/rango de la ventana previa."""
    if not np.isfinite(net) or rng <= 0:
        return "n/d", np.nan
    eff = net / rng
    if eff >= C.TREND_EFF:
        return "alza", eff
    if eff <= -C.TREND_EFF:
        return "baja", eff
    return "rango", eff


def ny_daily(bars: pd.DataFrame) -> pd.DataFrame:
    """
    Tabla diaria de la sesión de contado de Nueva York (09:30-16:00 NY): apertura, cierre, máximo,
    mínimo, cierre anterior, gap y contexto diario (tendencia según SMA20 de los cierres previos).
    """
    t, o, h, lo, c = _arrays(bars)
    sc = C.SESSIONS["NewYork"]
    rows = []
    for d in session_days("NewYork"):
        i0 = int(np.searchsorted(t, _utc_minute(d, "09:30", sc["tz"])))
        i1 = int(np.searchsorted(t, _utc_minute(d, "16:00", sc["tz"])))
        if i1 - i0 < 300:
            continue
        rows.append({"date": d.isoformat(), "ny_open": o[i0], "ny_close": c[i1 - 1],
                     "ny_high": h[i0:i1].max(), "ny_low": lo[i0:i1].min(), "i0": i0, "i1": i1})
    df = pd.DataFrame(rows).set_index("date")
    df["prev_close"] = df.ny_close.shift(1)
    df["prev_high"] = df.ny_high.shift(1)
    df["prev_low"] = df.ny_low.shift(1)
    sma = df.ny_close.rolling(20).mean()
    slope = sma - sma.shift(5)
    # Contexto conocido ANTES de la apertura del día: usa sólo cierres hasta el día anterior
    prev_sma, prev_slope = sma.shift(1), slope.shift(1)
    df["daily_trend"] = np.where(prev_sma.isna(), "n/d",
                         np.where((df.prev_close > prev_sma) & (prev_slope > 0), "alcista",
                         np.where((df.prev_close < prev_sma) & (prev_slope < 0), "bajista", "lateral")))
    df["adr20"] = (df.ny_high - df.ny_low).rolling(20).mean().shift(1)   # rango medio previo
    df["prev_day_dir"] = np.sign(df.ny_close - df.ny_open).shift(1).map({1.0: "alcista", -1.0: "bajista", 0.0: "plano"})
    return df


def extract_events(symbol: str, bars: pd.DataFrame, daily: pd.DataFrame | None = None):
    """Devuelve (DataFrame de eventos, dict event_id -> Path)."""
    t, o, h, lo, c = _arrays(bars)
    daily = ny_daily(bars) if daily is None else daily
    rows, paths = [], {}
    for session, sc in C.SESSIONS.items():
        for d in session_days(session):
            t0 = _utc_minute(d, sc["open"], sc["tz"])
            t_end = _utc_minute(d, sc["horizon_end"], sc["tz"])
            i0 = int(np.searchsorted(t, t0))
            i_end = int(np.searchsorted(t, t_end))
            for n in C.OR_MINUTES:
                i_or = int(np.searchsorted(t, t0 + np.timedelta64(n, "m")))
                # Rango con datos suficientes (Dukascopy omite minutos sin cotización)
                if i_or - i0 < max(3, int(0.8 * n)) or i_end - i_or < 30 or t[i0] >= t0 + np.timedelta64(n, "m"):
                    continue
                H, L = h[i0:i_or].max(), lo[i0:i_or].min()
                R = H - L
                if R <= 0:
                    continue
                ph, pl, pc = h[i_or:i_end], lo[i_or:i_end], c[i_or:i_end]
                pt = t[i_or:i_end]
                k_up, k_dn = _first(pc > H), _first(pc < L)
                touch_up, touch_dn = _first(ph > H), _first(pl < L)
                if touch_up < 0 and touch_dn < 0:
                    first_touch = "none"
                elif touch_dn < 0 or (0 <= touch_up < touch_dn):
                    first_touch = "up"
                elif touch_up < 0 or touch_dn < touch_up:
                    first_touch = "down"
                else:
                    first_touch = "both"   # misma vela toca ambos lados

                ev = {
                    "event_id": f"{symbol}|{d.isoformat()}|{session}|{n}",
                    "symbol": symbol, "date": d.isoformat(), "session": session, "or_min": n,
                    "weekday": d.strftime("%a"), "month": d.strftime("%Y-%m"),
                    "sample": "IS" if d.isoformat() <= C.IS_END else "OOS",
                    "open_price": o[i0], "or_high": H, "or_low": L, "or_range": R,
                    "or_range_bp": R / o[i0] * 1e4,
                    "first_touch": first_touch,
                }
                # Contexto previo a la apertura (ventana configurable por sesión)
                ip = int(np.searchsorted(t, _utc_minute(d, sc["pre_start"], sc["tz"])))
                if i0 - ip >= 30:
                    net = c[i0 - 1] - o[ip]
                    rng = h[ip:i0].max() - lo[ip:i0].min()
                    ev["pre_trend"], ev["pre_eff"] = classify_trend(net, rng)
                    ev["pre_range_bp"] = rng / o[i0] * 1e4
                    ev["pre_range_vs_or"] = rng / R
                else:
                    ev["pre_trend"] = "n/d"
                dk = d.isoformat()
                if dk in daily.index:
                    dr = daily.loc[dk]
                    ev["daily_trend"] = dr.daily_trend
                    ev["prev_day_dir"] = dr.prev_day_dir
                    ev["or_vs_adr"] = R / dr.adr20 if dr.adr20 > 0 else np.nan
                else:
                    ev["daily_trend"] = "n/d"
                if k_up < 0 and k_dn < 0:
                    ev.update({"break_dir": "none"})
                    rows.append(ev)
                    continue
                if k_dn < 0 or (0 <= k_up < k_dn):
                    k, sgn, lvl = k_up, 1.0, H
                else:
                    k, sgn, lvl = k_dn, -1.0, L
                if sgn > 0:
                    fav, adv, cl = (ph - H) / R, (pl - H) / R, (pc - H) / R
                else:
                    fav, adv, cl = (L - pl) / R, (L - ph) / R, (L - pc) / R
                bx = cl[k]
                f, a, cc = fav[k + 1:], adv[k + 1:], cl[k + 1:]
                ev.update({
                    "break_dir": "up" if sgn > 0 else "down",
                    "break_time_utc": str(pt[k]),
                    "min_to_break": k + 1,                 # minutos tras cerrar el OR
                    "break_x": bx,
                    "max_ext": float(f.max()) if f.size else np.nan,
                    "max_retrace": float(-a.min()) if a.size else np.nan,
                    "close_x": float(cc[-1]) if cc.size else float(bx),
                })
                if f.size:
                    ipk = int(np.argmax(f))
                    ev["retrace_before_peak"] = float(-a[: ipk + 1].min())
                    ev["min_to_peak"] = ipk + 1
                    ev["retest"] = bool((a <= 0).any())
                    # Ruptura fallida: cierre más allá del extremo opuesto
                    ev["opposite_break"] = bool((cc < -1).any())
                    for e in C.EXT_LEVELS:
                        j = _first(f >= e)
                        ev[f"t_ext_{_lvl(e)}"] = j + 1 if j >= 0 else np.nan
                    for r in C.RETRACE_LEVELS:
                        j = _first(a <= -r)
                        ev[f"t_ret_{_lvl(r)}"] = j + 1 if j >= 0 else np.nan
                    ev.update(scenarios(f, a, cc))
                rows.append(ev)
                paths[ev["event_id"]] = Path(f, a, cc, float(bx), float(lvl), float(R))
    return pd.DataFrame(rows), paths


def scenarios(f: np.ndarray, a: np.ndarray, cc: np.ndarray) -> dict:
    """Escenario con cada umbral de continuación (1.272 / 1.618 / 2.0)."""
    out = scenario(f, a, cc, C.SCEN_EXT)
    for e in C.SCEN_EXT_ALT:
        alt = scenario(f, a, cc, e)
        out[f"scenario_{C.EXT_LABEL[e].replace('.', '')}"] = alt["scenario"]
    return out


def scenario(f: np.ndarray, a: np.ndarray, cc: np.ndarray, e1: float | None = None) -> dict:
    """
    Árbol de escenarios tras la primera ruptura (coordenadas x orientadas a la ruptura):

      directa         nunca vuelve al nivel roto: continúa sin retest
      retest_continua vuelve al nivel roto y después alcanza la extensión 1.272 a favor de la
                      primera ruptura ANTES de tocar el extremo opuesto
      giro_continua   vuelve, llega al extremo opuesto, lo rompe y alcanza la extensión 1.272 del
                      otro lado (x ≤ −1.272): la ruptura falla y el precio continúa hacia el otro lado
      giro_rechazo    llega al extremo opuesto pero no se extiende 0.272 R más allá
      rango           vuelve al nivel roto pero no alcanza ni 1.272 ni el extremo opuesto
    Empates en la misma vela se resuelven a favor del extremo opuesto (conservador).
    """
    e1 = C.SCEN_EXT if e1 is None else e1
    jr = _first(a <= 0)
    out = {"scenario": None, "min_to_retest": np.nan, "min_to_scenario": np.nan,
           "ext_after_retest": np.nan}
    if jr < 0:
        out["scenario"] = "directa"
        j = _first(f >= e1)
        out["min_to_scenario"] = j + 1 if j >= 0 else np.nan
        return out
    out["min_to_retest"] = jr + 1
    jo = _first(a[jr:] <= -1)
    je = _first(f[jr + 1:] >= e1)
    jo = jo + jr if jo >= 0 else -1
    je = je + jr + 1 if je >= 0 else -1
    if je >= 0:
        out["ext_after_retest"] = float(f[jr + 1:].max())
    if je >= 0 and (jo < 0 or je < jo):
        out["scenario"], out["min_to_scenario"] = "retest_continua", je + 1
    elif jo >= 0:
        jx = _first(a[jo:] <= -(1 + e1))
        if jx >= 0:
            out["scenario"], out["min_to_scenario"] = "giro_continua", jo + jx + 1
        else:
            out["scenario"], out["min_to_scenario"] = "giro_rechazo", jo + 1
    else:
        out["scenario"] = "rango"
    return out


# --------------------------------------------------------------------------------------------
# Gap Fibonacci: cierre NY del día anterior -> apertura NY del día
# --------------------------------------------------------------------------------------------

def extract_gaps(symbol: str, bars: pd.DataFrame, daily: pd.DataFrame | None = None) -> pd.DataFrame:
    """
    Fibonacci trazado entre el CIERRE de Nueva York del día anterior (16:00) y la APERTURA de
    Nueva York del día (09:30). Coordenada p = (apertura − precio) / gap:
        p = 0  apertura;  p = 1  cierre anterior (gap cerrado);  0 < p < 1  retroceso del gap
        p > 1  el precio supera el cierre anterior (extensión 1.272 / 1.618 del gap)
        p < 0  el precio se aleja del cierre anterior a favor del gap (−0.272, −0.618, −1)
    Para cada nivel se guarda el minuto (desde las 09:30) del primer toque durante la sesión.
    """
    t, o, h, lo, c = _arrays(bars)
    daily = ny_daily(bars) if daily is None else daily
    rows = []
    for dk, dr in daily.iterrows():
        if not np.isfinite(dr.prev_close):
            continue
        gap = dr.ny_open - dr.prev_close
        i0, i1 = int(dr.i0), int(dr.i1)
        adr = dr.adr20
        row = {"event_id": f"{symbol}|{dk}|gap", "symbol": symbol, "date": dk,
               "weekday": date.fromisoformat(dk).strftime("%a"), "year": dk[:4],
               "sample": "IS" if dk <= C.IS_END else "OOS",
               "prev_close": dr.prev_close, "ny_open": dr.ny_open, "ny_close": dr.ny_close,
               "gap": gap, "gap_bp": gap / dr.prev_close * 1e4,
               "gap_vs_adr": abs(gap) / adr if adr > 0 else np.nan,
               "daily_trend": dr.daily_trend, "prev_day_dir": dr.prev_day_dir,
               "open_vs_prev_range": ("sobre máximo previo" if dr.ny_open > dr.prev_high else
                                      "bajo mínimo previo" if dr.ny_open < dr.prev_low else "dentro rango previo")}
        rel = row["gap_vs_adr"]
        if not np.isfinite(rel) or rel < C.GAP_FLAT_ADR:
            row["gap_dir"] = "plano"
            rows.append(row)
            continue
        row["gap_dir"] = "alcista" if gap > 0 else "bajista"
        row["gap_size"] = ("pequeño" if rel < 0.25 else "medio" if rel < 0.5 else "grande")
        if gap > 0:
            pf, pa = (dr.ny_open - lo[i0:i1]) / gap, (dr.ny_open - h[i0:i1]) / gap
        else:
            pf, pa = (dr.ny_open - h[i0:i1]) / gap, (dr.ny_open - lo[i0:i1]) / gap
        pc = (dr.ny_open - c[i0:i1]) / gap
        row.update({"max_fill": float(pf.max()), "max_away": float(-pa.min()), "close_p": float(pc[-1])})
        for lv in C.GAP_FILL_LEVELS:
            j = _first(pf >= lv)
            row[f"t_fill_{_lvl(lv)}"] = j + 1 if j >= 0 else np.nan
        for lv in C.GAP_AWAY_LEVELS:
            j = _first(pa <= -lv)
            row[f"t_away_{_lvl(lv)}"] = j + 1 if j >= 0 else np.nan
        rows.append(row)
    return pd.DataFrame(rows)


def gap_path(bars: pd.DataFrame, i0: int, i1: int, ny_open: float, gap: float) -> np.ndarray:
    """Trayectoria de cierres en coordenadas p del gap (para gráficos de patrón)."""
    return (ny_open - bars["close"].to_numpy(float)[i0:i1]) / gap


# --------------------------------------------------------------------------------------------
# Simulación de reglas
# --------------------------------------------------------------------------------------------

def simulate(p: Path, entry, stop: float, target: float, cost_bp: float = C.COST_BP_PER_SIDE):
    """
    Simula una operación a favor de la ruptura sobre la trayectoria normalizada.

    entry  : 'break' -> entrada al cierre de la vela de ruptura (x = break_x)
             float   -> orden límite en el retroceso x = −entry, activa desde la vela siguiente
                        a la ruptura y cancelada si el objetivo se alcanza antes del fill.
    stop   : nivel de retroceso (x = −stop).    target: extensión (x = +target).
    Supuestos conservadores: si en una misma vela se tocan stop y objetivo, cuenta el stop; en
    la vela del fill sólo se evalúa el stop. Sin salida: cierre al final del horizonte.
    Devuelve dict o None si no hay operación.
    """
    sx, tx = -stop, target
    n = p.fav.size
    if n == 0:
        return None
    if entry == "break":
        ex, i = p.break_x, 0
        if ex <= sx or ex >= tx:
            return None
        fill_bar_check_target = True
    else:
        ex = -float(entry)
        if ex <= sx:
            return None
        hit_fill = p.adv <= ex
        hit_tgt = p.fav >= tx
        jf, jt = _first(hit_fill), _first(hit_tgt)
        if jf < 0 or (0 <= jt < jf):
            return None          # nunca se llena o el objetivo llega antes (orden cancelada)
        i = jf
        fill_bar_check_target = False
    risk = ex - sx
    stop_hit = p.adv[i:] <= sx
    tgt_hit = p.fav[i:] >= tx
    if not fill_bar_check_target:
        tgt_hit = tgt_hit.copy()
        tgt_hit[0] = False
    js, jt = _first(stop_hit), _first(tgt_hit)
    if js >= 0 and (jt < 0 or js <= jt):
        out, xx, j = "stop", sx, js
    elif jt >= 0:
        out, xx, j = "target", tx, jt
    else:
        out, xx, j = "time", float(p.close[-1]), n - 1 - i
    r_gross = (xx - ex) / risk
    # coste ida y vuelta en unidades de x, convertido a R
    cost_x = 2 * cost_bp / 1e4 * p.price / p.range_pts
    return {"outcome": out, "r_gross": r_gross, "r_net": r_gross - cost_x / risk,
            "entry_x": ex, "risk_x": risk, "bars_in_trade": j + 1}


def flip(p: Path) -> Path:
    """Trayectoria vista desde el lado contrario (para el modelo de reversión / fade)."""
    return Path(-p.adv, -p.fav, -p.close, -p.break_x, p.price, p.range_pts)
