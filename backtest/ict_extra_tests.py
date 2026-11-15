"""Pruebas adicionales de reglas de ICT ("Trading premarket and regular session liquidity", 18/09/2025).

A. Lunch macro: en días alcistas, entre 11:30 y 13:00 el precio busca la primera sell-side liquidity
   destacada formada después de las 10:00 (y, en días bajistas, la buy side). Control: la liquidez
   del lado contrario, comparada a igual distancia.
B. Jueves: en semanas alcistas el máximo semanal se forma el jueves o es un máximo falso que se
   rompe el viernes. Control: mismas semanas con el orden de los días permutado al azar.
C. Premarket antes de las 08:30: barrido de un extremo del rango 07:00-08:29 entre 08:30 y 09:29 y
   objetivo en el extremo opuesto.

Uso:  python3 backtest/ict_extra_tests.py   -> results/ict_pillars/extra_summary.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ict_pillars as ip  # noqa: E402

OUT = ip.OUT
RNG = np.random.default_rng(11)


def fractal_points(b: pd.DataFrame, k: int = 5):
    h, l = b["high"].to_numpy(), b["low"].to_numpy()
    highs = [(b.index[i], h[i]) for i in range(k, len(b) - k) if h[i] == h[i - k:i + k + 1].max()]
    lows = [(b.index[i], l[i]) for i in range(k, len(b) - k) if l[i] == l[i - k:i + k + 1].min()]
    return highs, lows


# --------------------------------------------------------------------------- A. lunch macro
def lunch_macro(days):
    rows = []
    for d in days:
        g = d["bars"]
        morning = g.between_time("09:55", "11:29")
        lunch = g.between_time("11:30", "12:59")
        if len(morning) < 90 or len(lunch) < 85:
            continue
        o930 = float(g.between_time("09:30", "09:30")["open"].iloc[0])
        px = float(morning["close"].iloc[-1])
        bull = px > o930
        highs, lows = fractal_points(morning)
        after = morning[morning.index >= morning.index[0].replace(hour=10, minute=0)]

        def first_pending(points, is_high):
            for t, v in points:
                if t.hour < 10:
                    continue
                later = morning[morning.index > t]
                taken = (later["high"] > v).any() if is_high else (later["low"] < v).any()
                if not taken:
                    return v
            return None

        ssl, bsl = first_pending(lows, False), first_pending(highs, True)
        for lvl, kind in [(ssl, "SSL"), (bsl, "BSL")]:
            if lvl is None:
                continue
            hit = (lunch["low"] <= lvl).any() if kind == "SSL" else (lunch["high"] >= lvl).any()
            rows.append({"date": d["date"], "bull": bull, "kind": kind,
                         "counter": (kind == "SSL") == bull,   # liquidez contraria al sesgo del día
                         "dist_pct": 100 * abs(px - lvl) / px, "hit": bool(hit)})
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------- B. jueves
def thursday(days):
    rth = []
    for d in days:
        b = d["bars"].between_time("09:30", "16:14")
        rth.append({"date": pd.Timestamp(d["date"]), "open": b["open"].iloc[0], "high": b["high"].max(),
                    "low": b["low"].min(), "close": b["close"].iloc[-1]})
    df = pd.DataFrame(rth).set_index("date")
    df["wk"] = df.index.to_period("W-SUN")
    res, perm = [], []
    for wk, w in df.groupby("wk"):
        if len(w) != 5 or list(w.index.weekday) != [0, 1, 2, 3, 4]:
            continue
        up = w["close"].iloc[-1] > w["open"].iloc[0]
        hi_day = int(np.argmax(w["high"].to_numpy()))
        lo_day = int(np.argmin(w["low"].to_numpy()))
        thu_high_so_far = w["high"].iloc[3] >= w["high"].iloc[:4].max()
        fri_breaks = w["high"].iloc[4] > w["high"].iloc[3]
        res.append({"week": str(wk), "up": up, "high_day": hi_day, "low_day": lo_day,
                    "thu_high_so_far": thu_high_so_far, "fri_breaks_thu": fri_breaks})
        # control: permutar el orden de los días (mismos movimientos, otro orden)
        prev = np.r_[w["open"].iloc[0], w["close"].to_numpy()[:-1]]
        rel_h = w["high"].to_numpy() - prev
        rel_c = w["close"].to_numpy() - prev
        for _ in range(200):
            p = RNG.permutation(5)
            base = np.r_[0, np.cumsum(rel_c[p])[:-1]]
            hh = base + rel_h[p]
            perm.append({"up": up, "high_day": int(np.argmax(hh)),
                         "thu_high_so_far": hh[3] >= hh[:4].max(), "fri_breaks_thu": hh[4] > hh[3]})
    return pd.DataFrame(res), pd.DataFrame(perm)


# --------------------------------------------------------------------------- C. premarket pre-08:30
def pre830(days):
    trades = []
    for d in days:
        g = d["bars"]
        pm = g.between_time("07:00", "08:29")
        win = g.between_time("08:30", "11:59")
        if len(pm) < 85 or len(win) < 200:
            continue
        ph, pl = pm["high"].max(), pm["low"].min()
        ext_h, ext_l = -np.inf, np.inf
        for i, (ts, r) in enumerate(win.iterrows()):
            if ts.hour >= 9 and ts.minute >= 30 or ts.hour >= 10:
                break
            ext_h, ext_l = max(ext_h, r["high"]), min(ext_l, r["low"])
            side = 0
            if ext_h > ph and r["close"] < ph:
                side, entry, stop, target = -1, r["close"], ext_h + ip.TICK, pl
            elif ext_l < pl and r["close"] > pl:
                side, entry, stop, target = 1, r["close"], ext_l - ip.TICK, ph
            if side:
                if (target - entry) * side <= 0:
                    break
                R, why, _ = ip.simulate(win.iloc[i + 1:], side, entry, stop, target, False)
                risk = abs(entry - stop)
                trades.append({"date": d["date"], "side": "long" if side > 0 else "short", "R_gross": R,
                               "R_net": R - ip.COST_PTS / risk, "exit": why, "risk_pts": risk,
                               "planned_rr": abs(target - entry) / risk})
                break
    return pd.DataFrame(trades)


def main():
    m = ip.load_minutes(ip.START, ip.END)
    days = ip.build_days(m)
    S = {}

    # A
    lm = lunch_macro(days)
    lm.to_csv(OUT / "extra_lunch_macro.csv", index=False)
    lm["bucket"] = pd.cut(lm["dist_pct"], [0, 0.1, 0.2, 0.4, 5])
    rows = []
    for bkt, gb in lm.groupby("bucket", observed=True):
        c, w = gb[gb.counter], gb[~gb.counter]
        rows.append({"dist_pct": str(bkt), "n_counter": len(c), "hit_counter": ip.prop_ci(int(c.hit.sum()), len(c)),
                     "n_with": len(w), "hit_with": ip.prop_ci(int(w.hit.sum()), len(w)),
                     "p": ip.two_prop_p(int(c.hit.sum()), len(c), int(w.hit.sum()), len(w))})
    bull_ssl = lm[lm.bull & (lm.kind == "SSL")]
    bear_ssl = lm[~lm.bull & (lm.kind == "SSL")]
    S["lunch_macro"] = {
        "days": int(lm.date.nunique()),
        "bull_days_ssl_hit": ip.prop_ci(int(bull_ssl.hit.sum()), len(bull_ssl)),
        "bull_days_ssl_dist_median": float(bull_ssl.dist_pct.median()),
        "counter_vs_with_by_distance": rows,
    }

    # B
    wk, perm = thursday(days)
    wk.to_csv(OUT / "extra_weeks.csv", index=False)
    up, upp = wk[wk.up], perm[perm.up]
    names = ["lunes", "martes", "miércoles", "jueves", "viernes"]
    S["thursday"] = {
        "weeks": int(len(wk)), "up_weeks": int(len(up)),
        "up_week_high_day_pct": {names[i]: round(100 * float((up.high_day == i).mean()), 1) for i in range(5)},
        "perm_high_day_pct": {names[i]: round(100 * float((upp.high_day == i).mean()), 1) for i in range(5)},
        "thu_or_fri_high": ip.prop_ci(int(up.high_day.isin([3, 4]).sum()), len(up)),
        "thu_or_fri_high_perm_pct": round(100 * float(upp.high_day.isin([3, 4]).mean()), 1),
        "fri_breaks_thu_given_thu_high": ip.prop_ci(int((up.thu_high_so_far & up.fri_breaks_thu).sum()),
                                                    int(up.thu_high_so_far.sum())),
        "fri_breaks_thu_given_thu_high_perm_pct": round(100 * float(
            (upp.thu_high_so_far & upp.fri_breaks_thu).sum() / upp.thu_high_so_far.sum()), 1),
    }

    # C
    t = pre830(days)
    t.to_csv(OUT / "extra_pre830_trades.csv", index=False)
    S["pre830"] = {"all": ip.trade_stats(t), "long": ip.trade_stats(t[t.side == "long"]),
                   "short": ip.trade_stats(t[t.side == "short"])}

    (OUT / "extra_summary.json").write_text(json.dumps(S, indent=1, default=str, ensure_ascii=False))
    print(json.dumps(S, indent=1, default=str, ensure_ascii=False))


if __name__ == "__main__":
    main()
