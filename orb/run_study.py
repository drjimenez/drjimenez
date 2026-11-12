"""
run_study.py — Construye la base de datos ORB, calcula probabilidades, prueba reglas Fibonacci
(in-sample vs out-of-sample) y genera tablas, gráficos e informe en orb/results/.

Uso:
    python3 orb/run_study.py                                   # datos Binance (QQQUSDT, SPYUSDT)
    python3 orb/run_study.py --csv NAS100=ruta.csv --tz Europe/Athens   # datos de tu bróker
"""
from __future__ import annotations

import argparse
import itertools
import json
import os
import sys

import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config as C  # noqa: E402
import database as db  # noqa: E402
import engine as E  # noqa: E402

RES = db.results_dir()
lv = E._lvl

# Paleta (paleta de referencia del skill dataviz, modo claro; la misma que el resto del repo)
SURFACE, INK, INK2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
BLUE, ORANGE, GREEN, AMBER = "#2a78d6", "#eb6834", "#1baf7a", "#eda100"
SESSION_COLOR = {"London": BLUE, "NewYork": ORANGE}
SEQ = LinearSegmentedColormap.from_list("seq", ["#f3f7fd", "#9cc1ef", "#2a78d6", "#0f3f80"])
DIV = LinearSegmentedColormap.from_list("div", ["#c2441a", "#f4b597", "#efeeec", "#9cc1ef", "#1c5fb0"])
plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "axes.edgecolor": GRID, "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
    "text.color": INK, "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6,
    "axes.spines.top": False, "axes.spines.right": False, "font.size": 9, "lines.linewidth": 2,
    "legend.frameon": False,
})


def pct(s) -> float:
    s = pd.Series(s).dropna()
    return round(100.0 * s.astype(float).mean(), 1) if len(s) else np.nan


def rule_label(r) -> str:
    e = "ruptura" if r.entry == "break" else None
    if r.model == "continuacion":
        e = e or f"límite retroceso {float(r.entry):g}"
        return f"{r.session} OR{r.or_min} · continuación: entrada {e}, stop ret {r.stop:g}, obj ext {C.EXT_LABEL[r.target]}"
    e = e or f"límite ext {C.EXT_LABEL[float(r.entry)]}"
    return f"{r.session} OR{r.or_min} · reversión: entrada {e}, stop ext {C.EXT_LABEL[r.stop]}, obj ret {r.target:g}"


# --------------------------------------------------------------------------------------------
# 1. Probabilidades descriptivas
# --------------------------------------------------------------------------------------------

def breakout_table(ev: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (ses, n, sym), g in ev.groupby(["session", "or_min", "symbol"]):
        b = g[g.break_dir != "none"]
        rows.append({
            "session": ses, "or_min": n, "symbol": sym, "days": len(g),
            "range_bp_median": round(g.or_range_bp.median(), 1),
            "pct_up": pct(g.break_dir == "up"), "pct_down": pct(g.break_dir == "down"),
            "pct_no_break": pct(g.break_dir == "none"),
            "min_to_break_median": b.min_to_break.median(),
            "pct_retest_level": pct(b.retest),
            "pct_no_retest": pct(~b.retest.astype(bool)),
            "pct_failed_opposite": pct(b.opposite_break),
            "pct_close_beyond_level": pct(b.close_x > 0),
        })
    return pd.DataFrame(rows)


def retrace_ext_table(ev: pd.DataFrame, by=("session", "or_min")) -> pd.DataFrame:
    b = ev[ev.break_dir != "none"]
    rows = []
    for key, g in b.groupby(list(by)):
        r = dict(zip(by, key if isinstance(key, tuple) else (key,)))
        r["breaks"] = len(g)
        for lvl in C.RETRACE_LEVELS:
            r[f"ret_{lvl:g}"] = pct(g[f"t_ret_{lv(lvl)}"].notna())
        for e in C.EXT_LEVELS:
            r[f"ext_{C.EXT_LABEL[e]}"] = pct(g[f"t_ext_{lv(e)}"].notna())
        rows.append(r)
    return pd.DataFrame(rows)


def ext_before_retrace(g: pd.DataFrame) -> pd.DataFrame:
    """P(alcanzar la extensión E ANTES de retroceder al nivel F) — empate en el mismo minuto = retroceso."""
    m = pd.DataFrame(index=[C.EXT_LABEL[e] for e in C.EXT_LEVELS],
                     columns=[f"{r:g}" for r in C.RETRACE_LEVELS], dtype=float)
    for e in C.EXT_LEVELS:
        te = g[f"t_ext_{lv(e)}"]
        for r in C.RETRACE_LEVELS:
            tr = g[f"t_ret_{lv(r)}"]
            ok = te.notna() & (tr.isna() | (te < tr))
            m.loc[C.EXT_LABEL[e], f"{r:g}"] = 100 * ok.mean()
    return m


def depth_buckets(g: pd.DataFrame) -> pd.Series:
    """Distribución del retroceso máximo tras la ruptura, por tramos Fibonacci."""
    edges = [-np.inf, 0, 0.236, 0.382, 0.5, 0.618, 0.786, 1.0, np.inf]
    labels = ["sin retest", "0–23.6", "23.6–38.2", "38.2–50", "50–61.8", "61.8–78.6",
              "78.6–100", ">100 (extremo opuesto)"]
    cut = pd.cut(g.max_retrace, edges, labels=labels, right=False)
    return (100 * cut.value_counts(normalize=True)).reindex(labels).round(1)


def conditional_table(ev: pd.DataFrame) -> pd.DataFrame:
    """Probabilidades condicionadas por dirección, tamaño del rango y tiempo hasta la ruptura."""
    b = ev[ev.break_dir != "none"].copy()
    b["range_tercile"] = b.groupby(["session", "or_min", "symbol"]).or_range_bp.transform(
        lambda s: pd.qcut(s, 3, labels=["pequeño", "medio", "grande"]))
    b["break_speed"] = np.where(b.min_to_break <= 5, "≤5 min", ">5 min")
    rows = []
    for dim in ["break_dir", "range_tercile", "break_speed", "weekday"]:
        for (ses, n, val), g in b.groupby(["session", "or_min", dim], observed=True):
            rows.append({
                "dimension": dim, "value": val, "session": ses, "or_min": n, "breaks": len(g),
                "pct_retest": pct(g.retest), "pct_ret_50": pct(g.t_ret_0500.notna()),
                "pct_ext_1618": pct(g.t_ext_0618.notna()),
                "pct_ext_1618_before_ret_50": pct(g.t_ext_0618.notna() & (g.t_ret_0500.isna() | (g.t_ext_0618 < g.t_ret_0500))),
                "pct_failed_opposite": pct(g.opposite_break),
            })
    return pd.DataFrame(rows)


def london_ny_table(ev: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Relación entre la ruptura de Londres y la de Nueva York del mismo día."""
    out = []
    for n in C.OR_MINUTES:
        lo = ev[(ev.session == "London") & (ev.or_min == n)].set_index(["symbol", "date"])
        ny = ev[(ev.session == "NewYork") & (ev.or_min == n)].set_index(["symbol", "date"])
        j = lo[["break_dir", "or_high", "or_low", "or_range"]].join(
            ny[["break_dir", "open_price", "max_ext", "retest"]], lsuffix="_lon", rsuffix="_ny", how="inner")
        j = j[(j.break_dir_lon != "none") & (j.break_dir_ny != "none")]
        # Posición de la apertura de NY dentro del rango de Londres (0 = mínimo, 1 = máximo)
        j["ny_open_fib_in_lon"] = (j.open_price - j.or_low) / j.or_range
        j["or_min"] = n
        out.append(j.reset_index())
    j = pd.concat(out)
    j["same_dir"] = j.break_dir_lon == j.break_dir_ny
    j["ny_open_zone"] = pd.cut(j.ny_open_fib_in_lon, [-np.inf, 0, 0.382, 0.618, 1, np.inf],
                               labels=["bajo mínimo Londres", "0–38.2", "38.2–61.8", "61.8–100", "sobre máximo Londres"])
    summ = (j.groupby(["or_min", "ny_open_zone"], observed=True)
             .agg(days=("same_dir", "size"), pct_ny_up=("break_dir_ny", lambda s: pct(s == "up")),
                  pct_same_dir_as_london=("same_dir", pct)).reset_index())
    tot = j.groupby("or_min").agg(days=("same_dir", "size"), pct_same_dir_as_london=("same_dir", pct)).reset_index()
    tot["ny_open_zone"] = "TODOS"
    return pd.concat([tot, summ], ignore_index=True), j


# --------------------------------------------------------------------------------------------
# 2. Rejilla de reglas (entrada / stop / objetivo) con IS y OOS
# --------------------------------------------------------------------------------------------

def metrics(r: pd.Series, outcome: pd.Series) -> dict:
    """r = R netos. win_pct = % de operaciones que alcanzan el objetivo."""
    if len(r) == 0:
        return {"n": 0}
    wins, losses = r[r > 0].sum(), -r[r < 0].sum()
    eq = r.cumsum()
    return {"n": len(r), "win_pct": round(100 * (outcome == "target").mean(), 1), "exp_R": round(r.mean(), 3),
            "total_R": round(r.sum(), 2), "pf": round(wins / losses, 2) if losses > 0 else np.inf,
            "max_dd_R": round((eq - eq.cummax()).min(), 2)}


MODELS = {
    "continuacion": (C.ENTRIES, C.STOPS, C.TARGETS),
    "reversion": (C.FADE_ENTRIES, C.FADE_STOPS, C.FADE_TARGETS),
}


def run_grid(ev: pd.DataFrame, paths: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Simula cada combinación entrada/stop/objetivo para cada ruptura.
      continuacion: a favor de la ruptura (entrada en ruptura o en retroceso Fibonacci).
      reversion:    en contra de la ruptura (entrada en ruptura o en extensión Fibonacci,
                    objetivo de vuelta al rango).
    """
    b = ev[ev.break_dir != "none"].set_index("event_id")
    trades = []
    for model, (ents, stops, tgts) in MODELS.items():
        combos = [(e, s, t) for e, s, t in itertools.product(ents, stops, tgts)
                  if e == "break" or float(e) < s]
        for eid, row in b.iterrows():
            p = paths[eid] if model == "continuacion" else E.flip(paths[eid])
            for e, s, t in combos:
                res = E.simulate(p, e, s, t)
                if res:
                    trades.append({"event_id": eid, "symbol": row.symbol, "date": row.date,
                                   "session": row.session, "or_min": row.or_min, "sample": row["sample"],
                                   "break_dir": row.break_dir, "model": model,
                                   "entry": str(e), "stop": s, "target": t, **res})
    tr = pd.DataFrame(trades)
    rows = []
    for key, g in tr.groupby(["session", "or_min", "model", "entry", "stop", "target"]):
        for scope, gg in [("ALL", g)] + list(g.groupby("symbol")):
            r = dict(zip(["session", "or_min", "model", "entry", "stop", "target"], key))
            r["symbol"] = scope
            for smp in ["IS", "OOS"]:
                x = gg[gg["sample"] == smp]
                for k, v in metrics(x.r_net, x.outcome).items():
                    r[f"{smp}_{k}"] = v
                r[f"{smp}_exp_R_gross"] = round(x.r_gross.mean(), 3) if len(x) else np.nan
            rows.append(r)
    return pd.DataFrame(rows), tr


def select_rules(grid: pd.DataFrame) -> pd.DataFrame:
    """Mejor regla por sesión/OR elegida SOLO con in-sample (ambos índices juntos)."""
    g = grid[(grid.symbol == "ALL") & (grid.IS_n >= C.MIN_TRADES_IS)]
    best = g.sort_values("IS_exp_R", ascending=False).groupby(["session", "or_min"]).head(3)
    return best.sort_values(["session", "or_min", "IS_exp_R"], ascending=[True, True, False])


# --------------------------------------------------------------------------------------------
# 3. Gráficos
# --------------------------------------------------------------------------------------------

def _save(fig, name):
    fig.savefig(os.path.join(RES, name), dpi=150, bbox_inches="tight")
    plt.close(fig)


def chart_depth(ev):
    b = ev[(ev.break_dir != "none")]
    fig, axes = plt.subplots(1, 2, figsize=(11, 3.8), sharey=True)
    for ax, n in zip(axes, C.OR_MINUTES):
        data = {ses: depth_buckets(b[(b.session == ses) & (b.or_min == n)]) for ses in C.SESSIONS}
        labels = list(next(iter(data.values())).index)
        x = np.arange(len(labels))
        w = 0.38
        for i, (ses, s) in enumerate(data.items()):
            ax.bar(x + (i - 0.5) * w, s.values, w - 0.04, color=SESSION_COLOR[ses], label=ses)
        ax.set_xticks(x, labels, rotation=35, ha="right")
        ax.set_title(f"Retroceso máximo tras la ruptura — OR {n} min", loc="left", fontsize=10)
        ax.set_ylabel("% de rupturas")
        ax.grid(axis="x", visible=False)
    axes[0].legend()
    _save(fig, "retrace_depth.png")


def chart_extension(ev):
    b = ev[ev.break_dir != "none"]
    fig, axes = plt.subplots(1, 2, figsize=(11, 3.6), sharey=True)
    xs = np.linspace(0, 3, 121)
    for ax, n in zip(axes, C.OR_MINUTES):
        for ses in C.SESSIONS:
            g = b[(b.session == ses) & (b.or_min == n)].max_ext.dropna().values
            ax.plot(xs, [100 * (g >= x).mean() for x in xs], color=SESSION_COLOR[ses], label=ses)
        for e in C.EXT_LEVELS:
            ax.axvline(e, color=GRID, lw=1, ls="--")
            ax.text(e, 101, C.EXT_LABEL[e], ha="center", va="bottom", fontsize=8, color=INK2)
        ax.set_xlabel("Extensión máxima desde el nivel roto (en rangos de apertura)")
        ax.set_title(f"P(extensión ≥ x) — OR {n} min", loc="left", fontsize=10, pad=14)
        ax.set_ylabel("% de rupturas")
    axes[0].legend()
    _save(fig, "extension_survival.png")


def chart_heat_ext_ret(ev):
    b = ev[ev.break_dir != "none"]
    fig, axes = plt.subplots(2, 2, figsize=(11, 6.2))
    for i, ses in enumerate(C.SESSIONS):
        for j, n in enumerate(C.OR_MINUTES):
            ax = axes[i, j]
            m = ext_before_retrace(b[(b.session == ses) & (b.or_min == n)])
            ax.imshow(m.values.astype(float), cmap=SEQ, vmin=0, vmax=100, aspect="auto")
            for (r, c), v in np.ndenumerate(m.values.astype(float)):
                ax.text(c, r, f"{v:.0f}", ha="center", va="center", fontsize=8,
                        color="white" if v > 55 else INK)
            ax.set_xticks(range(m.shape[1]), m.columns)
            ax.set_yticks(range(m.shape[0]), m.index)
            ax.grid(False)
            ax.set_title(f"{ses} · OR {n} min", loc="left", fontsize=10)
            if i == 1:
                ax.set_xlabel("…antes de retroceder al nivel Fibonacci")
            if j == 0:
                ax.set_ylabel("Llega a extensión…")
    fig.suptitle("% de rupturas que alcanzan la extensión ANTES de retroceder al nivel", x=0.01, ha="left")
    fig.tight_layout()
    _save(fig, "heat_ext_before_retrace.png")


def chart_grid(grid):
    """Expectativa neta (R) IS vs OOS de cada regla, ambos índices juntos."""
    g = grid[grid.symbol == "ALL"]
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.4), sharex=True, sharey=True)
    for ax, n in zip(axes, C.OR_MINUTES):
        for ses in C.SESSIONS:
            for model, mk in [("continuacion", "o"), ("reversion", "^")]:
                x = g[(g.session == ses) & (g.or_min == n) & (g.model == model) & (g.IS_n >= C.MIN_TRADES_IS)]
                ax.scatter(x.IS_exp_R, x.OOS_exp_R, s=22, marker=mk, color=SESSION_COLOR[ses], alpha=0.8,
                           edgecolor=SURFACE, linewidth=0.6, label=f"{ses} · {model}")
        ax.axhline(0, color=INK2, lw=0.8)
        ax.axvline(0, color=INK2, lw=0.8)
        ax.set_title(f"Cada punto = una regla · OR {n} min", loc="left", fontsize=10)
        ax.set_xlabel("Expectativa neta in-sample (R/operación)")
    axes[0].set_ylabel("Expectativa neta out-of-sample (R/operación)")
    axes[0].legend(loc="lower right")
    _save(fig, "rules_is_vs_oos.png")


def chart_equity(tr, chosen):
    fig, ax = plt.subplots(figsize=(11, 4))
    cols = [BLUE, ORANGE, GREEN, AMBER]
    for k, (_, r) in enumerate(chosen.iterrows()):
        x = tr[(tr.session == r.session) & (tr.or_min == r.or_min) & (tr.model == r.model) & (tr.entry == r.entry)
               & (tr.stop == r.stop) & (tr.target == r.target)].sort_values(["date", "symbol"])
        eq = x.r_net.cumsum().values
        ax.plot(pd.to_datetime(x.date).values, eq, color=cols[k % 4],
                label=rule_label(r))
    ax.axvline(pd.Timestamp(C.IS_END), color=INK2, lw=1, ls="--")
    ax.text(pd.Timestamp(C.IS_END), ax.get_ylim()[1], "  inicio out-of-sample", va="top", fontsize=8, color=INK2)
    ax.axhline(0, color=INK2, lw=0.8)
    ax.set_ylabel("R acumulado (neto)")
    ax.set_title("Mejor regla in-sample de cada sesión/OR, aplicada después out-of-sample (QQQ + SPY)", loc="left", fontsize=10)
    ax.legend(fontsize=8)
    _save(fig, "equity_selected.png")


# --------------------------------------------------------------------------------------------
# 4. Informe
# --------------------------------------------------------------------------------------------

def md(df: pd.DataFrame, floatfmt=".1f") -> str:
    return df.to_markdown(index=False, floatfmt=floatfmt)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", action="append", default=[], help="SIMBOLO=ruta.csv (velas de 1 minuto)")
    ap.add_argument("--tz", default="UTC", help="zona horaria de los CSV (p. ej. Europe/Athens)")
    ap.add_argument("--source", default=C.SOURCE, choices=list(C.SOURCES) + ["csv"],
                    help="dukascopy (2022→hoy, por defecto), binance (6 meses) o csv")
    ap.add_argument("--no-bars", action="store_true", help="no guardar las velas en SQLite")
    args = ap.parse_args()

    global RES
    if args.source != "csv":
        C.use_source(args.source)
    else:
        C.SOURCE = "csv"
    RES = db.results_dir()
    os.makedirs(RES, exist_ok=True)
    con = db.connect()
    sources = {}
    if args.csv:
        for item in args.csv:
            sym, path = item.split("=", 1)
            sources[sym] = db.import_csv(path, args.tz)
    else:
        for sym in C.SYMBOLS:
            sources[sym] = db.load_bars(sym)

    evs, gaps, paths = [], [], {}
    for sym, bars in sources.items():
        print(f"[orb] {sym}: {len(bars)} velas 1m {bars.index[0]} -> {bars.index[-1]}", flush=True)
        if not args.no_bars:
            db.write_bars(con, sym, bars)
        daily = E.ny_daily(bars)
        e, p = E.extract_events(sym, bars, daily)
        evs.append(e)
        gaps.append(E.extract_gaps(sym, bars, daily))
        paths.update(p)
    ev = pd.concat(evs, ignore_index=True)
    gp = pd.concat(gaps, ignore_index=True)
    print(f"[orb] eventos: {len(ev)}  rupturas: {(ev.break_dir != 'none').sum()}")

    bt = breakout_table(ev)
    rx = retrace_ext_table(ev)
    rx_sym = retrace_ext_table(ev, by=("session", "or_min", "symbol"))
    cond = conditional_table(ev)
    lny, lny_rows = london_ny_table(ev)
    grid, tr = run_grid(ev, paths)
    best = select_rules(grid)
    top1 = best.groupby(["session", "or_min"]).head(1)
    chosen_tr = tr.merge(top1[["session", "or_min", "model", "entry", "stop", "target"]])

    # Robustez: reglas positivas en IS y OOS, y en ambos índices
    g_all = grid[(grid.symbol == "ALL") & (grid.IS_n >= C.MIN_TRADES_IS)]
    robust = g_all[(g_all.IS_exp_R > 0) & (g_all.OOS_exp_R > 0)]
    per_sym = grid[grid.symbol != "ALL"].groupby(["session", "or_min", "model", "entry", "stop", "target"]).apply(
        lambda x: bool(((x.IS_exp_R > 0) & (x.OOS_exp_R > 0)).all()), include_groups=False).rename("all_symbols_pos")
    robust = robust.merge(per_sym.reset_index(), how="left").sort_values("OOS_exp_R", ascending=False)

    # Base de datos: completa (con velas) y ligera (sólo eventos), mismas tablas
    if os.path.exists(db.db_light_path()):
        os.remove(db.db_light_path())
    for cx in (con, db.connect(db.db_light_path())):
        db.write_table(cx, "events", ev)
        db.write_table(cx, "gaps", gp)
        db.write_table(cx, "strategy_grid", grid)
        db.write_table(cx, "trades", chosen_tr)
        db.write_views(cx)
        cx.close()
    gp.to_csv(os.path.join(RES, "gaps.csv"), index=False, float_format="%.5f")

    # CSV
    ev.to_csv(os.path.join(RES, "events.csv"), index=False, float_format="%.5f")
    bt.to_csv(os.path.join(RES, "breakout_summary.csv"), index=False)
    rx_sym.to_csv(os.path.join(RES, "retrace_extension_by_symbol.csv"), index=False)
    cond.to_csv(os.path.join(RES, "conditional_probabilities.csv"), index=False)
    lny.to_csv(os.path.join(RES, "london_vs_newyork.csv"), index=False)
    grid.to_csv(os.path.join(RES, "strategy_grid.csv"), index=False)
    chosen_tr.to_csv(os.path.join(RES, "trades_selected_rules.csv"), index=False, float_format="%.4f")

    # Gráficos
    chart_depth(ev)
    chart_extension(ev)
    chart_heat_ext_ret(ev)
    chart_grid(grid)
    chart_equity(tr, top1)

    b = ev[ev.break_dir != "none"]
    heat = {f"{s}_OR{n}": ext_before_retrace(b[(b.session == s) & (b.or_min == n)]).round(1).to_dict()
            for s in C.SESSIONS for n in C.OR_MINUTES}
    depth = {f"{s}_OR{n}": depth_buckets(b[(b.session == s) & (b.or_min == n)]).to_dict()
             for s in C.SESSIONS for n in C.OR_MINUTES}
    summary = {
        "period": [C.START, C.END], "is_end": C.IS_END, "symbols": list(sources),
        "cost_bp_per_side": C.COST_BP_PER_SIDE, "events": len(ev), "breaks": int(len(b)),
        "rules_tested_per_slice": int(grid.groupby(["session", "or_min"]).size().iloc[0] / (1 + len(sources))),
        "rules_positive_IS_and_OOS": int(len(robust)),
        "rules_positive_IS_OOS_all_symbols": int(robust.all_symbols_pos.fillna(False).sum()),
        "ext_before_retrace": heat, "retrace_depth": depth,
    }
    with open(os.path.join(RES, "summary.json"), "w") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False, default=str)

    # Informe markdown
    cols_rule = ["session", "or_min", "model", "entry", "stop", "target", "IS_n", "IS_win_pct", "IS_exp_R",
                 "IS_exp_R_gross", "OOS_n", "OOS_win_pct", "OOS_exp_R", "OOS_exp_R_gross", "OOS_pf"]
    with open(os.path.join(RES, "REPORT.md"), "w") as f:
        f.write(f"# Estudio ORB + Fibonacci — resultados\n\nPeríodo {C.START} → {C.END} "
                f"(IS hasta {C.IS_END}, OOS después). Símbolos: {', '.join(sources)}. "
                f"Coste {C.COST_BP_PER_SIDE} pb por lado.\n\n")
        f.write("## 1. Dirección de ruptura y retrocesos\n\n" + md(bt) + "\n\n")
        f.write("## 2. % de rupturas que tocan cada retroceso / extensión (en algún momento)\n\n"
                + md(rx) + "\n\n")
        for s in C.SESSIONS:
            for n in C.OR_MINUTES:
                f.write(f"### Extensión antes que retroceso — {s} OR {n} min (%)\n\n"
                        + ext_before_retrace(b[(b.session == s) & (b.or_min == n)]).round(1)
                        .reset_index(names="ext \\ ret").to_markdown(index=False, floatfmt=".1f") + "\n\n")
        f.write("## 3. Probabilidades condicionadas\n\n" + md(cond) + "\n\n")
        f.write("## 4. Londres → Nueva York (mismo día)\n\n" + md(lny) + "\n\n")
        f.write("## 5. Mejores reglas in-sample (top 3 por sesión) y su resultado out-of-sample\n\n"
                + md(best[cols_rule], ".3f") + "\n\n")
        f.write(f"## 6. Reglas positivas en IS y en OOS ({len(robust)} de {len(g_all)} con n≥{C.MIN_TRADES_IS})\n\n"
                + (md(robust[cols_rule + ['all_symbols_pos']].head(25), ".3f") if len(robust) else "Ninguna.") + "\n")
    print(open(os.path.join(RES, "REPORT.md")).read()[:20000])


if __name__ == "__main__":
    main()
