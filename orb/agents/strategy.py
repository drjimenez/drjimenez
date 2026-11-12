"""
strategy.py — Agente de estrategia: patrones con Fibonacci entre el CIERRE de Nueva York del día
anterior (16:00) y la APERTURA de Nueva York del día (09:30).

Coordenada del gap  p = (apertura − precio) / (apertura − cierre_anterior)
    p = 0      apertura                      p = 1      cierre anterior (gap cerrado)
    0 < p < 1  retroceso del gap (23.6 … 78.6)   p > 1  extensión más allá del cierre (1.272, 1.618)
    p < 0      el precio se aleja del cierre a favor del gap (−0.272, −0.618, −1)

El agente:
1. Mide probabilidades del gap: P(tocar cada nivel), orden de los toques, y cómo cambian con el
   tamaño del gap, la tendencia diaria, la posición de la apertura frente al rango del día
   anterior y la dirección de la primera ruptura del rango de apertura de NY (15 min).
2. Prueba una familia de PATRONES operables (con variantes de stop/objetivo):
     P1 Fade del gap en la apertura         entrada 09:30 hacia el cierre anterior
     P2 Fade tras ruptura del OR hacia el cierre   espera la ruptura del OR15 hacia el cierre
     P3 Gap and go                          ruptura del OR15 a favor del gap
     P4 Retroceso Fibonacci y continuación  límite en 38.2/50/61.8 del gap, a favor del gap
     P5 Gap cerrado y extensión             al tocar el cierre anterior, sigue hacia 1.272/1.618
   Cada variante se evalúa con todos los días y por filtros (tamaño del gap, gap a favor/en contra
   de la tendencia diaria). Se elige con in-sample (2022-2024) y se valida out-of-sample (2025-2026).
3. Genera gráficos de los patrones (escalera de probabilidades Fibonacci, trayectoria media,
   ejemplos reales y curvas de resultados) y el informe ESTRATEGIA.md.
"""
from __future__ import annotations

import itertools
import os
import sys
from zoneinfo import ZoneInfo

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

NY = ZoneInfo("America/New_York")
lv = E._lvl
FILL = C.GAP_FILL_LEVELS
AWAY = C.GAP_AWAY_LEVELS


# --------------------------------------------------------------------------------------------
# Simulador en precio (largo o corto) con supuestos conservadores
# --------------------------------------------------------------------------------------------

def _first(m):
    i = np.flatnonzero(m)
    return int(i[0]) if i.size else -1


def sim(h, lo, c, side: int, entry: float, stop: float, target: float, start: int,
        limit: bool = False, stop_entry: bool = False, cost_bp: float = C.COST_BP_PER_SIDE):
    """
    side +1 largo / −1 corto. Barras desde `start` hasta el final de los arrays (16:00 NY).
    limit=False: entrada a mercado en `entry` en la vela `start` (se evalúa desde la siguiente).
    limit=True : orden límite en `entry` desde `start`; se cancela si el objetivo llega antes.
    stop_entry=True: orden stop (entra cuando el precio llega a `entry` moviéndose a favor).
    Empate stop/objetivo en una vela -> stop. Sin salida -> cierre de las 16:00.
    """
    risk = (entry - stop) * side
    if risk <= 0 or (target - entry) * side <= 0:
        return None
    if stop_entry:
        fill = (h[start:] >= entry) if side > 0 else (lo[start:] <= entry)
        jf = _first(fill)
        if jf < 0:
            return None
        i = start + jf
        sh = (lo[i:] <= stop) if side > 0 else (h[i:] >= stop)
        th = (h[i:] >= target) if side > 0 else (lo[i:] <= target)
        th = th.copy()
        th[0] = False
    elif limit:
        fill = (lo[start:] <= entry) if side > 0 else (h[start:] >= entry)
        tgt0 = (h[start:] >= target) if side > 0 else (lo[start:] <= target)
        jf, jt = _first(fill), _first(tgt0)
        if jf < 0 or (0 <= jt < jf):
            return None
        i = start + jf
        sh = (lo[i:] <= stop) if side > 0 else (h[i:] >= stop)
        th = (h[i:] >= target) if side > 0 else (lo[i:] <= target)
        th = th.copy()
        th[0] = False                   # en la vela del fill sólo cuenta el stop
    else:
        i = start + 1
        if i >= len(c):
            return None
        sh = (lo[i:] <= stop) if side > 0 else (h[i:] >= stop)
        th = (h[i:] >= target) if side > 0 else (lo[i:] <= target)
    js, jt = _first(sh), _first(th)
    if js >= 0 and (jt < 0 or js <= jt):
        out, px = "stop", stop
    elif jt >= 0:
        out, px = "target", target
    else:
        out, px = "time", c[-1]
    r = (px - entry) * side / risk
    cost = 2 * cost_bp / 1e4 * entry / risk
    return {"outcome": out, "r_gross": r, "r_net": r - cost}


# --------------------------------------------------------------------------------------------
# Agente
# --------------------------------------------------------------------------------------------

PATTERN_TXT = {
    "P1": "Fade del gap en la apertura",
    "P2": "Fade tras ruptura del OR15 hacia el cierre",
    "P3": "Gap and go (ruptura del OR15 a favor del gap)",
    "P4": "Retroceso Fibonacci y continuación a favor del gap",
    "P5": "Gap cerrado y extensión más allá del cierre anterior",
}


class StrategyAgent:
    MIN_N_IS = 40

    def __init__(self, bars: dict[str, pd.DataFrame], gaps: pd.DataFrame, out_dir: str):
        self.bars = bars
        self.g = gaps[gaps.gap_dir != "plano"].copy()
        self.all_gaps = gaps
        self.out = out_dir
        os.makedirs(out_dir, exist_ok=True)
        self._prepare()

    # -- preparación: índices de cada día y OR de 15 minutos -----------------------------------
    def _prepare(self):
        self.arr = {}
        for s, b in self.bars.items():
            t = b.index.tz_convert("UTC").tz_localize(None).values.astype("datetime64[m]")
            self.arr[s] = (t, b.high.to_numpy(float), b.low.to_numpy(float), b.close.to_numpy(float),
                           b.open.to_numpy(float))
        rows = []
        for _, r in self.g.iterrows():
            t, h, lo, c, o = self.arr[r.symbol]
            d = pd.Timestamp(r.date).date()
            i0 = int(np.searchsorted(t, E._utc_minute(d, "09:30", "America/New_York")))
            i_or = int(np.searchsorted(t, E._utc_minute(d, "09:45", "America/New_York")))
            i1 = int(np.searchsorted(t, E._utc_minute(d, "16:00", "America/New_York")))
            H, L = h[i0:i_or].max(), lo[i0:i_or].min()
            pc = c[i_or:i1]
            ku, kd = _first(pc > H), _first(pc < L)
            if ku < 0 and kd < 0:
                bdir, k = 0, -1
            elif kd < 0 or (0 <= ku < kd):
                bdir, k = 1, i_or + ku
            else:
                bdir, k = -1, i_or + kd
            rows.append({"i0": i0, "i_or": i_or, "i1": i1, "or_h": H, "or_l": L, "or_dir": bdir, "or_k": k})
        self.g = pd.concat([self.g.reset_index(drop=True), pd.DataFrame(rows)], axis=1)
        s = np.sign(self.g.gap)
        self.g["or_vs_gap"] = np.select([self.g.or_dir == 0, self.g.or_dir == s], ["sin ruptura", "a favor del gap"],
                                        "hacia el cierre")
        self.g["gap_vs_tendencia"] = np.select(
            [((s > 0) & (self.g.daily_trend == "alcista")) | ((s < 0) & (self.g.daily_trend == "bajista")),
             ((s > 0) & (self.g.daily_trend == "bajista")) | ((s < 0) & (self.g.daily_trend == "alcista"))],
            ["a favor de la tendencia", "contra la tendencia"], "tendencia lateral")

    # -- 1. Probabilidades del gap --------------------------------------------------------------
    def gap_probabilities(self) -> dict[str, pd.DataFrame]:
        g = self.g

        def prob(df):
            r = {"dias": len(df)}
            for x in FILL:
                r[f"retrocede {x:g}"] = 100 * df[f"t_fill_{lv(x)}"].notna().mean()
            for x in AWAY:
                r[f"se aleja {x:g}"] = 100 * df[f"t_away_{lv(x)}"].notna().mean()
            a, f = df.t_away_0272, df.t_fill_0500
            r["50% antes que −0.272"] = 100 * (f.notna() & (a.isna() | (f < a))).mean()
            f1 = df.t_fill_1000
            r["cierra gap antes que −0.618"] = 100 * (f1.notna() & (df.t_away_0618.isna() | (f1 < df.t_away_0618))).mean()
            return pd.Series(r)

        out = {}
        for by in ["gap_dir", "gap_size", "gap_vs_tendencia", "open_vs_prev_range", "or_vs_gap", "year"]:
            out[by] = g.groupby(by).apply(prob, include_groups=False).round(1)
        out["total"] = prob(g).to_frame("todos").T.round(1)
        out["gap_dir_x_size"] = g.groupby(["gap_dir", "gap_size"]).apply(prob, include_groups=False).round(1)
        return out

    # -- 2. Patrones ----------------------------------------------------------------------------
    def _trades_for_day(self, r) -> list[dict]:
        t, h, lo, c, o = self.arr[r.symbol]
        i0, i1 = int(r.i0), int(r.i1)
        H, L, G, O = r.or_h, r.or_l, r.gap, r.ny_open
        hh, ll, cc = h[i0:i1], lo[i0:i1], c[i0:i1]
        s = 1 if G > 0 else -1           # dirección del gap
        P = lambda p: O - p * G          # noqa: E731  precio del nivel p
        out = []

        def add(pat, var, res):
            if res:
                out.append({"pattern": pat, "variant": var, **res})

        # P1: fade en la apertura (hacia el cierre anterior). Entrada al open de las 09:30.
        for tgt, stp in itertools.product([0.382, 0.5, 0.618, 1.0], [0.272, 0.618, 1.0]):
            res = sim(hh, ll, cc, -s, O, P(-stp), P(tgt), start=0) if True else None
            if res is not None:
                # la vela de entrada (09:30) también puede tocar stop: conservador -> se revisa
                if (s > 0 and hh[0] >= P(-stp)) or (s < 0 and ll[0] <= P(-stp)):
                    res = {"outcome": "stop", "r_gross": -1.0,
                           "r_net": -1.0 - 2 * C.COST_BP_PER_SIDE / 1e4 * O / abs(O - P(-stp))}
            add("P1", f"obj {tgt:g} · stop −{stp:g}", res)

        k = int(r.or_k) - i0 if r.or_dir != 0 else -1
        # P2: ruptura del OR hacia el cierre -> fade; stop en el otro extremo del OR
        if k >= 0 and r.or_dir == -s:
            e = cc[k]
            stop = H if s > 0 else L
            for tgt in [0.5, 0.618, 1.0]:
                add("P2", f"obj {tgt:g} · stop extremo OR", sim(hh, ll, cc, -s, e, stop, P(tgt), start=k))
        # P3: ruptura del OR a favor del gap -> continuación; stop en el otro extremo del OR
        if k >= 0 and r.or_dir == s:
            e = cc[k]
            stop = L if s > 0 else H
            for tgt in [0.618, 1.0]:
                add("P3", f"obj −{tgt:g} · stop extremo OR", sim(hh, ll, cc, s, e, stop, P(-tgt), start=k))
            add("P3", "obj 2R · stop extremo OR", sim(hh, ll, cc, s, e, stop, e + 2 * (e - stop), start=k))
        # P4: retroceso Fibonacci del gap y continuación a favor del gap (orden límite)
        for ent, stp, tgt in itertools.product([0.382, 0.5, 0.618], [0.786, 1.0, 1.272], [0.0, -0.272]):
            if stp <= ent:
                continue
            add("P4", f"entrada {ent:g} · stop {stp:g} · obj {tgt:g}",
                sim(hh, ll, cc, s, P(ent), P(stp), P(tgt), start=1, limit=True))
        # P5: el precio cierra el gap (toca el cierre anterior) y sigue: límite en p = 1
        for stp, tgt in itertools.product([0.618, 0.786], [1.272, 1.618]):
            add("P5", f"stop {stp:g} · obj {tgt:g}",
                sim(hh, ll, cc, -s, P(1.0), P(stp), P(tgt), start=1, stop_entry=True))
        return out

    def run_patterns(self) -> tuple[pd.DataFrame, pd.DataFrame]:
        rows = []
        for _, r in self.g.iterrows():
            for tr in self._trades_for_day(r):
                rows.append({"symbol": r.symbol, "date": r.date, "year": r.year, "sample": r["sample"],
                             "gap_dir": r.gap_dir, "gap_size": r.gap_size, "gap_vs_tendencia": r.gap_vs_tendencia,
                             **tr})
        tr = pd.DataFrame(rows)
        res = []
        filters = [("todos", None, None)] + [("gap_size", "gap_size", v) for v in ["pequeño", "medio", "grande"]] \
            + [("gap_vs_tendencia", "gap_vs_tendencia", v) for v in ["a favor de la tendencia", "contra la tendencia"]]
        for (pat, var), g in tr.groupby(["pattern", "variant"]):
            for fname, col, val in filters:
                gg = g if col is None else g[g[col] == val]
                r = {"pattern": pat, "pattern_txt": PATTERN_TXT[pat], "variant": var,
                     "filtro": fname if col is None else f"{val}"}
                for smp in ("IS", "OOS"):
                    x = gg[gg["sample"] == smp]
                    r[f"{smp}_n"] = len(x)
                    r[f"{smp}_win"] = 100 * (x.outcome == "target").mean() if len(x) else np.nan
                    r[f"{smp}_exp_R"] = x.r_net.mean() if len(x) else np.nan
                    r[f"{smp}_exp_R_gross"] = x.r_gross.mean() if len(x) else np.nan
                    r[f"{smp}_total_R"] = x.r_net.sum()
                yrs = gg.groupby("year").r_net.mean()
                r["anios_positivos"] = f"{int((yrs > 0).sum())}/{len(yrs)}"
                r["por_simbolo_OOS"] = " · ".join(f"{s}:{v:+.2f}" for s, v in
                                                  gg[gg["sample"] == "OOS"].groupby("symbol").r_net.mean().items())
                res.append(r)
        return pd.DataFrame(res), tr

    # -- 3. Gráficos ----------------------------------------------------------------------------
    def chart_ladder(self, probs):
        """Escalera de niveles Fibonacci del gap con la probabilidad de tocarlos."""
        levels = [(-x, f"−{x:g}  (se aleja)") for x in AWAY[::-1]] + [(0, "0  apertura")] + \
                 [(x, f"{x:g}" + ("  cierre anterior" if x == 1 else "")) for x in FILL]
        fig, axes = plt.subplots(1, 3, figsize=(12, 5.2), sharey=True)
        for ax, size in zip(axes, ["pequeño", "medio", "grande"]):
            sub = self.g[self.g.gap_size == size]
            ys = np.arange(len(levels))
            vals = []
            for p, _ in levels:
                if p < 0:
                    vals.append(100 * sub[f"t_away_{lv(-p)}"].notna().mean())
                elif p == 0:
                    vals.append(100.0)
                else:
                    vals.append(100 * sub[f"t_fill_{lv(p)}"].notna().mean())
            cols = [style.ORANGE if p < 0 else style.GRAY if p == 0 else style.BLUE for p, _ in levels]
            ax.barh(ys, vals, color=cols, height=0.7, edgecolor=style.SURFACE, linewidth=1.5)
            for y, v, (p, _) in zip(ys, vals, levels):
                if p != 0:
                    ax.text(v + 1.5, y, f"{v:.0f}%", va="center", fontsize=8, color=style.INK)
            ax.axhline(ys[[p for p, _ in levels].index(1.0)], color=style.INK2, lw=0.8, ls="--")
            ax.set_yticks(ys, [l for _, l in levels])
            ax.set_xlim(0, 110)
            ax.set_xlabel("% de días que lo tocan (09:30-16:00)")
            ax.set_title(f"Gap {size} (n={len(sub)})", loc="left", fontsize=10)
            ax.grid(axis="y", visible=False)
        fig.suptitle("Fibonacci entre el cierre NY anterior y la apertura NY: probabilidad de alcanzar cada nivel\n"
                     "azul = retroceso hacia el cierre anterior · naranja = se aleja a favor del gap",
                     x=0.01, ha="left", fontsize=10)
        fig.tight_layout()
        fig.savefig(os.path.join(self.out, "patrones_gap_fibonacci.png"), dpi=150, bbox_inches="tight")
        plt.close(fig)

    def chart_paths(self):
        """Trayectoria mediana (en coordenadas p) según si el gap se cierra o no."""
        fig, axes = plt.subplots(1, 2, figsize=(11, 4.2), sharey=True)
        mins = np.arange(390)
        for ax, (name, mask) in zip(axes, [("Días que cierran el gap", self.g.t_fill_1000.notna()),
                                           ("Días que NO cierran el gap", self.g.t_fill_1000.isna())]):
            for size, col in zip(["pequeño", "medio", "grande"], [style.BLUE, style.GREEN, style.ORANGE]):
                sub = self.g[mask & (self.g.gap_size == size)]
                paths = []
                for _, r in sub.iterrows():
                    c = self.arr[r.symbol][3][int(r.i0):int(r.i1)]
                    p = (r.ny_open - c) / r.gap
                    if len(p) >= 300:
                        paths.append(np.pad(p[:390], (0, max(0, 390 - len(p))), mode="edge"))
                if len(paths) < 10:
                    continue
                M = np.vstack(paths)
                med = np.median(M, axis=0)
                ax.plot(mins, med, color=col, label=f"gap {size} (n={len(paths)})")
                ax.fill_between(mins, np.percentile(M, 25, axis=0), np.percentile(M, 75, axis=0),
                                color=col, alpha=0.10, linewidth=0)
            for y in [0, 0.5, 1.0]:
                ax.axhline(y, color=style.GRID, lw=1, ls="--", zorder=0)
                ax.text(392, y, f"{y:g}", va="center", fontsize=7.5, color=style.INK2)
            ax.set_xticks([0, 60, 120, 180, 240, 300, 390], ["9:30", "10:30", "11:30", "12:30", "13:30", "14:30", "16:00"])
            ax.set_title(name, loc="left", fontsize=10)
            ax.legend(fontsize=8, loc="upper left")
        axes[0].set_ylabel("p (0 = apertura, 1 = cierre anterior)")
        fig.suptitle("Trayectoria mediana del precio en coordenadas Fibonacci del gap (banda = percentiles 25-75)",
                     x=0.01, ha="left", fontsize=10)
        fig.tight_layout()
        fig.savefig(os.path.join(self.out, "trayectoria_gap.png"), dpi=150, bbox_inches="tight")
        plt.close(fig)

    def chart_examples(self):
        """Un día real reciente de cada patrón, con los niveles Fibonacci del gap."""
        g = self.g.sort_values(["gap_size", "date"], ascending=[True, False])   # 'grande' primero
        g = g[g.gap_size != "pequeño"]
        picks = {
            "Gap cerrado (fade)": g[g.t_fill_1000.notna() & g.t_away_0272.isna()],
            "Gap and go": g[g.t_fill_0382.isna() & g.t_away_1000.notna()],
            "Retroceso al 50-61.8 y continúa": g[g.t_fill_0500.notna() & g.t_fill_0786.isna() & g.t_away_0272.notna()
                                                  & (g.t_fill_0500 < g.t_away_0272)],
            "Cierra el gap y se extiende a 1.618": g[g.t_fill_1618.notna()],
        }
        fig, axes = plt.subplots(2, 2, figsize=(12, 7.5))
        for ax, (name, sub) in zip(axes.ravel(), picks.items()):
            if sub.empty:
                ax.set_visible(False)
                continue
            r = sub.iloc[0]
            b = self.bars[r.symbol]
            t, h, lo, c, o = self.arr[r.symbol]
            seg = b.iloc[int(r.i0):int(r.i1)].resample("5min").agg(
                {"open": "first", "high": "max", "low": "min", "close": "last"}).dropna()
            x = np.arange(len(seg))
            up = seg.close >= seg.open
            ax.vlines(x, seg.low, seg.high, color=style.INK2, lw=0.7)
            ax.bar(x[up], (seg.close - seg.open)[up], bottom=seg.open[up], color=style.BLUE, width=0.7)
            ax.bar(x[~up], (seg.close - seg.open)[~up], bottom=seg.open[~up], color=style.ORANGE, width=0.7)
            for p in [-1.0, -0.618, -0.272, 0, 0.382, 0.5, 0.618, 1.0, 1.272, 1.618]:
                y = r.ny_open - p * r.gap
                strong = p in (0, 1.0)
                ax.axhline(y, color=style.INK if strong else style.GRID, lw=1 if strong else 0.8,
                           ls="-" if strong else "--", zorder=0)
                if p in (-1.0, -0.618, 0, 0.5, 1.0, 1.618):
                    ax.text(len(seg) + 0.5, y, f"{p:g}" + (" cierre ant." if p == 1 else " apertura" if p == 0 else ""),
                            va="center", fontsize=7, color=style.INK2)
            ticks = [0, 12, 24, 36, 48, 60, 72]
            ax.set_xticks(ticks, [seg.index[i].tz_convert(NY).strftime("%H:%M") for i in ticks if i < len(seg)][:len(ticks)])
            ax.set_title(f"{name} — {r.symbol} {r.date} (gap {r.gap_bp:+.0f} pb)", loc="left", fontsize=9.5)
            ax.grid(axis="x", visible=False)
        fig.suptitle("Ejemplos reales de cada patrón (velas de 5 min, niveles Fibonacci del gap)", x=0.01, ha="left")
        fig.tight_layout()
        fig.savefig(os.path.join(self.out, "ejemplos_patrones.png"), dpi=150, bbox_inches="tight")
        plt.close(fig)

    def chart_equity(self, best: pd.DataFrame, tr: pd.DataFrame):
        fig, ax = plt.subplots(figsize=(11, 4.4))
        cols = [style.BLUE, style.ORANGE, style.GREEN, style.AMBER, style.PINK]
        for col, (_, b) in zip(cols, best.iterrows()):
            x = tr[(tr.pattern == b.pattern) & (tr.variant == b.variant)]
            if b.filtro != "todos":
                x = x[(x.gap_size == b.filtro) | (x.gap_vs_tendencia == b.filtro)]
            x = x.sort_values(["date", "symbol"])
            ax.plot(pd.to_datetime(x.date), x.r_net.cumsum(), color=col,
                    label=f"{b.pattern} {b.variant} [{b.filtro}]", lw=1.6)
        ax.axvline(pd.Timestamp(C.IS_END), color=style.INK2, lw=1, ls="--")
        ax.text(pd.Timestamp(C.IS_END), ax.get_ylim()[1], "  out-of-sample →", va="top", fontsize=8, color=style.INK2)
        ax.axhline(0, color=style.INK2, lw=0.8)
        ax.set_ylabel("R acumulado (neto)")
        ax.set_title("Mejor variante in-sample de cada patrón (NAS100 + US500)", loc="left", fontsize=10)
        ax.legend(fontsize=7.5, loc="upper left")
        fig.savefig(os.path.join(self.out, "patrones_equity.png"), dpi=150, bbox_inches="tight")
        plt.close(fig)

    # -- 4. Ejecución e informe -------------------------------------------------------------------
    def run(self) -> dict:
        probs = self.gap_probabilities()
        res, tr = self.run_patterns()
        ok = res[res.IS_n >= self.MIN_N_IS]
        best = ok.sort_values("IS_exp_R", ascending=False).groupby("pattern").head(1).sort_values("pattern")
        robust = ok[(ok.IS_exp_R > 0) & (ok.OOS_exp_R > 0) & (ok.OOS_n >= 20)].sort_values("OOS_exp_R", ascending=False)
        res.to_csv(os.path.join(self.out, "patrones_resultados.csv"), index=False, float_format="%.4f")
        tr.to_csv(os.path.join(self.out, "patrones_operaciones.csv"), index=False, float_format="%.4f")
        for k, v in probs.items():
            v.to_csv(os.path.join(self.out, f"gap_prob_{k}.csv"))
        self.chart_ladder(probs)
        self.chart_paths()
        self.chart_examples()
        self.chart_equity(best, tr)
        cols = ["pattern", "variant", "filtro", "IS_n", "IS_win", "IS_exp_R", "IS_exp_R_gross", "OOS_n", "OOS_win",
                "OOS_exp_R", "OOS_exp_R_gross", "anios_positivos", "por_simbolo_OOS"]
        n_flat = int((self.all_gaps.gap_dir == "plano").sum())
        L = [f"# Agente de estrategia — Fibonacci cierre NY → apertura NY ({C.SOURCE}, {C.START} → {C.END})\n",
             f"Días con gap: {len(self.g)} (más {n_flat} días de gap plano, < {C.GAP_FLAT_ADR:.0%} del rango diario medio). "
             f"Coste {C.COST_BP_PER_SIDE} pb por lado. IS hasta {C.IS_END}.\n",
             "## Probabilidad de alcanzar cada nivel del gap (%)\n",
             probs["total"].to_markdown(floatfmt=".1f"),
             "\n### Por tamaño del gap\n", probs["gap_size"].to_markdown(floatfmt=".1f"),
             "\n### Por dirección y tamaño\n", probs["gap_dir_x_size"].to_markdown(floatfmt=".1f"),
             "\n### Gap frente a la tendencia diaria\n", probs["gap_vs_tendencia"].to_markdown(floatfmt=".1f"),
             "\n### Apertura frente al rango del día anterior\n", probs["open_vs_prev_range"].to_markdown(floatfmt=".1f"),
             "\n### Primera ruptura del OR15 frente al gap\n", probs["or_vs_gap"].to_markdown(floatfmt=".1f"),
             "\n### Por año (estabilidad)\n", probs["year"].to_markdown(floatfmt=".1f"),
             "\n## Patrones: mejor variante in-sample de cada uno y su resultado out-of-sample\n",
             best[cols].to_markdown(index=False, floatfmt=".2f"),
             f"\n## Variantes positivas en IS y OOS ({len(robust)} de {len(ok)} con n IS ≥ {self.MIN_N_IS})\n",
             robust[cols].head(30).to_markdown(index=False, floatfmt=".2f") if len(robust) else "Ninguna.",
             ]
        with open(os.path.join(self.out, "ESTRATEGIA.md"), "w") as fh:
            fh.write("\n".join(L) + "\n")
        return {"probs": probs, "results": res, "trades": tr, "best": best, "robust": robust, "gaps": self.g}


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default=C.SOURCE)
    a = ap.parse_args()
    C.use_source(a.source)
    con = db.connect(db.db_light_path())
    gaps = pd.read_sql("SELECT * FROM gaps", con)
    bars = {s: db.load_bars(s) for s in C.SYMBOLS}
    out = os.path.join(db.results_dir(), "strategy")
    r = StrategyAgent(bars, gaps, out).run()
    print(f"[estrategia] {len(r['results'])} variantes·filtro, {len(r['robust'])} positivas en IS y OOS -> {out}")


if __name__ == "__main__":
    main()
