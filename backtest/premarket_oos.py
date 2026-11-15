"""Evaluación fuera de muestra (OOS) del setup "barrido del premarket -> extremo opuesto".

Las reglas están CONGELADAS: se llama directamente a ict_pillars.pillar1(), sin cambiar nada.
El periodo OOS (2021-01-01 a 2023-09-29) no se usó en el desarrollo (que fue 2023-10-01..2026-11-06).

Incluye:
  * verificación horaria de los datos de histdata (picos de volatilidad a las 08:30 y 09:30 NY en
    cada régimen de horario de verano EE. UU./Europa, incluidas las semanas en que no coinciden);
  * métricas OOS globales, por bloques consecutivos de 6 meses y por año;
  * probabilidades: objetivo alcanzado, P(esperanza > 0), Monte Carlo a 6 meses, win rate de
    equilibrio, sensibilidad a costes, subgrupos;
  * comparación con el periodo de desarrollo (in-sample) recalculado con el mismo código;
  * variantes de realismo (no sustituyen a la versión congelada): stop con hueco ejecutado en la
    apertura de la vela y vela ambigua resuelta a favor del objetivo (cota optimista).

Uso:  python3 backtest/premarket_oos.py      -> results/premarket_oos/
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
import ict_pillars as ip  # noqa: E402  reglas congeladas
from histdata_loader import load_minutes  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "premarket_oos"
OOS = ("2021-01-01", "2023-09-29")
IS = ("2023-10-01", "2026-11-06")
RNG = np.random.default_rng(2021)
N_BOOT = 20000
C1, C2, CG, C3 = "#1f4e79", "#c0504d", "#9aa5b1", "#5b8db8"


# --------------------------------------------------------------------------- verificación horaria
def regime(ts: pd.Timestamp) -> str:
    us = ts.dst() != pd.Timedelta(0)
    eu = ts.tz_convert("Europe/London").dst() != pd.Timedelta(0)
    if us and eu:
        return "verano EE. UU. y UE"
    if not us and not eu:
        return "invierno EE. UU. y UE"
    return "semanas desfasadas"


def tz_check(m: pd.DataFrame, keep_dates: set) -> tuple[dict, pd.DataFrame]:
    """|retorno de 1 min| medio por minuto del reloj de NY, por año y régimen de horario de verano.
    x_hh_mm = media del minuto / mediana de los minutos 07:00-11:00 (sin 08:30, 09:30, 10:00).
    open_x_hh = media de hh:30-hh:34 / media de hh:20-hh:29: el salto de la apertura de contado
    debe aparecer a las 09:30; si el reloj estuviera desplazado una hora, aparecería a las 08:30 o 10:30."""
    m = m[(m.index.weekday < 5) & pd.Index(m.index.date).isin(keep_dates)]
    ret = np.log(m["close"]).diff().abs() * 1e4          # pb
    gap_ok = m.index.to_series().diff() == pd.Timedelta(minutes=1)
    idx = m.index[gap_ok.to_numpy()]
    df = pd.DataFrame({"r": ret[gap_ok].to_numpy(), "t": idx.strftime("%H:%M"), "y": idx.year,
                       "d": idx.date})
    reg_by_day = {d: regime(pd.Timestamp(d).tz_localize("America/New_York") + pd.Timedelta(hours=12))
                  for d in set(df["d"])}
    df["reg"] = df["d"].map(reg_by_day)
    df = df[(df.t >= "07:00") & (df.t <= "11:00")]
    out = {}
    prof = df.groupby(["reg", "t"])["r"].mean().unstack(0)

    def win(s, a, b):
        return s[(s.index >= a) & (s.index <= b)].mean()

    for (y, rg), g in df.groupby(["y", "reg"]):
        s = g.groupby("t")["r"].mean()
        base = s.drop(["08:30", "09:30", "10:00"], errors="ignore").median()
        out[f"{y} · {rg}"] = {"days": int(g["d"].nunique()),
                              "x_08_30": float(s.get("08:30", np.nan) / base),
                              "x_09_30": float(s.get("09:30", np.nan) / base),
                              "open_x_08": float(win(s, "08:30", "08:34") / win(s, "08:20", "08:29")),
                              "open_x_09": float(win(s, "09:30", "09:34") / win(s, "09:20", "09:29")),
                              "open_x_10": float(win(s, "10:30", "10:34") / win(s, "10:20", "10:29")),
                              "top3": list(s.sort_values(ascending=False).index[:3])}
    return out, prof


# --------------------------------------------------------------------------- métricas
def max_dd(r: np.ndarray) -> float:
    if len(r) == 0:
        return 0.0
    eq = np.concatenate([[0.0], np.cumsum(r)])
    return float((eq - np.maximum.accumulate(eq)).min())


def longest_losing(r: np.ndarray) -> int:
    best = cur = 0
    for x in r:
        cur = cur + 1 if x < 0 else 0
        best = max(best, cur)
    return best


def pf(r: np.ndarray) -> float:
    gl = -r[r < 0].sum()
    return float(r[r > 0].sum() / gl) if gl > 0 else float("nan")


def boot_means(x: np.ndarray, n: int = N_BOOT) -> np.ndarray:
    return RNG.choice(x, size=(n, len(x)), replace=True).mean(axis=1)


def stats(t: pd.DataFrame, sessions: int | None = None) -> dict:
    if len(t) == 0:
        return {"n": 0}
    g, n_ = t["R_gross"].to_numpy(), t["R_net"].to_numpy()
    bg, bn = boot_means(g), boot_means(n_)
    win = ip.prop_ci(int((g > 0).sum()), len(g))
    tp = ip.prop_ci(int((t["exit"] == "TP").sum()), len(t))
    d = {"n": int(len(t)), "win_pct": win,
         "R_gross": float(g.mean()), "R_gross_ci": [float(np.percentile(bg, 2.5)), float(np.percentile(bg, 97.5))],
         "R_net": float(n_.mean()), "R_net_ci": [float(np.percentile(bn, 2.5)), float(np.percentile(bn, 97.5))],
         "p_net_gt0": float((bn > 0).mean()),
         "pf_gross": pf(g), "pf_net": pf(n_), "total_R_net": float(n_.sum()), "total_R_gross": float(g.sum()),
         "max_dd_net": max_dd(n_), "longest_losing": longest_losing(n_),
         "tp_pct": tp, "exits": {k: int(v) for k, v in t["exit"].value_counts().items()},
         "planned_rr_median": float(t["planned_rr"].median()), "risk_pts_median": float(t["risk_pts"].median())}
    if sessions:
        d["sessions"] = sessions
        d["trade_freq_pct"] = ip.prop_ci(len(t), sessions)
        d["tp_per_session_pct"] = ip.prop_ci(int((t["exit"] == "TP").sum()), sessions)
    return d


def t_one_sided(x: np.ndarray) -> tuple[float, float]:
    """t de Student unilateral H0: media <= 0 (aprox. normal para n grande)."""
    n, mu, sd = len(x), x.mean(), x.std(ddof=1)
    t = mu / (sd / math.sqrt(n))
    return float(t), float(0.5 * math.erfc(t / math.sqrt(2)))


def block_label(d, oos: bool = True) -> str:
    """Bloques semestrales consecutivos. En 2023 OOS solo hay 4 meses con datos completos
    (ene-feb y ago-sep), que forman un único bloque."""
    d = pd.Timestamp(d)
    if oos and d.year == 2023:
        return "2023 (4 m)"
    return f"{d.year}-S{1 if d.month <= 6 else 2}"


def six_month_mc(t: pd.DataFrame, allm: list, n_sims: int = 20000) -> dict:
    """Dos remuestreos de 6 meses de operativa (R neto):
    iid  -> se remuestrean operaciones; nº de operaciones = media observada por 6 meses;
    mes  -> bootstrap por bloques: se eligen 6 meses OOS con reemplazo y se encadenan sus operaciones
            (conserva la variación del nº de operaciones y la dependencia dentro del mes)."""
    r = t["R_net"].to_numpy()
    k = int(round(len(r) / len(allm) * 6))
    res = {}
    idx = RNG.integers(0, len(r), size=(n_sims, k))
    paths = r[idx]
    tot = paths.sum(1)
    eq = np.cumsum(paths, 1)
    dd = (eq - np.maximum.accumulate(np.maximum(eq, 0), axis=1)).min(1)
    res["iid"] = _mc_sum(tot, dd, k)
    months = t.assign(mo=pd.to_datetime(t["date"]).dt.to_period("M")).groupby("mo")["R_net"].apply(np.array)
    seqs = [months.get(p, np.array([])) for p in allm]
    tots, dds = np.empty(n_sims), np.empty(n_sims)
    pick = RNG.integers(0, len(seqs), size=(n_sims, 6))
    for s in range(n_sims):
        p = np.concatenate([seqs[j] for j in pick[s]])
        tots[s] = p.sum()
        e = np.concatenate([[0], np.cumsum(p)])
        dds[s] = (e - np.maximum.accumulate(e)).min()
    res["mes"] = _mc_sum(tots, dds, None)
    res["_tot_iid"], res["_tot_mes"] = tot, tots
    return res


def _mc_sum(tot, dd, k):
    return {"trades_per_6m": k, "p_positive": float((tot > 0).mean()),
            "median": float(np.median(tot)), "p5": float(np.percentile(tot, 5)),
            "p95": float(np.percentile(tot, 95)), "mean": float(tot.mean()),
            "p_dd_worse_10R": float((dd < -10).mean()),
            "p_dd_worse_20R": float((dd < -20).mean()), "p_total_below_m20R": float((tot < -20).mean()), "dd_median": float(np.median(dd))}


def break_even(t: pd.DataFrame) -> dict:
    out = {}
    for col in ("R_gross", "R_net"):
        r = t[col].to_numpy()
        w, l_ = r[r > 0], r[r <= 0]
        aw, al = w.mean(), -l_.mean()
        out[col] = {"avg_win": float(aw), "avg_loss": float(al), "win_pct": float(100 * len(w) / len(r)),
                    "be_win_pct": float(100 * al / (aw + al))}
    return out


# --------------------------------------------------------------------------- variantes de realismo
def resim(days_by_date: dict, t: pd.DataFrame, gap_fill: bool, target_first: bool) -> pd.DataFrame:
    """Repite la salida de cada operación (mismas entradas) con otra convención de ejecución.
    Con gap_fill=False y target_first=False reproduce exactamente ip.simulate (se comprueba)."""
    out = []
    for _, tr in t.iterrows():
        g = days_by_date[tr["date"]].between_time("09:30", "15:59")
        b = g[g.index > tr["entry_time"]]
        side = 1 if tr["side"] == "long" else -1
        e, s, tg, risk = tr["entry"], tr["stop"], tr["target"], tr["risk_pts"]
        R, why, amb = None, "EOD", False
        for o, h, lo in zip(b["open"].to_numpy(), b["high"].to_numpy(), b["low"].to_numpy()):
            hs = lo <= s if side > 0 else h >= s
            ht = h >= tg if side > 0 else lo <= tg
            amb |= hs and ht
            if hs and not (ht and target_first):
                fill = s
                if gap_fill and ((side > 0 and o < s) or (side < 0 and o > s)):
                    fill = o
                R, why = side * (fill - e) / risk, "SL"
                break
            if ht:
                R, why = abs(tg - e) / risk, "TP"
                break
        if R is None:
            R = side * (b["close"].iloc[-1] - e) / risk
        out.append({"R_gross": R, "R_net": R - ip.COST_PTS / risk, "exit": why, "ambiguous": amb})
    return pd.DataFrame(out, index=t.index)


def touched_target_any(days_by_date: dict, t: pd.DataFrame) -> np.ndarray:
    """¿Toca el precio el extremo opuesto en algún momento antes de las 16:00 (aunque antes salte el stop)?"""
    res = []
    for _, tr in t.iterrows():
        g = days_by_date[tr["date"]].between_time("09:30", "15:59")
        b = g[g.index > tr["entry_time"]]
        res.append(bool((b["high"] >= tr["target"]).any() if tr["side"] == "long" else (b["low"] <= tr["target"]).any()))
    return np.array(res)


def diff_p(a: np.ndarray, b: np.ndarray, n: int = 20000) -> float:
    """p bilateral por permutación para diferencia de medias."""
    x = np.concatenate([a, b])
    obs = abs(a.mean() - b.mean())
    cnt = 0
    for _ in range(n // 1000):
        P = np.array([RNG.permutation(x) for _ in range(1000)])
        cnt += int((np.abs(P[:, :len(a)].mean(1) - P[:, len(a):].mean(1)) >= obs).sum())
    return (cnt + 1) / (n + 1)


# --------------------------------------------------------------------------- gráficos
def style():
    plt.rcParams.update({"font.size": 8.5, "axes.spines.top": False, "axes.spines.right": False,
                         "axes.edgecolor": "#888", "axes.grid": True, "grid.color": "#e6e6e6",
                         "grid.linewidth": 0.6})


def _gap_nan(d: pd.Series, y: pd.Series, gap_days: int = 45):
    """Corta la línea donde faltan datos (> gap_days sin operaciones)."""
    d, y = d.reset_index(drop=True), y.reset_index(drop=True)
    br = np.where(d.diff().dt.days > gap_days)[0]
    for k in br[::-1]:
        d = pd.concat([d.iloc[:k], pd.Series([d.iloc[k - 1] + pd.Timedelta(days=1)]), d.iloc[k:]], ignore_index=True)
        y = pd.concat([y.iloc[:k], pd.Series([np.nan]), y.iloc[k:]], ignore_index=True)
    return d, y, br


def fig_equity(t: pd.DataFrame, path: Path):
    d = pd.to_datetime(t["date"])
    fig, ax = plt.subplots(figsize=(7.6, 3.2), dpi=170)
    ax.set_axisbelow(True)
    blocks = d.map(block_label)
    for i, (bl, g) in enumerate(d.groupby(blocks, sort=False)):
        if i % 2 == 0:
            ax.axvspan(g.min(), g.max(), color="#f1f4f8", lw=0, zorder=0)
        ax.text(g.min() + (g.max() - g.min()) / 2, 1.0, bl, transform=ax.get_xaxis_transform(),
                ha="center", va="bottom", fontsize=7, color="#555")
    dg, yg, br = _gap_nan(d, t["R_gross"].cumsum())
    dn, yn, _ = _gap_nan(d, t["R_net"].cumsum())
    for k in br:
        ax.axvspan(d.iloc[k - 1], d.iloc[k], color="white", hatch="///", ec="#cccccc", lw=0, zorder=0.5)
        ax.text(d.iloc[k - 1] + (d.iloc[k] - d.iloc[k - 1]) / 2, 0.06, "sin datos\nfiables", transform=ax.get_xaxis_transform(),
                ha="center", fontsize=7, color="#777")
    ax.plot(dg, yg, color=CG, lw=1.6, label="Bruto")
    ax.plot(dn, yn, color=C1, lw=2, label="Neto (1 punto por operación)")
    ax.axhline(0, color="#333", lw=0.8)
    ax.set_ylabel("R acumulado")
    ax.legend(frameon=False, loc="lower left", fontsize=8, bbox_to_anchor=(0.0, 0.12))
    fig.tight_layout(); fig.savefig(path); plt.close(fig)


def fig_full(t_oos, t_is, path):
    t = pd.concat([t_oos.assign(p="OOS"), t_is.assign(p="IS")])
    d = pd.to_datetime(t["date"])
    fig, ax = plt.subplots(figsize=(7.6, 2.8), dpi=170)
    eq = t["R_net"].cumsum().to_numpy()
    m = (t["p"] == "OOS").to_numpy()
    dg, yg, _ = _gap_nan(d[m], pd.Series(eq[m]))
    ax.plot(dg, yg, color=C1, lw=2, label="Fuera de muestra (2021–2023)")
    ax.plot(d[~m], eq[~m], color=CG, lw=2, label="Desarrollo / in-sample (2023–2026)")
    ax.axvline(pd.Timestamp(IS[0]), color="#333", lw=0.8, ls="--")
    ax.axhline(0, color="#333", lw=0.8)
    ax.set_ylabel("R neto acumulado")
    ax.legend(frameon=False, loc="upper left", fontsize=8)
    fig.tight_layout(); fig.savefig(path); plt.close(fig)


def fig_blocks(rows: list[dict], path: Path):
    fig, ax = plt.subplots(figsize=(7.6, 3.0), dpi=170)
    ax.set_axisbelow(True)
    x = np.arange(len(rows))
    m = [r["R_net"] for r in rows]
    lo = [r["R_net"] - r["R_net_ci"][0] for r in rows]
    hi = [r["R_net_ci"][1] - r["R_net"] for r in rows]
    is_ = ["(IS)" in r["label"] for r in rows]
    cols = [CG if k else C1 for k in is_]
    ax.bar(x, m, 0.6, color=cols, yerr=[lo, hi], capsize=3, ecolor="#444", error_kw={"lw": 0.8})
    ax.axhline(0, color="#333", lw=0.8)
    cut = is_.index(True) - 0.5
    ax.axvline(cut, color="#333", lw=0.8, ls="--")
    ax.text(cut - 0.15, 0.97, "fuera de muestra", ha="right", va="top", transform=ax.get_xaxis_transform(), fontsize=8, color=C1)
    ax.text(cut + 0.15, 0.97, "desarrollo (in-sample)", ha="left", va="top", transform=ax.get_xaxis_transform(), fontsize=8, color="#666")
    lab = [r["label"].replace(" (IS)", "").replace("2023 (4 m)", "2023\n(4 meses)") for r in rows]
    ax.set_xticks(x, [f"{a}\nn={r['n']}" for a, r in zip(lab, rows)], fontsize=6.8)
    ax.set_ylabel("R neto medio (IC 95 %)")
    ax.grid(axis="x", visible=False)
    fig.tight_layout(); fig.savefig(path); plt.close(fig)


def fig_mc(tot_iid, tot_mes, path):
    fig, ax = plt.subplots(figsize=(7.6, 2.8), dpi=170)
    ax.set_axisbelow(True)
    bins = np.linspace(min(tot_iid.min(), tot_mes.min()), max(tot_iid.max(), tot_mes.max()), 70)
    ax.hist(tot_mes, bins=bins, color=C1, alpha=0.75, label="Bootstrap por meses")
    ax.hist(tot_iid, bins=bins, histtype="step", color=C2, lw=1.4, label="Remuestreo de operaciones")
    ax.axvline(0, color="#333", lw=0.9)
    ax.set_xlabel("R neto total tras 6 meses")
    ax.set_ylabel("Simulaciones")
    ax.legend(frameon=False, fontsize=8)
    ax.grid(axis="x", visible=False)
    fig.tight_layout(); fig.savefig(path); plt.close(fig)


def fig_tz(prof: pd.DataFrame, path: Path):
    fig, ax = plt.subplots(figsize=(7.6, 2.7), dpi=170)
    cols = {"invierno EE. UU. y UE": C1, "verano EE. UU. y UE": CG, "semanas desfasadas": C2}
    x = pd.to_datetime(prof.index, format="%H:%M")
    for c in prof.columns:
        ax.plot(x, prof[c], lw=1.1 if c != "semanas desfasadas" else 1.4, color=cols.get(c, "#555"), label=c)
    ax.set_ylabel("|retorno 1 min| medio (pb)")
    ax.xaxis.set_major_formatter(matplotlib.dates.DateFormatter("%H:%M"))
    ax.set_xlabel("Hora de Nueva York (tras la conversión del cargador)")
    ax.legend(frameon=False, fontsize=7.5, loc="upper left")
    fig.tight_layout(); fig.savefig(path); plt.close(fig)


# --------------------------------------------------------------------------- principal
def r3(x):
    if isinstance(x, dict):
        return {k: r3(v) for k, v in x.items() if not str(k).startswith("_")}
    if isinstance(x, (list, tuple)):
        return [r3(v) for v in x]
    if isinstance(x, (float, np.floating)):
        return None if x != x else round(float(x), 4)
    if isinstance(x, np.integer):
        return int(x)
    return x


MIN_BARS = 530        # sesión "completa": >= 530 de las 540 velas de 07:00 a 15:59
MIN_FULL_PER_MONTH = 10


def complete_days(days: list[dict]) -> tuple[list[dict], dict]:
    """Filtro de CALIDAD DE DATOS (no de reglas): histdata tiene huecos masivos en NSXUSD de
    finales de feb. a jul. de 2023 (solo ~45-55 % de las velas). Se conservan las sesiones con
    >= MIN_BARS velas entre 07:00 y 15:59, en meses con >= MIN_FULL_PER_MONTH sesiones así."""
    nb = {d["date"]: len(d["bars"].between_time("07:00", "15:59")) for d in days}
    full = [d for d in days if nb[d["date"]] >= MIN_BARS]
    per_m = pd.Series([pd.Period(d["date"], "M") for d in full]).value_counts()
    ok_m = set(per_m[per_m >= MIN_FULL_PER_MONTH].index)
    keep = [d for d in full if pd.Period(d["date"], "M") in ok_m]
    allp = pd.Series([pd.Period(d["date"], "M") for d in days])
    info = {"sessions_raw": len(days), "sessions_kept": len(keep),
            "sessions_incomplete": len(days) - len(full),
            "months_kept": sorted(str(p) for p in ok_m),
            "months_dropped": sorted(str(p) for p in set(allp) - ok_m),
            "median_bars_by_month": {str(k): float(v) for k, v in
                                     pd.Series(list(nb.values()), index=allp).groupby(level=0).median().items()}}
    return keep, info


def analyze(days: list[dict], months: list, oos: bool = True, extra: bool = True) -> tuple[dict, pd.DataFrame]:
    p1, t, _ = ip.pillar1(days)
    by_date = {d["date"]: d["bars"] for d in days}
    t = t.sort_values("entry_time").reset_index(drop=True)
    t["block"] = t["date"].map(lambda d: block_label(d, oos))
    t["year"] = pd.to_datetime(t["date"]).dt.year
    S = stats(t, len(p1))
    S["t_test"] = t_one_sided(t["R_net"].to_numpy())
    S["p_boot_one_sided"] = 1 - S["p_net_gt0"]
    S["blocks"] = []
    for bl, g in t.groupby("block", sort=False):
        st = stats(g)
        st["label"] = bl if oos else bl + " (IS)"
        S["blocks"].append(st)
    S["years"] = {str(y): stats(g) for y, g in t.groupby("year")}
    S["subgroups"] = {"long": stats(t[t.side == "long"]), "short": stats(t[t.side == "short"]),
                      "tendencia": stats(t[t.pm_state == "tendencia"]),
                      "consolidación": stats(t[t.pm_state == "consolidación"])}
    mc = six_month_mc(t, months)
    S["mc_6m"] = mc
    rs = np.sort(t["R_net"].to_numpy())[::-1]
    S["outliers"] = {"top5_R_net": [float(x) for x in rs[:5]], "mean_excl_top1": float(rs[1:].mean()),
                     "mean_excl_top3": float(rs[3:].mean()), "median_R_net": float(np.median(rs)),
                     "n_risk_lt5pts": int((t["risk_pts"] < 5).sum()),
                     "share_total_from_top5": float(rs[:5].sum() / rs.sum()) if rs.sum() != 0 else None}
    if not extra:
        return S, t
    t["touched_target_any"] = touched_target_any(by_date, t)
    S["touched_target_any_pct"] = ip.prop_ci(int(t["touched_target_any"].sum()), len(t))
    S["blocks_positive"] = int(sum(b["R_net"] > 0 for b in S["blocks"]))
    S["blocks_ci_above0"] = int(sum(b["R_net_ci"][0] > 0 for b in S["blocks"]))
    S["blocks_ci_below0"] = int(sum(b["R_net_ci"][1] < 0 for b in S["blocks"]))
    mo = t.assign(mo=pd.to_datetime(t["date"]).dt.to_period("M")).groupby("mo")["R_net"].sum()
    mo = mo.reindex(months, fill_value=0.0)
    S["monthly"] = {str(p): float(v) for p, v in mo.items()}
    S["months_positive"] = [int((mo > 0).sum()), int(len(mo))]
    S["break_even"] = break_even(t)
    S["costs"] = {}
    for c in (0.0, 0.5, 1.0, 2.0):
        r = (t["R_gross"] - c / t["risk_pts"]).to_numpy()
        b = boot_means(r)
        S["costs"][str(c)] = {"R": float(r.mean()), "ci": [float(np.percentile(b, 2.5)), float(np.percentile(b, 97.5))],
                              "p_gt0": float((b > 0).mean())}
    S["subgroups"]["p_short_vs_long"] = diff_p(t.loc[t.side == "short", "R_net"].to_numpy(),
                                               t.loc[t.side == "long", "R_net"].to_numpy())
    S["subgroups"]["p_trend_vs_consol"] = diff_p(t.loc[t.pm_state == "tendencia", "R_net"].to_numpy(),
                                                 t.loc[t.pm_state == "consolidación", "R_net"].to_numpy())
    # variantes de ejecución (la versión congelada sigue siendo la principal)
    base = resim(by_date, t, gap_fill=False, target_first=False)
    S["resim_matches_frozen"] = bool(np.allclose(base["R_gross"], t["R_gross"]) and (base["exit"] == t["exit"]).all())
    t["ambiguous_bar"] = base["ambiguous"].to_numpy()
    gapv = resim(by_date, t, gap_fill=True, target_first=False)
    optv = resim(by_date, t, gap_fill=False, target_first=True)
    t["R_net_gapfill"] = gapv["R_net"].to_numpy()
    t["R_net_target_first"] = optv["R_net"].to_numpy()
    S["variants"] = {"ambiguous_bars": int(t["ambiguous_bar"].sum()),
                     "stop_gaps": int((gapv["R_gross"] < -1 - 1e-9).sum()),
                     "gap_fill": stats(t.assign(R_gross=gapv["R_gross"], R_net=gapv["R_net"], exit=gapv["exit"])),
                     "target_first": stats(t.assign(R_gross=optv["R_gross"], R_net=optv["R_net"], exit=optv["exit"]))}
    return S, t


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    style()
    S = {"rules": "ict_pillars.pillar1() sin cambios (congelado)", "cost_pts": ip.COST_PTS, "tick": ip.TICK,
         "quality_filter": {"min_bars_07_16": MIN_BARS, "min_full_sessions_per_month": MIN_FULL_PER_MONTH}}

    # ---------------- OOS
    m = load_minutes(*OOS)
    days_raw = ip.build_days(m)
    days, qinfo = complete_days(days_raw)
    S["data"] = {"period": list(OOS), "first": str(days[0]["date"]), "last": str(days[-1]["date"]), **qinfo}
    tzc, prof = tz_check(m, {d["date"] for d in days})
    S["tz_check"] = tzc
    fig_tz(prof, OUT / "tz_check.png")

    months = [pd.Period(x, "M") for x in qinfo["months_kept"]]
    S["oos"], t = analyze(days, months)
    t.to_csv(OUT / "trades_oos.csv", index=False)
    # sensibilidad: todas las sesiones que acepta el código congelado (incluidos días con huecos)
    allm = sorted({pd.Period(d["date"], "M") for d in days_raw})
    S["oos_all_sessions"], t_all = analyze(days_raw, allm, extra=False)
    t_all.to_csv(OUT / "trades_oos_all_sessions.csv", index=False)

    # ---------------- in-sample recalculado con el mismo código (sin filtro, como en el desarrollo)
    mi = load_minutes(*IS)
    di = ip.build_days(mi)
    mis = sorted({pd.Period(d["date"], "M") for d in di})
    S["is"], ti = analyze(di, mis, oos=False, extra=False)
    ti.to_csv(OUT / "trades_is.csv", index=False)
    dic, qi = complete_days(di)
    S["is_quality"] = {k: qi[k] for k in ("sessions_raw", "sessions_kept", "sessions_incomplete", "months_dropped")}
    S["is_complete_only"], _ = analyze(dic, [pd.Period(x, "M") for x in qi["months_kept"]], oos=False, extra=False)
    cols = ["date", "R_gross", "R_net", "exit", "planned_rr", "risk_pts", "side", "pm_state"]
    S["all_2021_2026"] = stats(pd.concat([t[cols], ti[cols]]))

    # ---------------- gráficos
    fig_equity(t, OUT / "equity_oos.png")
    fig_full(t, ti, OUT / "equity_oos_is.png")
    fig_blocks(S["oos"]["blocks"] + S["is"]["blocks"], OUT / "blocks.png")
    fig_mc(S["oos"]["mc_6m"]["_tot_iid"], S["oos"]["mc_6m"]["_tot_mes"], OUT / "mc_6m.png")

    (OUT / "summary.json").write_text(json.dumps(r3(S), indent=1, ensure_ascii=False, default=str))
    for name in ("oos", "oos_all_sessions", "is", "is_complete_only"):
        o = S[name]
        print(f"{name:18s} n={o['n']} win={o['win_pct'][0]:.1f}% gross={o['R_gross']:+.3f} net={o['R_net']:+.3f} "
              f"[{o['R_net_ci'][0]:+.3f}; {o['R_net_ci'][1]:+.3f}] P(>0)={o['p_net_gt0']:.3f} TP={o['tp_pct'][0]:.1f}%")
    for b in S["oos"]["blocks"] + S["is"]["blocks"]:
        print(f"  {b['label']:14s} n={b['n']:3d} net={b['R_net']:+.3f} [{b['R_net_ci'][0]:+.2f}; {b['R_net_ci'][1]:+.2f}]")
    print("resim ok:", S["oos"]["resim_matches_frozen"])


if __name__ == "__main__":
    main()
