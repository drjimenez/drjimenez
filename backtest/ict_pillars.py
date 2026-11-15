"""Medición estadística de los "tres pilares" de ICT (How New Students Should Start, parte 4).

Datos: velas de 1 minuto del CFD del Nasdaq 100 (NSXUSD de histdata.com, idéntico a
USATECHIDXUSD de Dukascopy) como proxy del futuro NQ, en hora de Nueva York.

Pilar 1  Premarket 07:00-09:00: estado (tendencia / consolidación) y relación con la mañana;
         toma de la liquidez del premarket tras las 09:30; setup "barrido y extremo opuesto".
Pilar 2  Hueco de apertura RTH (cierre 16:14 del día anterior -> apertura 09:30): frecuencia con
         la que se alcanza el 50 % (CE) antes de las 10:00 frente a un nivel espejo de control;
         proyecciones de "desviación estándar" (-1) del hueco frente a niveles de control.
Pilar 3  Silver Bullet: primer FVG de 1 minuto en la hora de las 10:00, entrada en su CE,
         stop tras la vela previa, objetivo en el extremo de corto plazo. Control: misma regla en
         otras horas.

Uso:  python3 backtest/ict_pillars.py      -> results/ict_pillars/
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from histdata_loader import load_minutes  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "ict_pillars"
START, END = "2023-10-01", "2026-11-06"
TICK = 0.25            # tick del NQ, usado para los ajustes de +/- 1 tick
COST_PTS = 1.0         # coste de ida y vuelta en puntos (comisión + deslizamiento aprox.)
ER_TREND = 0.5         # eficiencia direccional >= 0,5 -> "tendencia"
RNG = np.random.default_rng(7)


# --------------------------------------------------------------------------- utilidades
def prop_ci(k: int, n: int) -> tuple[float, float, float]:
    """Proporción con IC 95 % de Wilson (en %)."""
    if n == 0:
        return float("nan"), float("nan"), float("nan")
    p, z = k / n, 1.96
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return 100 * p, 100 * (c - h), 100 * (c + h)


def two_prop_p(k1: int, n1: int, k2: int, n2: int) -> float:
    """p-valor bilateral de diferencia de proporciones (z, varianza agrupada)."""
    if min(n1, n2) == 0:
        return float("nan")
    p = (k1 + k2) / (n1 + n2)
    se = math.sqrt(p * (1 - p) * (1 / n1 + 1 / n2))
    if se == 0:
        return float("nan")
    z = (k1 / n1 - k2 / n2) / se
    return math.erfc(abs(z) / math.sqrt(2))


def paired_p(a: np.ndarray, b: np.ndarray) -> float:
    """Test de McNemar (aprox. normal) para dos eventos medidos en los mismos días."""
    b10 = int(np.sum(a & ~b))
    b01 = int(np.sum(~a & b))
    if b10 + b01 == 0:
        return float("nan")
    z = (b10 - b01) / math.sqrt(b10 + b01)
    return math.erfc(abs(z) / math.sqrt(2))


def mean_ci(x: np.ndarray, n_boot: int = 4000) -> tuple[float, float, float]:
    x = np.asarray(x, float)
    if len(x) == 0:
        return float("nan"), float("nan"), float("nan")
    bs = RNG.choice(x, size=(n_boot, len(x)), replace=True).mean(axis=1)
    return float(x.mean()), float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))


def first_hit(bars: pd.DataFrame, level: float, above: bool):
    """Primer timestamp en que el precio toca level (above=True: high >= level)."""
    m = bars["high"].to_numpy() >= level if above else bars["low"].to_numpy() <= level
    if not m.any():
        return None
    return bars.index[int(np.argmax(m))]


def eff_ratio(b: pd.DataFrame) -> float:
    rng = b["high"].max() - b["low"].min()
    return abs(b["close"].iloc[-1] - b["open"].iloc[0]) / rng if rng > 0 else 0.0


def swings(b: pd.DataFrame, k: int = 2):
    """Máximos y mínimos fractales (k velas a cada lado)."""
    h, l = b["high"].to_numpy(), b["low"].to_numpy()
    hi = [i for i in range(k, len(b) - k) if h[i] == h[i - k:i + k + 1].max()]
    lo = [i for i in range(k, len(b) - k) if l[i] == l[i - k:i + k + 1].min()]
    return [h[i] for i in hi], [l[i] for i in lo]


def equal_levels(levels, tol):
    """Niveles de pares 'relativamente iguales' (|a-b| <= tol)."""
    out = []
    lv = sorted(levels)
    for a, b in zip(lv, lv[1:]):
        if b - a <= tol:
            out.append((a, b))
    return out


def simulate(bars: pd.DataFrame, side: int, entry: float, stop: float, target: float,
             skip_target_first_bar: bool = True):
    """Recorre las velas tras la entrada. side=+1 largo, -1 corto. Stop antes que objetivo si
    ambos caen en la misma vela. Salida al cierre de la última vela si no toca ninguno."""
    risk = abs(entry - stop)
    for j, (ts, r) in enumerate(bars.iterrows()):
        hit_stop = r["low"] <= stop if side > 0 else r["high"] >= stop
        hit_tgt = r["high"] >= target if side > 0 else r["low"] <= target
        if hit_stop:
            return -1.0, "SL", ts
        if hit_tgt and not (j == 0 and skip_target_first_bar):
            return abs(target - entry) / risk, "TP", ts
    last = bars["close"].iloc[-1]
    return side * (last - entry) / risk, "EOD", bars.index[-1]


# --------------------------------------------------------------------------- días
def build_days(m: pd.DataFrame) -> list[dict]:
    m = m[m.index.weekday < 5]
    dates = sorted(set(m.index.date))
    by_date = {d: g for d, g in m.groupby(m.index.date)}
    # Sesión completa = hay vela a las 09:30 y a las 16:14 (excluye festivos y medias jornadas).
    days, prev_settle = [], None
    for d in dates:
        g = by_date[d]
        has_open = ((g.index.hour == 9) & (g.index.minute == 30)).any()
        last_rth = g[(g.index.hour == 16) & (g.index.minute == 14)]
        if has_open and len(last_rth):
            days.append({"date": d, "bars": g, "settle_prev": prev_settle})
            prev_settle = float(last_rth["close"].iloc[0])
    return days


# --------------------------------------------------------------------------- pilar 1
def pillar1(days):
    rows, trades, swing_rows = [], [], []
    for d in days:
        g = d["bars"]
        pm = g.between_time("07:00", "08:59")
        am = g.between_time("09:30", "11:59")
        sess = g.between_time("09:30", "15:59")
        if len(pm) < 100 or len(am) < 120:
            continue
        ph, pl = pm["high"].max(), pm["low"].min()
        er_pm, er_am = eff_ratio(pm), eff_ratio(am)
        t_h = first_hit(am, ph, True)
        t_l = first_hit(am, pl, False)
        rows.append({"date": d["date"], "pm_high": ph, "pm_low": pl, "pm_range": ph - pl,
                     "pm_er": er_pm, "pm_state": "tendencia" if er_pm >= ER_TREND else "consolidación",
                     "am_er": er_am, "am_range": am["high"].max() - am["low"].min(),
                     "am_state": "tendencia" if er_am >= ER_TREND else "consolidación",
                     "am_takes_high": t_h is not None, "am_takes_low": t_l is not None,
                     "min_to_high": None if t_h is None else (t_h - am.index[0]).seconds / 60,
                     "min_to_low": None if t_l is None else (t_l - am.index[0]).seconds / 60})
        # Liquidez: swings del premarket, iguales o no, tomados en la mañana
        tol = 1e-4 * pm["close"].iloc[-1]
        sh, sl = swings(pm)
        eq_h = {max(p) for p in equal_levels(sh, tol)}
        eq_l = {min(p) for p in equal_levels(sl, tol)}
        o930 = am["open"].iloc[0]
        for lv in set(sh):
            if lv > o930:
                swing_rows.append({"side": "high", "equal": lv in eq_h, "dist_pct": 100 * (lv - o930) / o930,
                                   "taken": first_hit(am, lv, True) is not None})
        for lv in set(sl):
            if lv < o930:
                swing_rows.append({"side": "low", "equal": lv in eq_l, "dist_pct": 100 * (o930 - lv) / o930,
                                   "taken": first_hit(am, lv, False) is not None})
        # Setup: barrido de un extremo del premarket y objetivo en el opuesto (disparo hasta 12:00)
        win = sess
        swept_low = swept_high = False
        ext_low, ext_high = np.inf, -np.inf
        for i, (ts, r) in enumerate(win.iterrows()):
            if ts.time() >= pd.Timestamp("12:00").time():
                break
            ext_low, ext_high = min(ext_low, r["low"]), max(ext_high, r["high"])
            swept_low |= r["low"] < pl
            swept_high |= r["high"] > ph
            side = 0
            if swept_low and r["close"] > pl and ext_low < pl:
                side, entry, stop, target = 1, r["close"], ext_low - TICK, ph
            elif swept_high and r["close"] < ph and ext_high > ph:
                side, entry, stop, target = -1, r["close"], ext_high + TICK, pl
            if side:
                if (target - entry) * side <= 0 or abs(entry - stop) <= 0:
                    break
                R, why, ts_out = simulate(win.iloc[i + 1:], side, entry, stop, target, False)
                risk = abs(entry - stop)
                trades.append({"date": d["date"], "side": "long" if side > 0 else "short",
                               "pm_state": rows[-1]["pm_state"], "entry_time": ts, "entry": entry,
                               "stop": stop, "target": target, "risk_pts": risk,
                               "planned_rr": abs(target - entry) / risk, "R_gross": R,
                               "R_net": R - COST_PTS / risk, "exit": why})
                break
    return pd.DataFrame(rows), pd.DataFrame(trades), pd.DataFrame(swing_rows)


# --------------------------------------------------------------------------- pilar 2
def pillar2(days):
    rows = []
    for d in days:
        if d["settle_prev"] is None:
            continue
        g = d["bars"]
        to10 = g.between_time("09:30", "09:59")
        am = g.between_time("09:30", "11:59")
        sess = g.between_time("09:30", "15:59")
        if len(to10) < 25 or len(am) < 120:
            continue
        settle, op = d["settle_prev"], float(to10["open"].iloc[0])
        gap = op - settle
        if gap == 0:
            continue
        up = gap > 0                      # premium (abre por encima)
        ce, mirror = settle + gap / 2, op + gap / 2
        t_ce = first_hit(to10, ce, not up)
        t_ce_day = first_hit(sess, ce, not up)
        t_mir = first_hit(to10, mirror, up)
        t_fill10 = first_hit(to10, settle, not up)
        t_fill = first_hit(sess, settle, not up)
        t_mfill10 = first_hit(to10, op + gap, up)
        a = abs(gap)
        # Proyecciones: extremos de la mañana en unidades del hueco
        am_hi, am_lo = am["high"].max(), am["low"].min()
        if up:   # premium: settle abajo, apertura arriba
            u_beyond_open = (am_hi - op) / a       # -1 sobre la apertura -> 1.0
            u_beyond_settle = (settle - am_lo) / a # -1 bajo el cierre -> 1.0
        else:
            u_beyond_open = (op - am_lo) / a
            u_beyond_settle = (am_hi - settle) / a
        rows.append({"date": d["date"], "settle": settle, "open": op, "gap_pts": gap,
                     "gap_pct": 100 * gap / settle, "type": "premium" if up else "descuento",
                     "ce_by_10": t_ce is not None, "mirror_by_10": t_mir is not None,
                     "ce_by_16": t_ce_day is not None,
                     "min_to_ce": None if t_ce_day is None else (t_ce_day - sess.index[0]).seconds / 60,
                     "fill_by_10": t_fill10 is not None, "mirror_fill_by_10": t_mfill10 is not None,
                     "fill_by_16": t_fill is not None,
                     "u_beyond_open": u_beyond_open, "u_beyond_settle": u_beyond_settle})
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------- pilar 3
def first_fvg_trade(g: pd.DataFrame, start: str, end_entry: str):
    """Primer FVG cuya vela central está en [start, start+59) y operación sobre él."""
    b = g.between_time("09:30", "15:59")
    idx = b.index
    hh, ll = b["high"].to_numpy(), b["low"].to_numpy()
    t0 = pd.Timestamp(start).time()
    t_end = pd.Timestamp(end_entry).time()
    for i in range(1, len(b) - 1):
        ti = idx[i].time()
        if ti < t0:
            continue
        if ti >= t_end:
            return None
        bull = ll[i + 1] - hh[i - 1] >= TICK
        bear = ll[i - 1] - hh[i + 1] >= TICK
        if not (bull or bear):
            continue
        side = 1 if bull else -1
        lo_g, hi_g = (hh[i - 1], ll[i + 1]) if bull else (hh[i + 1], ll[i - 1])
        ce = (lo_g + hi_g) / 2
        stop = (min(ll[i - 1], ll[i]) - TICK) if bull else (max(hh[i - 1], hh[i]) + TICK)
        ext = hh[i + 1] if bull else ll[i + 1]   # extremo de corto plazo = objetivo
        rec = {"fvg_time": idx[i], "side": "long" if bull else "short", "gap_pts": hi_g - lo_g,
               "traded": False, "minutes_to_return": None}
        for j in range(i + 2, len(b)):
            if idx[j].time() >= t_end:
                return rec
            # si la vela toca la entrada (y quizá el stop), simulate cuenta el stop primero
            touched = ll[j] <= ce if bull else hh[j] >= ce
            if touched:
                target = ext
                entry = ce
                if (target - entry) * side <= 0:
                    return rec
                R, why, ts_out = simulate(b.iloc[j:], side, entry, stop, target, True)
                risk = abs(entry - stop)
                rec.update({"traded": True, "entry_time": idx[j],
                            "minutes_to_return": (idx[j] - idx[i + 1]).seconds / 60,
                            "entry": entry, "stop": stop, "target": target, "risk_pts": risk,
                            "planned_rr": abs(target - entry) / risk, "R_gross": R,
                            "R_net": R - COST_PTS / risk, "exit": why,
                            "run_pts": abs(target - entry) if why == "TP" else None})
                return rec
            ext = max(ext, hh[j]) if bull else min(ext, ll[j])
        return rec
    return None


def pillar3(days):
    windows = {"10:00 (Silver Bullet)": ("10:00", "11:00"), "11:00": ("11:00", "12:00"),
               "12:00": ("12:00", "13:00"), "13:00": ("13:00", "14:00"),
               "14:00 (Silver Bullet PM)": ("14:00", "15:00")}
    out = {}
    for name, (a, b) in windows.items():
        recs = []
        for d in days:
            r = first_fvg_trade(d["bars"], a, b)
            if r is not None:
                r["date"] = d["date"]
                recs.append(r)
        out[name] = pd.DataFrame(recs)
    return out


# --------------------------------------------------------------------------- FVG clasificados
def last_swing(vals: np.ndarray, upto: int, high: bool, k: int = 2):
    """Último máximo (high=True) o mínimo fractal confirmado antes de la vela 'upto'."""
    for c in range(upto - k - 1, k - 1, -1):
        w = vals[c - k:c + k + 1]
        if (high and vals[c] == w.max()) or (not high and vals[c] == w.min()):
            return vals[c]
    return None


def fvg_trade_at(b: pd.DataFrame, i: int, max_wait: int = 60):
    """Operación sobre el FVG con vela central i (misma regla que el Silver Bullet): entrada en el
    CE si el precio vuelve en <= max_wait minutos, stop tras las dos primeras velas, objetivo en el
    extremo alcanzado entre la formación y el retorno, salida a las 15:59."""
    hh, ll = b["high"].to_numpy(), b["low"].to_numpy()
    bull = ll[i + 1] - hh[i - 1] >= TICK
    side = 1 if bull else -1
    lo_g, hi_g = (hh[i - 1], ll[i + 1]) if bull else (hh[i + 1], ll[i - 1])
    ce = (lo_g + hi_g) / 2
    stop = (min(ll[i - 1], ll[i]) - TICK) if bull else (max(hh[i - 1], hh[i]) + TICK)
    ext = hh[i + 1] if bull else ll[i + 1]
    for j in range(i + 2, min(len(b), i + 2 + max_wait)):
        if (ll[j] <= ce) if bull else (hh[j] >= ce):
            if (ext - ce) * side <= 0:
                return None
            R, why, _ = simulate(b.iloc[j:], side, ce, stop, ext, True)
            risk = abs(ce - stop)
            return {"R_gross": R, "R_net": R - COST_PTS / risk, "exit": why, "risk_pts": risk,
                    "planned_rr": abs(ext - ce) / risk}
        ext = max(ext, hh[j]) if bull else min(ext, ll[j])
    return None


def classified_fvgs(days):
    """Todos los FVG de 1 minuto de 09:30 a 15:00 con su clasificación según ICT:
    first presented (FP), FP con desplazamiento (FPD) y first presented reflection (FPR)."""
    rows = []
    for d in days:
        g = d["bars"].between_time("07:00", "15:59")
        if len(g) < 400:
            continue
        idx = g.index
        hh, ll = g["high"].to_numpy(), g["low"].to_numpy()
        t930 = pd.Timestamp("09:30").time()
        t15 = pd.Timestamp("15:00").time()
        first = None
        fpd_done = refl_done = False
        n = 0
        for i in range(1, len(g) - 1):
            if idx[i - 1].time() < t930:
                continue
            if idx[i].time() >= t15:
                break
            bull = ll[i + 1] - hh[i - 1] >= TICK
            bear = ll[i - 1] - hh[i + 1] >= TICK
            if not (bull or bear):
                continue
            # desplazamiento: el tramo rompe el último máximo (alcista) o mínimo (bajista) fractal previo
            if bull:
                ref = last_swing(hh, i - 1, True)
                disp = ref is not None and max(hh[i], hh[i + 1]) > ref
            else:
                ref = last_swing(ll, i - 1, False)
                disp = ref is not None and min(ll[i], ll[i + 1]) < ref
            is_fp = first is None
            if is_fp:
                first = "bull" if bull else "bear"
            is_fpd = disp and not fpd_done
            fpd_done |= is_fpd
            is_refl = (not is_fp) and (not refl_done) and (("bull" if bull else "bear") != first)
            refl_done |= is_refl
            t = idx[i].time()
            macro = (t.minute >= 50 or t.minute < 10)
            tr = fvg_trade_at(g, i)
            rows.append({"date": d["date"], "time": idx[i], "order": n, "side": "long" if bull else "short",
                         "displacement": disp, "FP": is_fp, "FPD": is_fpd, "FPR": is_refl,
                         "macro": macro, "gap_pts": (ll[i + 1] - hh[i - 1]) if bull else (ll[i - 1] - hh[i + 1]),
                         "traded": tr is not None, **(tr or {})})
            n += 1
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------- resumen
def trade_stats(t: pd.DataFrame) -> dict:
    t = t[t.get("traded", True) == True] if "traded" in t else t  # noqa: E712
    if len(t) == 0:
        return {"n": 0}
    g, n = mean_ci(t["R_gross"].to_numpy()), mean_ci(t["R_net"].to_numpy())
    win = prop_ci(int((t["R_gross"] > 0).sum()), len(t))
    return {"n": int(len(t)), "win_pct": round(win[0], 1),
            "R_gross": round(g[0], 3), "R_gross_ci": [round(g[1], 3), round(g[2], 3)],
            "R_net": round(n[0], 3), "R_net_ci": [round(n[1], 3), round(n[2], 3)],
            "planned_rr_median": round(float(t["planned_rr"].median()), 2),
            "risk_pts_median": round(float(t["risk_pts"].median()), 1),
            "exits": t["exit"].value_counts().to_dict()}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    m = load_minutes(START, END)
    days = build_days(m)
    print(f"Sesiones: {len(days)}  ({days[0]['date']} -> {days[-1]['date']})")
    S = {"data": {"instrument": "NSXUSD (histdata.com = USATECHIDXUSD Dukascopy), 1 min, proxy del NQ",
                  "sessions": len(days), "first": str(days[0]["date"]), "last": str(days[-1]["date"]),
                  "cost_pts_round_trip": COST_PTS, "tick": TICK, "er_trend": ER_TREND}}

    # ---------------- Pilar 1
    p1, t1, sw = pillar1(days)
    p1.to_csv(OUT / "pillar1_days.csv", index=False)
    t1.to_csv(OUT / "pillar1_trades.csv", index=False)
    ct = pd.crosstab(p1["pm_state"], p1["am_state"])
    k_t = int(((p1.pm_state == "tendencia") & (p1.am_state == "consolidación")).sum())
    n_t = int((p1.pm_state == "tendencia").sum())
    k_c = int(((p1.pm_state == "consolidación") & (p1.am_state == "consolidación")).sum())
    n_c = int((p1.pm_state == "consolidación").sum())
    corr = float(np.corrcoef(p1["pm_er"], p1["am_er"])[0, 1])
    # rango de la mañana relativo a su mediana móvil de 20 días
    p1["am_range_rel"] = p1["am_range"] / p1["am_range"].rolling(20, min_periods=10).median().shift(1)
    rr = p1.dropna(subset=["am_range_rel"])
    rel_t = mean_ci(rr.loc[rr.pm_state == "tendencia", "am_range_rel"].to_numpy())
    rel_c = mean_ci(rr.loc[rr.pm_state == "consolidación", "am_range_rel"].to_numpy())
    takes = {"solo_alto": int((p1.am_takes_high & ~p1.am_takes_low).sum()),
             "solo_bajo": int((~p1.am_takes_high & p1.am_takes_low).sum()),
             "ambos": int((p1.am_takes_high & p1.am_takes_low).sum()),
             "ninguno": int((~p1.am_takes_high & ~p1.am_takes_low).sum())}
    # swings iguales vs no iguales por distancia
    sw["bucket"] = pd.cut(sw["dist_pct"], [0, 0.1, 0.25, 0.5, 5])
    eq_tab = (sw.groupby(["bucket", "equal"], observed=True)["taken"].agg(["mean", "size"])
              .reset_index())
    eq_rows = []
    for bkt, gb in sw.groupby("bucket", observed=True):
        e, ne = gb[gb.equal], gb[~gb.equal]
        eq_rows.append({"dist_pct": str(bkt), "n_equal": len(e), "taken_equal_pct": round(100 * e.taken.mean(), 1) if len(e) else None,
                        "n_single": len(ne), "taken_single_pct": round(100 * ne.taken.mean(), 1) if len(ne) else None,
                        "p": two_prop_p(int(e.taken.sum()), len(e), int(ne.taken.sum()), len(ne))})
    S["pillar1"] = {
        "days": int(len(p1)),
        "crosstab": {r: ct.loc[r].to_dict() for r in ct.index},
        "p_am_consol_given_pm_trend": prop_ci(k_t, n_t),
        "p_am_consol_given_pm_consol": prop_ci(k_c, n_c),
        "p_value_diff": two_prop_p(k_t, n_t, k_c, n_c),
        "corr_pm_er_am_er": round(corr, 3),
        "am_range_rel_after_pm_trend": rel_t, "am_range_rel_after_pm_consol": rel_c,
        "pm_extremes_taken_9_30_12": takes,
        "pm_high_taken_pct": prop_ci(int(p1.am_takes_high.sum()), len(p1)),
        "pm_low_taken_pct": prop_ci(int(p1.am_takes_low.sum()), len(p1)),
        "median_min_to_first_take": float(pd.concat([p1.min_to_high, p1.min_to_low]).median()),
        "equal_vs_single": eq_rows,
        "setup_sweep_opposite": trade_stats(t1),
        "setup_by_pm_state": {s: trade_stats(t1[t1.pm_state == s]) for s in ["tendencia", "consolidación"]},
    }

    # ---------------- Pilar 2
    p2 = pillar2(days)
    p2.to_csv(OUT / "pillar2_days.csv", index=False)
    p2["abs_pct"] = p2["gap_pct"].abs()
    p2["size"] = pd.cut(p2["abs_pct"], [0, 0.1, 0.25, 0.5, 100],
                        labels=["<0,10 %", "0,10–0,25 %", "0,25–0,50 %", ">0,50 %"])
    def p2block(df):
        n = len(df)
        return {"n": n,
                "ce_by_10": prop_ci(int(df.ce_by_10.sum()), n),
                "mirror_by_10": prop_ci(int(df.mirror_by_10.sum()), n),
                "p_paired": paired_p(df.ce_by_10.to_numpy(), df.mirror_by_10.to_numpy()),
                "ce_by_16": prop_ci(int(df.ce_by_16.sum()), n),
                "fill_by_10": prop_ci(int(df.fill_by_10.sum()), n),
                "mirror_fill_by_10": prop_ci(int(df.mirror_fill_by_10.sum()), n),
                "p_paired_fill": paired_p(df.fill_by_10.to_numpy(), df.mirror_fill_by_10.to_numpy()),
                "fill_by_16": prop_ci(int(df.fill_by_16.sum()), n),
                "median_min_to_ce": float(df.min_to_ce.dropna().median()) if df.min_to_ce.notna().any() else None}
    S["pillar2"] = {"all": p2block(p2),
                    "by_type": {k: p2block(v) for k, v in p2.groupby("type")},
                    "by_size": {str(k): p2block(v) for k, v in p2.groupby("size", observed=True)},
                    "gap_pct_median": float(p2.abs_pct.median()),
                    "gap_pts_median": float(p2.gap_pts.abs().median())}
    # proyecciones (solo huecos >= 0,10 %)
    big = p2[p2.abs_pct >= 0.10]
    u = np.concatenate([big.u_beyond_open.to_numpy(), big.u_beyond_settle.to_numpy()])
    u = u[np.isfinite(u)]
    tol = 0.10
    def frac_near(c):
        return float(np.mean(np.abs(u - c) <= tol))
    controls = [0.6, 0.7, 0.8, 0.9, 1.1, 1.2, 1.3, 1.4]
    S["pillar2"]["projections"] = {
        "n_gaps": int(len(big)), "n_extremes": int(len(u)), "tol_units": tol,
        "near_1.0_pct": round(100 * frac_near(1.0), 2),
        "near_controls_pct": {str(c): round(100 * frac_near(c), 2) for c in controls},
        "controls_mean_pct": round(100 * float(np.mean([frac_near(c) for c in controls])), 2),
        "near_2.0_pct": round(100 * frac_near(2.0), 2),
        "within_1pt_of_level_pct": round(100 * float(np.mean(
            np.concatenate([np.abs(big.u_beyond_open - 1) * big.gap_pts.abs(),
                            np.abs(big.u_beyond_settle - 1) * big.gap_pts.abs()]) <= 1.0)), 2)}

    # ---------------- Pilar 3
    p3 = pillar3(days)
    S["pillar3"] = {}
    for name, df in p3.items():
        df.to_csv(OUT / f"pillar3_{name.split()[0].replace(':', '')}.csv", index=False)
        tr = df[df.traded] if len(df) else df
        S["pillar3"][name] = {"days_with_fvg": int(len(df)),
                              "returned_and_traded": int(len(tr)),
                              "median_min_to_return": float(tr.minutes_to_return.median()) if len(tr) else None,
                              "stats": trade_stats(tr),
                              "long": trade_stats(tr[tr.side == "long"]),
                              "short": trade_stats(tr[tr.side == "short"])}

    # ---------------- FVG clasificados (first presented / desplazamiento / reflection)
    fv = classified_fvgs(days)
    fv.to_csv(OUT / "fvg_classified.csv", index=False)
    tr = fv[fv.traded]
    other = tr[~tr.FP & ~tr.FPD & ~tr.FPR]
    groups = {"First presented (FP)": tr[tr.FP], "FP con desplazamiento (FPD)": tr[tr.FPD],
              "First presented reflection (FPR)": tr[tr.FPR],
              "FPR en macro (xx:50–xx:10)": tr[tr.FPR & tr.macro],
              "Resto de FVG (control)": other,
              "Resto con desplazamiento": other[other.displacement],
              "Resto sin desplazamiento": other[~other.displacement]}
    S["fvg_classes"] = {
        "fvgs_total": int(len(fv)), "fvgs_per_day_median": float(fv.groupby("date").size().median()),
        "pct_with_displacement": round(100 * float(fv.displacement.mean()), 1),
        "fpd_median_order": float(fv[fv.FPD].order.median()),
        "fpd_median_time": str(pd.to_datetime(fv[fv.FPD].time.astype(str).str[11:16], format="%H:%M").median().time()),
        "fpr_median_time": str(pd.to_datetime(fv[fv.FPR].time.astype(str).str[11:16], format="%H:%M").median().time()),
        "groups": {k: trade_stats(v) for k, v in groups.items()},
        "p_disp_vs_nodisp_win": two_prop_p(int((other[other.displacement].R_gross > 0).sum()), int(other.displacement.sum()),
                                           int((other[~other.displacement].R_gross > 0).sum()), int((~other.displacement).sum())),
    }

    # ---------------- gráficos
    figs(p1, p2, u, p3)
    fig_fvg(groups)
    (OUT / "summary.json").write_text(json.dumps(S, indent=1, default=str, ensure_ascii=False))
    print(json.dumps(S, indent=1, default=str, ensure_ascii=False)[:6000])


def figs(p1, p2, u, p3):
    plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False})
    C1, C2, CG = "#1f4e79", "#c0504d", "#9aa5b1"

    # Pilar 2: CE vs espejo por tamaño
    p2s = p2.groupby("size", observed=True)
    labels = [str(k) for k in p2s.groups]
    ce = [100 * v.ce_by_10.mean() for _, v in p2s]
    mi = [100 * v.mirror_by_10.mean() for _, v in p2s]
    fig, ax = plt.subplots(figsize=(7.5, 3.3), dpi=170)
    x = np.arange(len(labels))
    ax.bar(x - 0.18, ce, 0.36, color=C1, label="50 % del hueco (CE)")
    ax.bar(x + 0.18, mi, 0.36, color=CG, label="Nivel espejo (control)")
    ax.axhline(70, color=C2, ls="--", lw=1)
    ax.text(len(labels) - 0.5, 71.5, "70 % citado por ICT", color=C2, ha="right", fontsize=8)
    ax.set_xticks(x, labels)
    ax.set_ylabel("% de días alcanzado antes de las 10:00")
    ax.set_xlabel("Tamaño del hueco (% del precio)")
    ax.set_ylim(0, 105)
    ax.legend(frameon=False, fontsize=8, loc="upper right", bbox_to_anchor=(1, 0.92))
    fig.tight_layout(); fig.savefig(OUT / "p2_ce_vs_mirror.png"); plt.close(fig)

    # Pilar 2: proyecciones
    fig, ax = plt.subplots(figsize=(7.5, 3.0), dpi=170)
    ax.hist(u[(u > -0.5) & (u < 3)], bins=np.arange(-0.5, 3.01, 0.05), color=C1, alpha=0.85)
    ax.axvline(1.0, color=C2, ls="--", lw=1)
    ax.text(1.03, ax.get_ylim()[1] * 0.9, "−1 del hueco (nivel de ICT)", color=C2, fontsize=8)
    ax.set_xlabel("Extremo de la mañana, en múltiplos del hueco más allá de la apertura / del cierre")
    ax.set_ylabel("Frecuencia")
    fig.tight_layout(); fig.savefig(OUT / "p2_projections.png"); plt.close(fig)

    # Pilar 3: R neto por ventana
    names = list(p3.keys())
    means, lo, hi, ns = [], [], [], []
    for nme in names:
        df = p3[nme]
        tr = df[df.traded] if len(df) else df
        mc = mean_ci(tr.R_net.to_numpy()) if len(tr) else (np.nan,) * 3
        means.append(mc[0]); lo.append(mc[0] - mc[1]); hi.append(mc[2] - mc[0]); ns.append(len(tr))
    fig, ax = plt.subplots(figsize=(7.5, 3.2), dpi=170)
    cols = [C1 if "Silver" in n_ else CG for n_ in names]
    ax.bar(range(len(names)), means, color=cols, yerr=[lo, hi], capsize=3, ecolor="#444")
    ax.axhline(0, color="#333", lw=0.8)
    ax.set_xticks(range(len(names)), [f"{n_}\n(n={k})" for n_, k in zip(names, ns)], fontsize=7.5)
    ax.set_ylabel("R medio por operación (neto)")
    fig.tight_layout(); fig.savefig(OUT / "p3_by_window.png"); plt.close(fig)

    # Pilar 1: estado premarket vs mañana
    ct = pd.crosstab(p1["pm_state"], p1["am_state"], normalize="index") * 100
    fig, ax = plt.subplots(figsize=(7.5, 2.6), dpi=170)
    y = np.arange(len(ct.index))
    left = np.zeros(len(ct.index))
    for col, c in zip(ct.columns, [CG, C1]):
        ax.barh(y, ct[col], left=left, color=c, label=f"mañana: {col}")
        for yi, (l_, v) in enumerate(zip(left, ct[col])):
            ax.text(l_ + v / 2, yi, f"{v:.0f} %", ha="center", va="center", color="white", fontsize=8)
        left += ct[col].to_numpy()
    ax.set_yticks(y, [f"premarket: {i}" for i in ct.index])
    ax.set_xlim(0, 100); ax.set_xlabel("% de días")
    ax.legend(frameon=False, fontsize=8, ncol=2, loc="lower center", bbox_to_anchor=(0.5, 1.0))
    fig.tight_layout(); fig.savefig(OUT / "p1_states.png"); plt.close(fig)


def fig_fvg(groups):
    names = list(groups)
    m, lo, hi, ns = [], [], [], []
    for k in names:
        mc = mean_ci(groups[k].R_net.to_numpy())
        m.append(mc[0]); lo.append(mc[0] - mc[1]); hi.append(mc[2] - mc[0]); ns.append(len(groups[k]))
    fig, ax = plt.subplots(figsize=(7.5, 3.4), dpi=170)
    cols = ["#1f4e79" if "control" not in k and "Resto" not in k else "#9aa5b1" for k in names]
    ax.barh(range(len(names))[::-1], m, color=cols, xerr=[lo, hi], capsize=3, ecolor="#444")
    ax.axvline(0, color="#333", lw=0.8)
    ax.set_yticks(range(len(names))[::-1], [f"{k} (n={n})" for k, n in zip(names, ns)], fontsize=7.5)
    ax.set_xlabel("R medio por operación (neto), IC 95 %")
    for s_ in ("top", "right"):
        ax.spines[s_].set_visible(False)
    fig.tight_layout(); fig.savefig(OUT / "fvg_classes.png"); plt.close(fig)


if __name__ == "__main__":
    main()
