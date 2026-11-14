"""
backtest_plan.py — Agente de estrategia: pautas y backtest de un plan concreto en una cuenta fondeada.

Reglas del plan (las del usuario):
  1. Sesiones de Londres (08:00) y Nueva York (09:30), rango de apertura de 15 minutos.
  2. Cuenta fondeada de 50.000 $.
  3. Tras la ruptura (cierre fuera del rango), esperar a que el precio retroceda al 50 % del rango;
     entrar cuando el precio vuelve a pasar por el 0,382 a favor de la ruptura (orden stop).
  4. Stop en el extremo opuesto del rango. Objetivos: la mitad en la extensión 1,618 y la otra
     mitad en 2,0.
  5. Al llegar a 2,0 se cierra todo. Si no se llega a ningún nivel, se cierra al final de la sesión
     (12:00 Londres, 16:00 Nueva York).
  Riesgo: 2 % de la cuenta por operación (lo pedido) con pérdida máxima diaria de 400 $.

Supuestos de la simulación (velas de 1 minuto, conservadores):
  * La entrada sólo puede llenarse en una vela POSTERIOR a la que toca el 50 %.
  * Si el precio toca el extremo opuesto antes de entrar, el plan se cancela ese día.
  * En la vela de entrada sólo cuenta el stop; si en una vela se tocan stop y objetivo, cuenta el stop.
  * Costes por lado en puntos (spread + comisión): config COST_PTS.
  * Límite diario: antes de cada operación, el riesgo se recorta a lo que queda del límite diario
    (y si no queda nada, no se opera). Londres va antes que Nueva York.

Salidas en results/<fuente>/backtest_plan/: operaciones (diario), resumen por política de riesgo,
ejemplos reales paso a paso, curva de capital, plantilla de registro, PAUTAS_BACKTEST.md y el PDF.
"""
from __future__ import annotations

import math
import os
import sys
from dataclasses import dataclass

import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config as C  # noqa: E402
import database as db  # noqa: E402
import engine as E  # noqa: E402
from agents import style  # noqa: E402

ACCOUNT = 50_000.0
RISK_PCT = 0.02
DAILY_MAX_LOSS = 400.0
OR_MIN = 15
ENTRY_TRIGGER = 0.5      # retroceso que hay que tocar primero
ENTRY_LEVEL = 0.382      # nivel de entrada (orden stop al volver a favor)
STOP_LEVEL = 1.0         # extremo opuesto
TP1, TP2 = 0.618, 1.0    # extensiones 1,618 y 2,0 (x desde el nivel roto)
COST_PTS = {"NAS100": 1.0, "US500": 0.25}   # spread + comisión por lado, en puntos del índice

# Valor por punto de cada unidad de tamaño
#   CFD: 1 lote = 1 $ por punto (lo habitual en NAS100/US500 de las cuentas fondeadas en MT4/MT5);
#        1 micro lote = 0,01 lotes = 0,01 $ por punto
#   Futuros micro: MNQ (Nasdaq) 2 $ por punto · MES (S&P 500) 5 $ por punto
UNITS = {
    "cfd": {"NAS100": 0.01, "US500": 0.01, "nombre": "micro lotes CFD (0,01 lote)"},
    "micro_fut": {"NAS100": 2.0, "US500": 5.0, "nombre": "contratos micro de futuros (MNQ / MES)"},
}

# Reglas típicas de una cuenta fondeada de 50K para la prueba de supervivencia (ajustables):
PROP_TARGET = 3_000.0      # objetivo de beneficio (6 %)
PROP_MAX_LOSS = 2_500.0    # pérdida máxima total (5 %, estática)

POLICIES = {
    "2 % por operación (lo pedido)": {"risk": ACCOUNT * RISK_PCT, "daily_cap": False},
    "2 % recortado al límite diario de 400 $": {"risk": ACCOUNT * RISK_PCT, "daily_cap": True},
    "200 $ por operación (0,4 %) con límite diario": {"risk": 200.0, "daily_cap": True},
}


@dataclass
class Trade:
    symbol: str
    date: str
    session: str
    direction: str
    or_high: float
    or_low: float
    rng: float
    t_break: pd.Timestamp
    t_50: pd.Timestamp
    t_entry: pd.Timestamp
    entry: float
    stop: float
    tp1: float
    tp2: float
    outcome: str            # "TP1+TP2", "TP1+stop", "TP1+cierre", "stop", "cierre"
    t_exit1: pd.Timestamp | None
    exit1: float
    t_exit2: pd.Timestamp | None
    exit2: float
    stop_pts: float
    r_gross: float          # resultado en R (riesgo = distancia entrada-stop), sin costes
    cost_r: float           # costes en R (ida y vuelta, ambas mitades)


def _first(m):
    i = np.flatnonzero(m)
    return int(i[0]) if i.size else -1


def simulate_day(symbol: str, bars: pd.DataFrame, ev: pd.Series) -> Trade | None:
    """Aplica las reglas del plan a una ruptura (precios reales vela a vela)."""
    sc = C.SESSIONS[ev.session]
    d = pd.Timestamp(ev.date).date()
    t_end = pd.Timestamp(E._utc_minute(d, sc["horizon_end"], sc["tz"])).tz_localize("UTC")
    t_brk = pd.Timestamp(ev.break_time_utc).tz_localize("UTC")
    seg = bars.loc[t_brk + pd.Timedelta(minutes=1): t_end - pd.Timedelta(minutes=1)]
    if seg.empty:
        return None
    H, L, R = ev.or_high, ev.or_low, ev.or_high - ev.or_low
    up = ev.break_dir == "up"
    s = 1 if up else -1
    lvl = lambda x: (H + x * R) if up else (L - x * R)   # noqa: E731  x desde el nivel roto
    p50, pentry, pstop = lvl(-ENTRY_TRIGGER), lvl(-ENTRY_LEVEL), lvl(-STOP_LEVEL)
    ptp1, ptp2 = lvl(TP1), lvl(TP2)
    hi, lo, cl = seg.high.to_numpy(), seg.low.to_numpy(), seg.close.to_numpy()
    adv = lo if up else hi          # extremo en contra
    fav = hi if up else lo          # extremo a favor
    a_le = (lambda v, p: v <= p) if up else (lambda v, p: v >= p)   # noqa: E731  llega en contra
    f_ge = (lambda v, p: v >= p) if up else (lambda v, p: v <= p)   # noqa: E731  llega a favor

    j50 = _first(a_le(adv, p50))
    if j50 < 0:
        return None
    jstop_pre = _first(a_le(adv, pstop))
    jf = _first(f_ge(fav[j50 + 1:], pentry))
    if jf < 0:
        return None
    jf += j50 + 1
    if 0 <= jstop_pre < jf:          # tocó el extremo opuesto antes de entrar: plan cancelado
        return None
    # tras la entrada
    a2, f2 = adv[jf:], fav[jf:]
    stop_hit = a_le(a2, pstop)
    t1 = f_ge(f2, ptp1)
    t2 = f_ge(f2, ptp2)
    t1[0] = False
    t2[0] = False
    js, j1 = _first(stop_hit), _first(t1)
    risk = abs(pentry - pstop)
    times = seg.index
    if js >= 0 and (j1 < 0 or js <= j1):
        out, e1, te1, e2, te2 = "stop", pstop, times[jf + js], pstop, times[jf + js]
    elif j1 >= 0:
        e1, te1 = ptp1, times[jf + j1]
        # segunda mitad desde la vela de TP1 (en esa vela, si toca stop y 2.0, stop)
        a3, f3 = a2[j1:], f2[j1:]
        js2, j2 = _first(a_le(a3, pstop)), _first(f_ge(f3, ptp2))
        if js2 >= 0 and (j2 < 0 or js2 <= j2):
            out, e2, te2 = "TP1+stop", pstop, times[jf + j1 + js2]
        elif j2 >= 0:
            out, e2, te2 = "TP1+TP2", ptp2, times[jf + j1 + j2]
        else:
            out, e2, te2 = "TP1+cierre", float(cl[-1]), times[-1]
    else:
        out, e1, te1, e2, te2 = "cierre", float(cl[-1]), times[-1], float(cl[-1]), times[-1]
    r = 0.5 * s * (e1 - pentry) / risk + 0.5 * s * (e2 - pentry) / risk
    cost = 2 * COST_PTS[symbol] / risk          # entrada + salida, en puntos sobre el riesgo
    return Trade(symbol, ev.date, ev.session, "alcista" if up else "bajista", H, L, R, t_brk, times[j50],
                 times[jf], pentry, pstop, ptp1, ptp2, out, te1, e1, te2, e2, risk, r, cost)


def size_units(risk_usd: float, stop_pts: float, value_per_pt: float) -> int:
    return int(math.floor(risk_usd / (stop_pts * value_per_pt))) if stop_pts > 0 else 0


def apply_policy(tr: pd.DataFrame, risk: float, daily_cap: bool, unit: str) -> pd.DataFrame:
    """Tamaño (unidades enteras) y P&L en $ con la política de riesgo y el límite diario."""
    rows = []
    for (sym, day), g in tr.sort_values(["t_entry"]).groupby(["symbol", "date"], sort=True):
        day_pl = 0.0
        for _, t in g.iterrows():
            allow = risk
            if daily_cap:
                allow = min(risk, DAILY_MAX_LOSS + day_pl)   # lo que queda del límite (day_pl < 0 si pierde)
            vpp = UNITS[unit][sym]
            # el coste también cuenta para no pasar el límite
            per_unit_loss = (t.stop_pts + 2 * COST_PTS[sym]) * vpp
            n = int(math.floor(allow / per_unit_loss)) if allow > 0 else 0
            if n <= 0:
                rows.append({**t.to_dict(), "unidades": 0, "riesgo_usd": 0.0, "pl_usd": 0.0, "operada": False,
                             "pl_dia_acumulado": round(day_pl, 2)})
                continue
            pl = n * vpp * (t.r_gross * t.stop_pts - 2 * COST_PTS[sym])
            day_pl += pl
            rows.append({**t.to_dict(), "unidades": n, "riesgo_usd": round(n * per_unit_loss, 2),
                         "pl_usd": round(pl, 2), "operada": True, "pl_dia_acumulado": round(day_pl, 2)})
    return pd.DataFrame(rows)


def summarize(x: pd.DataFrame) -> dict:
    o = x[x.operada]
    if o.empty:
        return {}
    eq = ACCOUNT + o.sort_values("t_entry").pl_usd.cumsum()
    peak = eq.cummax()
    daily = o.groupby("date").pl_usd.sum()
    wins = o.pl_usd > 0
    return {
        "operaciones": len(o),
        "aciertos_%": round(100 * wins.mean(), 1),
        "beneficio_total_$": round(o.pl_usd.sum(), 0),
        "beneficio_medio_$": round(o.pl_usd.mean(), 1),
        "ganancia_media_$": round(o[wins].pl_usd.mean(), 1),
        "perdida_media_$": round(o[~wins].pl_usd.mean(), 1),
        "factor_beneficio": round(o[wins].pl_usd.sum() / -o[~wins].pl_usd.sum(), 2) if (~wins).any() else np.inf,
        "max_drawdown_$": round((eq - peak).min(), 0),
        "peor_dia_$": round(daily.min(), 0),
        "dias_que_superan_400$": int(o.groupby("date").pl_dia_acumulado.min().lt(-DAILY_MAX_LOSS - 1e-6).sum()),
        "racha_perdedora_max": int(max((len(list(g)) for k, g in __import__("itertools").groupby(~wins.values) if k),
                                       default=0)),
        "R_medio_neto": round((o.r_gross - o.cost_r).mean(), 3),
    }


def prop_survival(book: pd.DataFrame) -> dict:
    """
    Empezando cada día hábil de la historia, ¿qué se alcanza antes: +PROP_TARGET, o perder la cuenta
    (−PROP_MAX_LOSS en total o más de DAILY_MAX_LOSS en un día)? Sobre las operaciones del libro, en orden. Devuelve % de aprobados, suspendidos y sin resolver.
    """
    o = book[book.operada].sort_values("t_entry")
    pl = o.pl_usd.to_numpy()
    days = o.date.to_numpy()
    starts = np.unique(days)
    passed = failed = open_ = 0
    dur = []
    # pérdida acumulada dentro de cada día hasta cada operación (para el límite diario)
    day_cum = o.pl_dia_acumulado.to_numpy()      # resultado del día en la cuenta (ambas sesiones)
    breach = day_cum < -DAILY_MAX_LOSS - 1e-6
    for d0 in starts:
        i0 = int(np.searchsorted(days, d0))
        cum = np.cumsum(pl[i0:])
        jp = _first(cum >= PROP_TARGET)
        jf = _first((cum <= -PROP_MAX_LOSS) | breach[i0:])
        if jp >= 0 and (jf < 0 or jp < jf):
            passed += 1
            dur.append(jp + 1)
        elif jf >= 0:
            failed += 1
        else:
            open_ += 1
    n = len(starts)
    return {"inicios": n, "aprueba_%": round(100 * passed / n, 1), "suspende_%": round(100 * failed / n, 1),
            "sin_resolver_%": round(100 * open_ / n, 1),
            "operaciones_medianas_hasta_aprobar": float(np.median(dur)) if dur else np.nan}


class BacktestPlanAgent:
    def __init__(self, bars: dict[str, pd.DataFrame], ev: pd.DataFrame, out_dir: str):
        self.bars = bars
        self.ev = ev[(ev.break_dir != "none") & (ev.or_min == OR_MIN)].copy()
        self.out = out_dir
        os.makedirs(out_dir, exist_ok=True)

    def trades(self) -> pd.DataFrame:
        rows = []
        for _, e in self.ev.iterrows():
            t = simulate_day(e.symbol, self.bars[e.symbol], e)
            if t:
                rows.append({**t.__dict__, "sample": e["sample"], "anio": e.date[:4]})
        return pd.DataFrame(rows)

    def run(self) -> dict:
        tr = self.trades()
        res, books = [], {}
        for unit in UNITS:
            for pname, pol in POLICIES.items():
                b = apply_policy(tr, pol["risk"], pol["daily_cap"], unit)
                books[(unit, pname)] = b
                for sym in ["NAS100", "US500"]:
                    for ses in ["todas", "London", "NewYork"]:
                        x = b[b.symbol == sym]
                        if ses != "todas":
                            x = x[x.session == ses]
                        s = summarize(x)
                        if s:
                            res.append({"unidad": UNITS[unit]["nombre"], "politica": pname, "indice": sym,
                                        "sesion": ses, **s})
        summ = pd.DataFrame(res)
        stats = self.rule_stats(tr)
        surv = []
        ny_books = {}
        for pname, pol in POLICIES.items():
            # "solo NY" = operar únicamente Nueva York (libro propio, sin operaciones de Londres)
            ny_books[pname] = apply_policy(tr[tr.session == "NewYork"], pol["risk"], pol["daily_cap"], "cfd")
            for sym in ["NAS100", "US500"]:
                for ses, b in [("Londres + NY", books[("cfd", pname)]), ("solo NY", ny_books[pname])]:
                    x = b[b.symbol == sym]
                    surv.append({"politica": pname, "indice": sym, "sesiones": ses, **prop_survival(x),
                                 **{k: v for k, v in summarize(x).items()
                                    if k in ("operaciones", "beneficio_total_$", "max_drawdown_$")}})
        surv = pd.DataFrame(surv)
        surv.to_csv(os.path.join(self.out, "supervivencia_cuenta_fondeada.csv"), index=False)
        tr.to_csv(os.path.join(self.out, "operaciones_reglas.csv"), index=False)
        summ.to_csv(os.path.join(self.out, "resumen_politicas.csv"), index=False)
        main = books[("cfd", "200 $ por operación (0,4 %) con límite diario")]
        main.to_csv(os.path.join(self.out, "diario_cfd_200usd.csv"), index=False)
        self.chart_equity(books)
        self.template()
        ex = self.examples(tr)
        self.ny_books = ny_books
        return {"trades": tr, "summary": summ, "stats": stats, "books": books, "examples": ex, "survival": surv,
                "ny_books": ny_books}

    def rule_stats(self, tr: pd.DataFrame) -> pd.DataFrame:
        g = tr.groupby(["symbol", "session"])
        st = g.apply(lambda x: pd.Series({
            "operaciones": len(x),
            "por_año": round(len(x) / x.anio.nunique(), 0),
            "TP1+TP2_%": round(100 * (x.outcome == "TP1+TP2").mean(), 1),
            "TP1+stop_%": round(100 * (x.outcome == "TP1+stop").mean(), 1),
            "TP1+cierre_%": round(100 * (x.outcome == "TP1+cierre").mean(), 1),
            "stop_%": round(100 * (x.outcome == "stop").mean(), 1),
            "cierre_sin_TP_%": round(100 * (x.outcome == "cierre").mean(), 1),
            "R_bruto": round(x.r_gross.mean(), 3),
            "R_neto": round((x.r_gross - x.cost_r).mean(), 3),
            "R_neto_IS": round((x[x["sample"] == "IS"].r_gross - x[x["sample"] == "IS"].cost_r).mean(), 3),
            "R_neto_OOS": round((x[x["sample"] == "OOS"].r_gross - x[x["sample"] == "OOS"].cost_r).mean(), 3),
            "stop_mediano_pts": round(x.stop_pts.median(), 1),
        }), include_groups=False)
        st.to_csv(os.path.join(self.out, "estadisticas_reglas.csv"))
        return st

    def chart_equity(self, books):
        fig, axes = plt.subplots(1, 2, figsize=(11, 3.8), sharey=False)
        cols = [style.ORANGE, style.AMBER, style.BLUE]
        for ax, sym in zip(axes, ["NAS100", "US500"]):
            for col, pname in zip(cols, POLICIES):
                b = books[("cfd", pname)]
                x = b[(b.symbol == sym) & b.operada].sort_values("t_entry")
                ax.plot(pd.to_datetime(x.t_entry), ACCOUNT + x.pl_usd.cumsum(), color=col, lw=1.4, label=pname)
            ax.axhline(ACCOUNT, color=style.INK2, lw=0.8)
            ax.set_title(f"{sym} · Londres + Nueva York, OR 15 min", loc="left", fontsize=10)
            ax.set_ylabel("Capital ($)")
        axes[0].legend(fontsize=7.5, loc="best")
        fig.suptitle("Plan: entrada en 0,382 tras tocar el 50 %, stop en el extremo opuesto, mitad en 1,618 y mitad en 2,0 "
                     "(cuenta de 50.000 $)", x=0.01, ha="left", fontsize=10)
        fig.tight_layout()
        fig.savefig(os.path.join(self.out, "capital_plan.png"), dpi=150, bbox_inches="tight")
        plt.close(fig)

    def template(self):
        cols = ["fecha", "sesion", "indice", "hora_ruptura", "direccion", "maximo_rango", "minimo_rango",
                "tamano_rango_pts", "tamano_rango (pequeño/medio/grande)", "hora_toca_50", "precio_50",
                "hora_entrada", "precio_entrada_0382", "stop_extremo_opuesto", "distancia_stop_pts",
                "riesgo_usd", "limite_diario_restante_usd", "micro_lotes", "tp1_1618", "tp2_20",
                "hora_salida_mitad1", "precio_salida_mitad1", "hora_salida_mitad2", "precio_salida_mitad2",
                "resultado (TP1+TP2 / TP1+stop / stop / cierre)", "pl_usd", "pl_R", "saldo_cuenta",
                "perdida_del_dia_usd", "regla_incumplida (sí/no y cuál)", "notas"]
        pd.DataFrame(columns=cols).to_csv(os.path.join(self.out, "plantilla_registro_backtest.csv"), index=False)

    def examples(self, tr: pd.DataFrame) -> dict:
        """Un día real reciente de cada desenlace (NAS100, Nueva York) para el ejemplo paso a paso."""
        ex = {}
        for out in ["TP1+TP2", "TP1+stop", "stop"]:
            x = tr[(tr.outcome == out) & (tr.symbol == "NAS100") & (tr.session == "NewYork")].sort_values("date")
            if len(x):
                ex[out] = x.iloc[-1]
        return ex


def money(v: float) -> str:
    s = f"{abs(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return ("−" if v < 0 else "") + s + " $"


def num(v: float, d: int = 2) -> str:
    return f"{v:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def example_rows(t: pd.Series, risk_usd: float, unit: str) -> dict:
    """Cálculo paso a paso para el ejemplo: tamaño, valor por punto, P&L por mitad."""
    vpp = UNITS[unit][t.symbol]
    per_unit_loss = (t.stop_pts + 2 * COST_PTS[t.symbol]) * vpp
    n = int(math.floor(risk_usd / per_unit_loss))
    half = n / 2
    s = 1 if t.direction == "alcista" else -1
    pl1 = half * vpp * (s * (t.exit1 - t.entry) - 2 * COST_PTS[t.symbol])
    pl2 = half * vpp * (s * (t.exit2 - t.entry) - 2 * COST_PTS[t.symbol])
    return {"n": n, "vpp": vpp, "per_unit_loss": per_unit_loss, "pl1": pl1, "pl2": pl2, "pl": pl1 + pl2,
            "risk_real": n * per_unit_loss}


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default="dukascopy")
    a = ap.parse_args()
    C.use_source(a.source)
    bars = {s: db.load_bars(s) for s in C.SYMBOLS}
    evs = []
    for sym, b in bars.items():
        e_, _ = E.extract_events(sym, b, E.ny_daily(b))
        evs.append(e_)
    out = os.path.join(db.results_dir(), "backtest_plan")
    ag = BacktestPlanAgent(bars, pd.concat(evs, ignore_index=True), out)
    r = ag.run()
    pdf, pdf2 = write_documents(ag, r)
    print(f"[plan] {len(r['trades'])} operaciones -> {out}\n{pdf}\n{pdf2}")
    print(r["stats"].to_string())
    s = r["summary"]
    print(s[(s.sesion == "todas")].to_string(index=False))
    print(r["survival"].to_string(index=False))
    for k, t in r["examples"].items():
        print(k, t.date, t.direction, t.entry, t.stop, t.tp1, t.tp2, t.stop_pts, t.t_entry, t.t_exit1, t.t_exit2)
    return r



# ================================================================================================
# Documento de pautas (PDF + Markdown)
# ================================================================================================

def example_even(t: pd.Series, risk_usd: float, unit: str) -> dict:
    """Como example_rows, pero con un número PAR de unidades (mitad en 1,618 y mitad en 2,0)."""
    vpp = UNITS[unit][t.symbol]
    per_unit_loss = (t.stop_pts + 2 * COST_PTS[t.symbol]) * vpp
    n = int(math.floor(risk_usd / per_unit_loss))
    n -= n % 2
    s = 1 if t.direction == "alcista" else -1
    h = n // 2
    pl1 = h * vpp * (s * (t.exit1 - t.entry) - 2 * COST_PTS[t.symbol])
    pl2 = h * vpp * (s * (t.exit2 - t.entry) - 2 * COST_PTS[t.symbol])
    return {"n": n, "h": h, "vpp": vpp, "per_unit_loss": per_unit_loss, "risk_real": n * per_unit_loss,
            "pl1": pl1, "pl2": pl2, "pl": pl1 + pl2}


def fig_plan(path):
    fig, ax = plt.subplots(figsize=(7.4, 3.7))
    H, L = 1.0, 0.0
    ax.axvspan(0, 15, color="#e6ebf2", lw=0)
    ax.text(7.5, 2.18, "Rango de apertura\n15 min", ha="center", fontsize=7.5, color=style.INK2)
    lines = [(H, "Máximo = nivel roto", style.BLUE, "-", 1.4), (L, "Mínimo = extremo opuesto → STOP", style.ORANGE, "-", 1.8),
             (0.5, "50 % (hay que tocarlo primero)", style.INK2, ":", 1.0),
             (H - 0.382, "0,382 → ENTRADA (orden stop al volver)", style.GREEN, "-", 1.8),
             (H + 0.618, "1,618 → cierra la MITAD (TP1)", "#1c5fb0", "--", 1.6),
             (H + 1.0, "2,0 → cierra el RESTO (TP2) y fin", "#6250d6", "--", 1.6)]
    for y, t, c, ls, w in lines:
        ax.axhline(y, color=c, lw=w, ls=ls)
        ax.text(101, y, t, va="center", fontsize=7.3, color=c)
    xs = [0, 4, 8, 12, 15, 18, 22, 27, 31, 35, 40, 46, 52, 58, 64, 70, 78, 86, 94]
    ys = [0.5, 0.85, 0.25, 0.9, 0.6, 1.12, 1.2, 0.85, 0.62, 0.48, 0.55, 0.66, 0.95, 1.2, 1.45, 1.63, 1.75, 1.9, 2.02]
    ax.plot(xs, ys, color=style.INK, lw=1.4)
    for x, y, t, tx, ty in [(18, 1.12, "1 · ruptura\n(cierre fuera)", 10, 1.5), (35, 0.48, "2 · toca el 50 %", 22, 0.12),
                            (40, 0.618, "3 · vuelve a 0,382:\nENTRA", 46, 0.2), (70, 1.618, "4 · TP1", 62, 1.95),
                            (94, 2.0, "5 · TP2", 86, 2.25)]:
        ax.annotate(t, xy=(x, y), xytext=(tx, ty), fontsize=7, arrowprops=dict(arrowstyle="->", color=style.INK2))
    ax.set_xlim(-2, 100)
    ax.set_ylim(-0.2, 2.35)
    ax.axis("off")
    fig.savefig(path, dpi=220, bbox_inches="tight")
    plt.close(fig)


def write_documents(agent: "BacktestPlanAgent", r: dict):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.units import cm
    from reportlab.platypus import Image, KeepTogether, PageBreak, SimpleDocTemplate, Spacer, Table, TableStyle
    from guide.build_guide import P, table, boxed, ST, GRID as G_GRID

    out = agent.out
    fig_plan(os.path.join(out, "plan_niveles.png"))
    st, surv, summ, ex = r["stats"], r["survival"], r["summary"], r["examples"]
    NY = "America/New_York"

    def hm(ts):
        return pd.Timestamp(ts).tz_convert(NY).strftime("%H:%M") if ts is not None and not pd.isna(ts) else "—"

    S = []
    S += [P("Pautas de backtest: plan ORB «50 % → entrada en 0,382» en una cuenta fondeada de 50.000 $", "h1"),
          P("Redactado por el agente de estrategia con velas de 1 minuto de NAS100 y US500 (2022-2026). Rango de apertura "
            "de 15 minutos en Londres (08:00) y Nueva York (09:30).", "sub"),
          boxed(P("<b>Antes de empezar: tus reglas de riesgo chocan.</b> El 2 % de 50.000 $ son <b>1.000 $</b> por operación, "
                  f"pero el límite de pérdida diaria es de <b>{DAILY_MAX_LOSS:.0f} $</b>. Un solo stop con el 2 % rompe el "
                  "límite y, en una cuenta fondeada, eso normalmente significa perder la cuenta. En el backtest, con el 2 % "
                  f"se habría superado el límite en <b>{int(summ[(summ.politica.str.startswith('2 % por')) & (summ.indice == 'NAS100') & (summ.sesion == 'todas') & (summ.unidad.str.startswith('micro lotes'))]['dias_que_superan_400$'].iloc[0])} días</b> "
                  "con NAS100. Estas pautas usan como máximo <b>400 $ por operación si solo operas una sesión al día</b>, "
                  "o <b>200 $ por operación si operas Londres y Nueva York</b>.", "box"), "#c2441a", "#fdf3ef"),
          Spacer(1, 6),
          P("1. Reglas del plan", "h2"),
          Image(os.path.join(out, "plan_niveles.png"), width=17 * cm, height=8.4 * cm),
          table([["#", "Regla", "Detalle exacto para el backtest"],
                 ["1", "Sesiones", "Londres: rango 08:00-08:15 (hora de Londres), seguimiento hasta las 12:00. Nueva York: rango "
                                   "09:30-09:45 (hora de NY), seguimiento hasta las 16:00."],
                 ["2", "Cuenta", "Fondeada de 50.000 $. Pérdida máxima diaria 400 $ (cuenta la operación abierta en su peor caso: el stop)."],
                 ["3", "Ruptura", "Primera vela de 1 min que CIERRA fuera del rango. Define la dirección (alcista o bajista)."],
                 ["4", "Condición previa", "Después de la ruptura el precio debe tocar el 50 % del rango. Si antes toca el extremo "
                                           "opuesto, no hay operación ese día."],
                 ["5", "Entrada", "Orden stop en el 0,382 (contado desde el nivel roto): se entra cuando el precio, tras tocar el "
                                  "50 %, vuelve a pasar por el 0,382 a favor de la ruptura. Solo en una vela posterior a la que tocó el 50 %."],
                 ["6", "Stop", "En el extremo opuesto del rango (mínimo si la ruptura es alcista, máximo si es bajista)."],
                 ["7", "Objetivos", "Mitad de la posición en la extensión 1,618 (TP1) y la otra mitad en 2,0 (TP2). El stop de la "
                                    "segunda mitad sigue en el extremo opuesto."],
                 ["8", "Salida", "Al tocar 2,0 se cierra todo. Si al final de la sesión no se ha cerrado, se cierra a mercado "
                                 "(12:00 Londres, 16:00 NY)."],
                 ["9", "Una operación", "Como máximo una operación por sesión y por índice."]],
                [0.6 * cm, 2.8 * cm, 13.6 * cm])]

    # 2. Tamaño
    S += [PageBreak(), P("2. Cómo calcular los micro lotes", "h2"),
          boxed(P("<b>Micro lotes = riesgo en $ ÷ (distancia al stop en puntos + costes) ÷ valor de un punto por micro lote</b><br/>"
                  "Redondea siempre hacia abajo y a un número <b>par</b> (la mitad sale en 1,618 y la otra mitad en 2,0).", "box")),
          Spacer(1, 4),
          table([["Instrumento", "Unidad", "Valor de 1 punto", "Comprueba en tu plataforma"],
                 ["NAS100 / US500 (CFD)", "1 micro lote = 0,01 lotes", "0,01 $ por micro lote (1 lote = 1 $/punto)",
                  "Especificación del símbolo: tamaño de contrato. Algunas cuentas usan 1 lote = 10 $/punto o 20 $/punto: divide en consecuencia."],
                 ["Nasdaq 100 (futuros)", "1 contrato MNQ", "2 $ por punto", "Cuentas fondeadas de futuros."],
                 ["S&P 500 (futuros)", "1 contrato MES", "5 $ por punto", "Cuentas fondeadas de futuros."]],
                [3.6 * cm, 3.6 * cm, 4.2 * cm, 5.6 * cm]),
          P(f"Costes usados (spread + comisión por lado): NAS100 {COST_PTS['NAS100']:g} punto, US500 {COST_PTS['US500']:g} punto. "
            "Ajusta estos valores a tu cuenta.", "small")]

    # 3. Ejemplos reales
    S += [P("3. Tres operaciones reales paso a paso (NAS100, Nueva York)", "h2"),
          P("Precios de la serie CFD de Dukascopy, horas de Nueva York. Para cada ejemplo se muestra el tamaño con el riesgo "
            "recomendado (400 $ si solo operas esa sesión) y con el 2 % pedido (1.000 $), en micro lotes CFD y en contratos MNQ.")]
    titles = {"TP1+TP2": "Ganadora completa: TP1 y TP2", "TP1+stop": "TP1 y después stop en la segunda mitad",
              "stop": "Perdedora: stop"}
    for key in ["TP1+TP2", "TP1+stop", "stop"]:
        if key not in ex:
            continue
        t = ex[key]
        up = t.direction == "alcista"
        rows = [["Paso", "Hora NY", "Qué pasa", "Precio"],
                ["Rango", "09:30-09:45", f"Máximo {num(t.or_high)} · mínimo {num(t.or_low)} · tamaño {num(t.rng, 1)} pts", ""],
                ["Ruptura", hm(t.t_break), f"Vela cierra {'por encima del máximo' if up else 'por debajo del mínimo'}: plan {t.direction}", ""],
                ["Toca 50 %", hm(t.t_50), "Retrocede a la mitad del rango: se activa la orden", num((t.or_high + t.or_low) / 2)],
                ["Entrada", hm(t.t_entry), f"Vuelve al 0,382 → orden stop de {'compra' if up else 'venta'} ejecutada", num(t.entry)],
                ["Stop", "", f"Extremo opuesto · distancia {num(t.stop_pts, 1)} pts", num(t.stop)],
                ["TP1 / TP2", "", "Extensión 1,618 / extensión 2,0", f"{num(t.tp1)} / {num(t.tp2)}"]]
        if t.outcome == "stop":
            rows.append(["Salida", hm(t.t_exit1), "Toca el stop: se cierra toda la posición", num(t.exit1)])
        else:
            rows.append(["Salida 1", hm(t.t_exit1), "Toca 1,618: cierra la mitad", num(t.exit1)])
            rows.append(["Salida 2", hm(t.t_exit2), "Toca 2,0: cierra el resto y termina" if t.outcome == "TP1+TP2" else
                         "Toca el stop con la segunda mitad", num(t.exit2)])
        sz = [["Tamaño y resultado", "Riesgo 400 $ · CFD", "Riesgo 400 $ · MNQ", "Riesgo 2 % (1.000 $) · CFD", "Riesgo 2 % · MNQ"]]
        cells = [example_even(t, 400, "cfd"), example_even(t, 400, "micro_fut"),
                 example_even(t, ACCOUNT * RISK_PCT, "cfd"), example_even(t, ACCOUNT * RISK_PCT, "micro_fut")]
        sz.append(["Unidades (par)"] + [f"{c['n']} micro lotes ({c['n'] / 100:.2f} lotes)" if i in (0, 2) else f"{c['n']} contratos"
                                        for i, c in enumerate(cells)])
        sz.append(["Riesgo real si salta el stop"] + [money(-c["risk_real"]) for c in cells])
        sz.append(["Resultado mitad 1"] + [money(c["pl1"]) for c in cells])
        sz.append(["Resultado mitad 2"] + [money(c["pl2"]) for c in cells])
        sz.append(["Resultado total"] + [money(c["pl"]) for c in cells])
        sz.append(["¿Respeta el límite de 400 $?"] + ["sí" if c["risk_real"] <= DAILY_MAX_LOSS + 1e-6 else "NO: un stop lo supera"
                                                     for c in cells])
        zero = [i for i, c in enumerate(cells) if c["n"] == 0]
        note = ("Con 0 unidades el stop es demasiado amplio para ese riesgo: no alcanza para 2 contratos (uno por mitad). "
                "Se opera 1 contrato con salida única en 1,618, o no se opera." if zero else "")
        S += [KeepTogether([P(f"{titles[key]} — {t.date}", "h3"),
                            table(rows, [2.2 * cm, 2.4 * cm, 9.2 * cm, 3.2 * cm]), Spacer(1, 3),
                            table(sz, [3.8 * cm, 3.3 * cm, 3.1 * cm, 3.6 * cm, 3.2 * cm])] + ([P(note, "small")] if note else []))]

    # 4. Pautas para hacer el backtest
    S += [PageBreak(), P("4. Pautas para hacer el backtest", "h2"),
          table([["Paso", "Qué hacer"],
                 ["1. Preparación", "TradingView con el indicador ORB en 1 minuto, modo Replay. Elige un índice y anota de antemano "
                                    "las sesiones que vas a operar. No cambies las reglas a mitad del backtest."],
                 ["2. Orden", "Avanza día a día desde una fecha fija, sin saltarte días ni elegir «los bonitos». Si un día no hay "
                              "setup, anótalo como «sin operación»."],
                 ["3. Cada sesión", "Marca el rango a los 15 minutos. Espera la vela que cierra fuera. Espera el toque del 50 %. "
                                    "Coloca la orden stop en el 0,382 con stop en el extremo opuesto y los dos objetivos."],
                 ["4. Tamaño", "Antes de entrar calcula los micro lotes con la fórmula de la sección 2 y el riesgo que te queda del "
                               "límite diario (400 $ menos lo perdido hoy)."],
                 ["5. Ejecución", "Si en una misma vela se tocan el stop y un objetivo, cuenta el stop. Si la entrada y el stop se "
                                  "tocan en la misma vela, cuenta la pérdida. Suma el spread y la comisión."],
                 ["6. Registro", "Anota cada operación en la hoja de registro (PDF aparte, o plantilla_registro_backtest.csv): horas, "
                                 "precios, micro lotes, resultado en $ y en R, saldo y pérdida del día."],
                 ["7. Muestra", "Mínimo 100 operaciones por sesión (≈ 9 meses) antes de sacar conclusiones. Divide en dos mitades "
                                "y comprueba que el resultado se repite en las dos."],
                 ["8. Métricas", "% de aciertos, R medio por operación (después de costes), beneficio total, máximo drawdown, peor "
                                 "día, racha perdedora más larga y número de días que habrías superado el límite diario."],
                 ["9. Decisión", "Solo pasa a cuenta real si el R medio neto es positivo en las dos mitades, el drawdown máximo "
                                 "cabe en la pérdida máxima de la cuenta y ningún día supera el límite diario."]],
                [2.8 * cm, 14.2 * cm])]

    # 5. Resultados del backtest automático
    stx = st.reset_index()
    rows = [["Índice", "Sesión", "Operac. (por año)", "TP1 + TP2", "TP1 + stop", "Stop", "Cierre sin TP", "R neto", "R neto 2022-24",
             "R neto 2025-26", "Stop mediano"]]
    for _, x in stx.iterrows():
        rows.append([x.symbol, "Londres" if x.session == "London" else "Nueva York", f"{int(x.operaciones)} ({int(x['por_año'])})",
                     f"{x['TP1+TP2_%']:.0f} %", f"{x['TP1+stop_%']:.0f} %", f"{x['stop_%']:.0f} %",
                     f"{x['cierre_sin_TP_%'] + x['TP1+cierre_%']:.0f} %", f"{x.R_neto:+.2f}", f"{x.R_neto_IS:+.2f}",
                     f"{x.R_neto_OOS:+.2f}", f"{x.stop_mediano_pts:.0f} pts"])
    sv = surv[surv.politica != "2 % por operación (lo pedido)"].copy()
    srows = [["Riesgo", "Índice", "Sesiones", "Operac.", "Beneficio 2022-26", "Máx. drawdown", "Aprueba", "Pierde"]]
    for _, x in surv.iterrows():
        srows.append([x.politica, x.indice, x.sesiones, int(x.operaciones), money(x["beneficio_total_$"]),
                      money(x["max_drawdown_$"]), f"{x['aprueba_%']:.0f} %", f"{x['suspende_%']:.0f} %"])
    S += [P("5. Resultado del backtest automático (2022-2026)", "h2"),
          P("El agente aplicó estas reglas exactas, vela a vela, a todas las sesiones de 2022 a 2026. «R» es el resultado en "
            "unidades de riesgo, con la mitad en 1,618 y la otra mitad en 2,0: si salen las dos mitades se ganan +1,93 R; con "
            "TP1 y después stop, +0,31 R; con stop, −1 R."),
          table(rows, [1.5 * cm, 1.7 * cm, 1.9 * cm, 1.4 * cm, 1.4 * cm, 1.2 * cm, 1.5 * cm, 1.3 * cm, 1.7 * cm, 1.7 * cm, 1.7 * cm]),
          Spacer(1, 4),
          Image(os.path.join(out, "capital_plan.png"), width=17 * cm, height=5.9 * cm),
          P(f"Cuenta fondeada simulada: empezando cada día de la historia, ¿qué pasa antes, ganar {PROP_TARGET:,.0f} $ (objetivo "
            f"típico del 6 %) o perder la cuenta (−{PROP_MAX_LOSS:,.0f} $ en total o más de {DAILY_MAX_LOSS:.0f} $ en un día)? "
            "Objetivo y pérdida máxima total son supuestos típicos: cámbialos por los de tu empresa.".replace(",", "."), "small"),
          table(srows, [4.1 * cm, 1.5 * cm, 2 * cm, 1.4 * cm, 2.3 * cm, 2.3 * cm, 1.9 * cm, 1.5 * cm])]

    # 6. Conclusión
    ny = st.loc[("NAS100", "NewYork")]
    S += [P("6. Lo que dice el backtest", "h2"),
          table([["Hallazgo", "Qué significa para ti"],
                 ["El 2 % por operación no es compatible con el límite diario de 400 $.",
                  "Con el 2 % la cuenta se habría perdido la gran mayoría de las veces, casi siempre por superar el límite diario."],
                 [f"El plan gana el 26-29 % de las veces las dos mitades (+1,93 R) y pierde el stop completo el 55-57 %.",
                  "Es una estrategia de pocos aciertos y ganancias grandes: espera rachas de 10-12 pérdidas seguidas."],
                 ["En Londres el rango es pequeño (stop mediano 17 pts en NAS100 y 3 en US500) y los costes se comen el resultado.",
                  "Londres sale negativo en todos los periodos: el backtest no apoya operarlo con este plan."],
                 [f"Nueva York con NAS100: R neto {ny.R_neto:+.2f} ({ny.R_neto_IS:+.2f} en 2022-24 y {ny.R_neto_OOS:+.2f} en 2025-26).",
                  "Prácticamente en equilibrio y sin estabilidad entre periodos: no hay una ventaja clara."],
                 ["Con 200-400 $ de riesgo y solo NY en NAS100, la cuenta se aprueba en ≈ 35-49 % de los inicios y se pierde en ≈ 43-49 %.",
                  "Con una expectativa cercana a cero, aprobar o suspender es casi una moneda al aire."]],
                [8 * cm, 9 * cm]),
          boxed(P("<b>Recomendación del agente.</b> Haz el backtest manual siguiendo estas pautas en NAS100, sesión de Nueva York, "
                  "con 200 $ de riesgo, y anota todo. Antes de usar dinero de una cuenta fondeada, prueba cambios de una sola "
                  "variable cada vez (por ejemplo, operar solo con rango pequeño, o mover el stop a entrada al tocar 1,618) y "
                  "comprueba que mejoran en las dos mitades del periodo. Material educativo, no es asesoramiento financiero.", "box"))]

    # 7. Plantilla imprimible
    hdr = ["Fecha", "Sesión", "Dir.", "Máx / mín rango", "Hora 50 %", "Entrada 0,382", "Stop", "Pts stop", "Micro lotes",
           "TP1 / TP2", "Resultado", "P&L $", "P&L R", "Pérdida del día"]
    blank = [hdr] + [[""] * len(hdr) for _ in range(18)]
    tt = Table([[P(c.replace("&", "&amp;"), "cellb") for c in blank[0]]] + blank[1:],
               colWidths=[1.9 * cm, 1.6 * cm, 1.2 * cm, 2.4 * cm, 1.6 * cm, 2.1 * cm, 1.8 * cm, 1.5 * cm, 1.7 * cm, 2.6 * cm,
                          2.2 * cm, 1.6 * cm, 1.3 * cm, 2 * cm], rowHeights=[None] + [0.85 * cm] * 18)
    tt.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#9a9a9a")),
                            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e6ebf2")), ("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))

    pdf = os.path.join(out, "Pautas_Backtest_50K.pdf")

    def footer(canvas, doc):
        canvas.saveState()
        canvas.setFont("DV", 7)
        canvas.setFillColor(colors.HexColor("#4a4a4a"))
        canvas.drawString(doc.leftMargin, 1.1 * cm, "Pautas de backtest · plan ORB 50 % → 0,382 · cuenta fondeada 50.000 $ · "
                                                    "material educativo, no es asesoramiento financiero")
        canvas.drawRightString(doc.pagesize[0] - doc.rightMargin, 1.1 * cm, f"{doc.page}")
        canvas.restoreState()
    doc = SimpleDocTemplate(pdf, pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm, topMargin=1.6 * cm, bottomMargin=1.8 * cm,
                            title="Pautas de backtest — plan ORB 50K", author="Agente de estrategia (orb/)")
    from reportlab.platypus import NextPageTemplate, PageTemplate, Frame, BaseDocTemplate  # noqa: F401
    doc.build(S, onFirstPage=footer, onLaterPages=footer)

    # plantilla en apaisado, archivo aparte para imprimir varias copias
    pdf2 = os.path.join(out, "Hoja_Registro_Backtest.pdf")
    doc2 = SimpleDocTemplate(pdf2, pagesize=landscape(A4), leftMargin=1.2 * cm, rightMargin=1.2 * cm, topMargin=1.2 * cm,
                             bottomMargin=1.4 * cm, title="Hoja de registro del backtest")
    doc2.build([P("Hoja de registro del backtest · plan ORB 50 % → 0,382 · cuenta 50.000 $ · límite diario 400 $", "h2"),
                P("Índice: ____________   Riesgo por operación: ________ $   Página: ____", "p"), tt], onFirstPage=footer,
               onLaterPages=footer)
    return pdf, pdf2


if __name__ == "__main__":
    main()
