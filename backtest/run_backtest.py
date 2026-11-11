"""
run_backtest.py — Ejecuta el backtest TTFM sobre el universo de SPEC para los dos perfiles
(4H→15m intradía y 1D→1H swing), calcula métricas y guarda resultados en results/.

Uso:  python3 backtest/run_backtest.py
"""
from __future__ import annotations

import json
import os
import sys
import warnings
from dataclasses import asdict, replace

import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import data_loader as dl  # noqa: E402
import ttfm_engine as eng  # noqa: E402

warnings.filterwarnings("ignore", category=RuntimeWarning)
warnings.filterwarnings("ignore", message=".*origin.*")

ROOT = dl.ROOT
RES = os.path.join(ROOT, "results")
CLASSES = ["Forex", "Cripto", "Indices", "Commodities"]
BASE = eng.Params(start=dl.START, end=pd.Timestamp(dl.END).strftime("%Y-%m-%d 23:59:59"))

# Paleta (reference palette del skill dataviz, modo claro)
SURFACE, INK, INK2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
CLASS_COLOR = dict(zip(CLASSES, SERIES[:4]))
PROFILE_COLOR = {"intradia_4H_15m": SERIES[0], "swing_1D_1H": SERIES[1]}
PROFILE_LABEL = {"intradia_4H_15m": "Intradía 4H→15m", "swing_1D_1H": "Swing 1D→1H"}

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "axes.edgecolor": GRID, "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
    "text.color": INK, "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6,
    "axes.spines.top": False, "axes.spines.right": False, "font.size": 9, "lines.linewidth": 2,
    "legend.frameon": False,
})


# ----------------------------------------------------------------------------- métricas
def equity_stats(eq: pd.Series, initial: float) -> dict:
    if eq.empty:
        return dict(return_pct=0.0, max_dd_pct=0.0, sharpe_daily=np.nan)
    dd = (eq / eq.cummax() - 1).min() * 100
    daily = eq.resample("1D").last().ffill()
    daily = pd.concat([pd.Series([initial], index=[daily.index[0] - pd.Timedelta(days=1)]), daily])
    r = daily.pct_change().dropna()
    sharpe = r.mean() / r.std() * np.sqrt(365) if r.std() > 0 else np.nan
    return dict(return_pct=(eq.iloc[-1] / initial - 1) * 100, max_dd_pct=dd, sharpe_daily=sharpe)


def trade_stats(tr: pd.DataFrame) -> dict:
    if tr is None or tr.empty:
        return dict(trades=0, win_rate_pct=np.nan, profit_factor=np.nan, expectancy_R=np.nan,
                    avg_planned_rr=np.nan, avg_win_R=np.nan, avg_loss_R=np.nan, best_R=np.nan,
                    worst_R=np.nan, avg_duration_h=np.nan, long_trades=0, short_trades=0)
    wins, losses = tr[tr.pnl > 0], tr[tr.pnl <= 0]
    gl = -losses.pnl.sum()
    return dict(
        trades=len(tr), win_rate_pct=len(wins) / len(tr) * 100,
        profit_factor=(wins.pnl.sum() / gl) if gl > 0 else np.inf,
        expectancy_R=tr.r_multiple.mean(), avg_planned_rr=tr.planned_rr.mean(),
        avg_win_R=wins.r_multiple.mean() if len(wins) else np.nan,
        avg_loss_R=losses.r_multiple.mean() if len(losses) else np.nan,
        best_R=tr.r_multiple.max(), worst_R=tr.r_multiple.min(),
        avg_duration_h=((tr.exit_time - tr.entry_time).dt.total_seconds() / 3600).mean(),
        long_trades=int((tr.direction == "long").sum()), short_trades=int((tr.direction == "short").sum()))


def portfolio(curves: dict, initial: float) -> pd.Series:
    """Cartera equiponderada: media de curvas normalizadas (cada activo arranca con el mismo capital)."""
    if not curves:
        return pd.Series(dtype=float)
    df = pd.concat(curves, axis=1).sort_index().ffill().fillna(initial)
    return df.mean(axis=1)


# ----------------------------------------------------------------------------- backtest
def ltf_frame(df15: pd.DataFrame, ltf_rule: str) -> pd.DataFrame:
    return df15 if ltf_rule == "15min" else dl.resample(df15, ltf_rule)


def run_profile(data: dict, profile: str, params: eng.Params, check: bool = True):
    htf_rule, ltf_rule = eng.PROFILES[profile]
    trades, curves, sigs = [], {}, []
    for sym, df15 in data.items():
        if df15.empty:
            continue
        tr, eq, sg = eng.run(ltf_frame(df15, ltf_rule), htf_rule, params, symbol=sym, check=check)
        if not tr.empty:
            tr.insert(1, "asset_class", dl.UNIVERSE[sym][1])
            trades.append(tr)
        if not sg.empty:
            sigs.append(sg)
        curves[sym] = eq
    trades = pd.concat(trades, ignore_index=True) if trades else pd.DataFrame()
    sigs = pd.concat(sigs, ignore_index=True) if sigs else pd.DataFrame()
    return trades, curves, sigs


def metrics_table(data, trades, curves, sigs, params):
    rows = []
    init = params.initial_capital
    groups = [(s, "asset", dl.UNIVERSE[s][1], [s]) for s in curves]
    groups += [(c, "class", c, [s for s in curves if dl.UNIVERSE[s][1] == c]) for c in CLASSES]
    groups += [("GLOBAL", "global", "Todas", list(curves))]
    for name, level, cls, syms in groups:
        if not syms:
            continue
        tr = trades[trades.symbol.isin(syms)] if not trades.empty else trades
        eq = portfolio({s: curves[s] for s in syms}, init)
        bh = np.mean([(data[s].close.iloc[-1] / data[s].open.iloc[0] - 1) * 100 for s in syms])
        sg = sigs[sigs.symbol.isin(syms)] if not sigs.empty else sigs
        row = dict(name=name, level=level, asset_class=cls, n_symbols=len(syms))
        row.update(trade_stats(tr))
        row.update(equity_stats(eq, init))
        row["buy_hold_pct"] = bh
        row["cisd_signals"] = len(sg)
        row["rejected_minRR"] = int((~sg.taken).sum()) if len(sg) else 0
        row["valid_not_entered"] = int((sg.taken & ~sg.entered).sum()) if len(sg) else 0
        row["lev_capped_trades"] = int(tr.lev_capped.sum()) if len(tr) else 0
        rows.append(row)
    return pd.DataFrame(rows)


# ----------------------------------------------------------------------------- gráficos
def _end_label(ax, s, text, color, y=None):
    ax.annotate(text, (s.index[-1], s.iloc[-1] if y is None else y), xytext=(6, 0), textcoords="offset points",
                va="center", fontsize=8, color=INK2)
    ax.plot(s.index[-1], s.iloc[-1], "o", ms=4, color=color, mec=SURFACE, mew=1.5)


def _spread(values, min_gap):
    """Separa verticalmente etiquetas finales para que no se solapen."""
    order = np.argsort(values)
    out = np.array(values, float)
    for k in range(1, len(order)):
        a, b = order[k - 1], order[k]
        if out[b] - out[a] < min_gap:
            out[b] = out[a] + min_gap
    return out


def plot_equity_by_class(res, init):
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.6), sharey=True)
    for ax, (prof, r) in zip(axes, res.items()):
        eqs = {}
        for c in CLASSES:
            syms = [s for s in r["curves"] if dl.UNIVERSE[s][1] == c]
            eqs[c] = portfolio({s: r["curves"][s] for s in syms}, init)
            ax.plot(eqs[c].index, eqs[c].values, color=CLASS_COLOR[c], label=c)
        ys = _spread([e.iloc[-1] for e in eqs.values()], 110)
        for (c, eq), y in zip(eqs.items(), ys):
            _end_label(ax, eq, f"{c} {(eq.iloc[-1]/init-1)*100:+.1f}%", CLASS_COLOR[c], y)
        ax.axhline(init, color=INK2, lw=0.8, ls="--")
        ax.set_title(f"Equity por clase de activo — {PROFILE_LABEL[prof]}", loc="left", fontsize=10)
        ax.set_ylabel("Equity (USD, cartera equiponderada de la clase)")
        ax.margins(x=0.18)
    axes[0].legend(loc="upper left", ncol=2)
    fig.tight_layout()
    fig.savefig(os.path.join(RES, "equity_by_class.png"), dpi=140)
    plt.close(fig)


def plot_equity_global(res, data, init):
    fig, ax = plt.subplots(figsize=(11, 4.6))
    for prof, r in res.items():
        eq = portfolio(r["curves"], init)
        ax.plot(eq.index, eq.values, color=PROFILE_COLOR[prof], label=f"TTFM {PROFILE_LABEL[prof]}")
        _end_label(ax, eq, f"{(eq.iloc[-1]/init-1)*100:+.1f}%", PROFILE_COLOR[prof])
    bh = portfolio({s: df.close / df.open.iloc[0] * init for s, df in data.items() if not df.empty}, init)
    bh = bh.resample("1h").last().dropna()
    ax.plot(bh.index, bh.values, color=SERIES[2], label="Buy & hold equiponderado")
    _end_label(ax, bh, f"{(bh.iloc[-1]/init-1)*100:+.1f}%", SERIES[2])
    ax.axhline(init, color=INK2, lw=0.8, ls="--")
    ax.set_title("Cartera global equiponderada (9 activos, 10 000 USD por activo normalizado)", loc="left", fontsize=10)
    ax.set_ylabel("Equity (USD)")
    ax.legend(loc="upper left")
    ax.margins(x=0.08)
    fig.tight_layout()
    fig.savefig(os.path.join(RES, "equity_global.png"), dpi=140)
    plt.close(fig)


def plot_r_distribution(res):
    fig, axes = plt.subplots(1, 2, figsize=(12, 4), sharey=False)
    # Nota: R < -1 en pérdidas por SL se debe a los costes (comisión+slippage) sobre SL estrechos
    for ax, (prof, r) in zip(axes, res.items()):
        tr = r["trades"]
        if tr.empty:
            continue
        bins = np.arange(np.floor(tr.r_multiple.min() * 4) / 4, tr.r_multiple.max() + 0.25, 0.25)
        ax.hist(tr.r_multiple, bins=bins, color=PROFILE_COLOR[prof], edgecolor=SURFACE, linewidth=1.5)
        ax.axvline(0, color=INK2, lw=0.8)
        ax.axvline(tr.r_multiple.mean(), color=INK, lw=1.2, ls="--")
        ax.annotate(f"media {tr.r_multiple.mean():+.2f}R  (n={len(tr)})", (tr.r_multiple.mean(), ax.get_ylim()[1] * 0.92),
                    xytext=(5, 0), textcoords="offset points", fontsize=8, color=INK2)
        ax.set_title(f"Distribución de R por trade — {PROFILE_LABEL[prof]}", loc="left", fontsize=10)
        ax.set_xlabel("R múltiplo (neto de costes)")
        ax.set_ylabel("Nº de trades")
    fig.tight_layout()
    fig.savefig(os.path.join(RES, "r_distribution.png"), dpi=140)
    plt.close(fig)


def monthly_returns(curves, init):
    out = {}
    for s, eq in curves.items():
        m = eq.resample("ME").last()
        prev = m.shift(1).fillna(init)
        out[s] = (m / prev - 1) * 100
    port = portfolio(curves, init).resample("ME").last()
    out["CARTERA"] = (port / port.shift(1).fillna(init) - 1) * 100
    df = pd.DataFrame(out).T
    df.columns = [c.strftime("%Y-%m") for c in df.columns]
    return df


def plot_monthly_heatmap(res, init):
    cmap = LinearSegmentedColormap.from_list("div", ["#e34948", "#f0efec", "#2a78d6"])
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    for ax, (prof, r) in zip(axes, res.items()):
        mr = monthly_returns(r["curves"], init)
        r["monthly"] = mr
        v = np.nanmax(np.abs(mr.values)) or 1
        ax.imshow(mr.values, cmap=cmap, norm=TwoSlopeNorm(0, -v, v), aspect="auto")
        ax.set_xticks(range(mr.shape[1]), mr.columns, rotation=45, ha="right")
        ax.set_yticks(range(mr.shape[0]), mr.index)
        ax.grid(False)
        for i in range(mr.shape[0]):
            for j in range(mr.shape[1]):
                val = mr.values[i, j]
                if not np.isnan(val):
                    ax.text(j, i, f"{val:+.1f}", ha="center", va="center", fontsize=7, color=INK)
        ax.set_title(f"Retorno mensual % — {PROFILE_LABEL[prof]}", loc="left", fontsize=10)
    fig.tight_layout()
    fig.savefig(os.path.join(RES, "monthly_heatmap.png"), dpi=140)
    plt.close(fig)


def plot_metrics_by_asset(res, bh):
    metrics = [("return_pct", "Retorno total %"), ("win_rate_pct", "Win rate %"),
               ("profit_factor", "Profit factor"), ("expectancy_R", "Expectancy (R)")]
    fig, axes = plt.subplots(2, 2, figsize=(13, 7.5))
    syms = list(dl.UNIVERSE)
    x = np.arange(len(syms))
    w = 0.38
    for ax, (col, title) in zip(axes.flat, metrics):
        for k, (prof, r) in enumerate(res.items()):
            m = r["metrics"].set_index("name").reindex(syms)[col].replace(np.inf, np.nan)
            ax.bar(x + (k - 0.5) * w, m.values, width=w - 0.04, color=PROFILE_COLOR[prof],
                   label=PROFILE_LABEL[prof])
        if col == "return_pct":
            ax.scatter(x, [bh[s] for s in syms], marker="D", s=28, color=INK, zorder=3, label="Buy & hold %")
        ref = {"profit_factor": 1.0, "win_rate_pct": 50.0}.get(col, 0.0)
        ax.axhline(ref, color=INK2, lw=0.8, ls="--")
        ax.set_xticks(x, syms, rotation=30, ha="right")
        ax.set_title(title, loc="left", fontsize=10)
    axes[0, 0].legend(loc="best", fontsize=8)
    fig.tight_layout()
    fig.savefig(os.path.join(RES, "metrics_by_asset.png"), dpi=140)
    plt.close(fig)


# ----------------------------------------------------------------------------- main
def _clean(o):
    if isinstance(o, dict):
        return {k: _clean(v) for k, v in o.items()}
    if isinstance(o, list):
        return [_clean(v) for v in o]
    if isinstance(o, (float, np.floating)):
        return None if (np.isnan(o) or np.isinf(o)) else round(float(o), 4)
    if isinstance(o, np.integer):
        return int(o)
    return o


def main():
    os.makedirs(RES, exist_ok=True)
    data = dl.load_all(verbose=True)
    notes = {}
    for s, df in data.items():
        if df.empty:
            notes[s] = "SIN DATOS: excluido"
        else:
            notes[s] = f"{len(df)} velas 15m, {df.index[0]} -> {df.index[-1]}"
    data = {s: df for s, df in data.items() if not df.empty}
    bh = {s: (df.close.iloc[-1] / df.open.iloc[0] - 1) * 100 for s, df in data.items()}

    res = {}
    for prof in eng.PROFILES:
        trades, curves, sigs = run_profile(data, prof, BASE, check=True)
        met = metrics_table(data, trades, curves, sigs, BASE)
        res[prof] = dict(trades=trades, curves=curves, signals=sigs, metrics=met)
        trades.to_csv(os.path.join(RES, f"trades_{prof}.csv"), index=False)
        met.to_csv(os.path.join(RES, f"metrics_{prof}.csv"), index=False, float_format="%.4f")
        # sanity: nº de trades razonable (al menos alguno, y no más de 1 por vela HTF por activo)
        htf_bars = {"intradia_4H_15m": 6, "swing_1D_1H": 1}[prof] * 224
        assert 0 < len(trades) <= htf_bars * len(data), f"Nº de trades anómalo en {prof}"
        print(f"\n=== {prof} ===  trades={len(trades)}")
        print(met[["name", "trades", "win_rate_pct", "profit_factor", "expectancy_R", "return_pct",
                   "max_dd_pct", "sharpe_daily", "buy_hold_pct"]].round(2).to_string(index=False))

    plot_equity_by_class(res, BASE.initial_capital)
    plot_equity_global(res, data, BASE.initial_capital)
    plot_r_distribution(res)
    plot_monthly_heatmap(res, BASE.initial_capital)
    plot_metrics_by_asset(res, bh)
    for prof, r in res.items():
        r["monthly"].round(3).to_csv(os.path.join(RES, f"monthly_returns_{prof}.csv"))

    # ---------------- impacto de costes: misma simulación sin comisión ni slippage ----------------
    gross = {}
    for prof in eng.PROFILES:
        p0 = replace(BASE, commission=0.0, slippage=0.0)
        tr, cv, sg = run_profile(data, prof, p0, check=False)
        m0 = metrics_table(data, tr, cv, sg, p0).query("level in ('class', 'global')")
        gross[prof] = m0.set_index("name")[["trades", "win_rate_pct", "profit_factor", "expectancy_R",
                                             "return_pct", "max_dd_pct"]].to_dict(orient="index")
        print(f"\n=== {prof} SIN COSTES (bruto) ===")
        print(m0[["name", "trades", "expectancy_R", "return_pct"]].round(2).to_string(index=False))

    # ---------------- sensibilidad (perfil intradía) ----------------
    rows = []
    for mrr in (1.0, 1.5, 2.0):
        for buf in (0.0, 0.1, 0.25):
            p = replace(BASE, minRR=mrr, slBufferATR=buf)
            tr, cv, sg = run_profile(data, "intradia_4H_15m", p, check=False)
            g = metrics_table(data, tr, cv, sg, p).query("level == 'global'").iloc[0]
            rows.append(dict(minRR=mrr, slBufferATR=buf, trades=g.trades, win_rate_pct=g.win_rate_pct,
                             profit_factor=g.profit_factor, expectancy_R=g.expectancy_R,
                             portfolio_return_pct=g.return_pct, max_dd_pct=g.max_dd_pct,
                             sharpe_daily=g.sharpe_daily))
    sens = pd.DataFrame(rows)
    sens.to_csv(os.path.join(RES, "sensitivity.csv"), index=False, float_format="%.4f")
    print("\n=== Sensibilidad intradía (global) ===")
    print(sens.round(2).to_string(index=False))

    summary = dict(
        period=dict(start=dl.START, end=dl.END),
        params=asdict(BASE),
        data_notes=notes,
        sanity_checks="OK: asserts de no look-ahead (C1/C2 cerradas antes de la señal, entrada en vela LTF de "
                      "confirmación dentro de C3, extremos C2 = resample independiente), precios dentro del "
                      "rango de la vela, sin posiciones solapadas",
        buy_hold_pct=bh,
        profiles={prof: dict(
            htf=eng.PROFILES[prof][0], ltf=eng.PROFILES[prof][1],
            global_=r["metrics"].query("level=='global'").iloc[0].to_dict(),
            by_class=r["metrics"].query("level=='class'").set_index("name").to_dict(orient="index"),
            by_asset=r["metrics"].query("level=='asset'").set_index("name").to_dict(orient="index"),
        ) for prof, r in res.items()},
        sensitivity_intradia=sens.to_dict(orient="records"),
        gross_no_costs=gross,
    )
    with open(os.path.join(RES, "summary.json"), "w") as f:
        json.dump(_clean(summary), f, indent=2, default=str, ensure_ascii=False)
    print("\nResultados guardados en", RES)


if __name__ == "__main__":
    main()
