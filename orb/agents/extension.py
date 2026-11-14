"""
extension.py — Estudio del agente de estrategia: ¿qué pasa cuando el precio supera la extensión
1.618 del rango de apertura? ¿Con qué probabilidad sigue hasta 2.0 (y 2.618)?

Coordenada x del estudio ORB (orientada a la ruptura, en unidades del rango R):
    x = 0      nivel roto            x = 0.272  extensión 1.272
    x = 0.618  extensión 1.618       x = 1.0    extensión 2.0        x = 1.618  extensión 2.618
    x = −1     extremo opuesto del rango

Se mide desde la PRIMERA vela que alcanza 1.618 (después de la vela de ruptura) hasta el final del
horizonte de la sesión (12:00 Londres, 16:00 Nueva York):

1. P(2.0 | 1.618) y P(2.618 | 1.618), por sesión, rango de 15/20 min, tamaño del rango, minutos
   hasta llegar a 1.618, si hubo retest antes, contexto previo, año (estabilidad) e índice.
2. Retroceso tras tocar 1.618: probabilidad de volver a 1.272 / al nivel roto / a la mitad del
   rango ANTES de llegar a 2.0, y P(2.0) una vez que ya retrocedió (para la proyección en vivo).
3. Operaciones hacia 2.0, simuladas vela a vela con supuestos conservadores (stop primero en
   empates, coste 1 pb por lado), elegidas en 2022-2024 y comprobadas en 2025-2026:
     A  entrada al tocar 1.618 (orden stop), stop en 1.272 / nivel roto / 1.0 + 0.382·R
     B  tras tocar 1.618, entrada límite en el retroceso a 1.272, stop en nivel roto / mitad del rango
4. Gráficos e informe EXTENSION_2.md en results/<fuente>/strategy/.
"""
from __future__ import annotations

import os

import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

import config as C
from agents import style

T1618, T2, T2618 = 0.618, 1.0, 1.618
PULLS = {"1.272": 0.272, "nivel roto": 0.0, "mitad del rango": -0.5}
LEVEL_TXT = {0.618: "1.618", 0.382: "1.382", 0.272: "1.272", 0.0: "nivel roto", -0.5: "mitad del rango"}


def _first(m: np.ndarray) -> int:
    i = np.flatnonzero(m)
    return int(i[0]) if i.size else -1


def _sim(f, a, c, start, entry, stop, target, kind, cost_x):
    """
    Operación a favor de la ruptura en coordenadas x desde la vela `start`.
    kind 'stop'  -> entra cuando fav >= entry (precio llega a 1.618 subiendo)
    kind 'limit' -> entra cuando adv <= entry; se cancela si el objetivo llega antes
    En la vela de entrada sólo se evalúa el stop. Empate stop/objetivo -> stop. Sin salida -> cierre.
    """
    if kind == "stop":
        jf = _first(f[start:] >= entry)
        if jf < 0:
            return None
    else:
        jf, jt = _first(a[start:] <= entry), _first(f[start:] >= target)
        if jf < 0 or (0 <= jt < jf):
            return None
    i = start + jf
    risk = entry - stop
    js = _first(a[i:] <= stop)
    tg = f[i:] >= target
    tg[0] = False
    jt = _first(tg)
    if js >= 0 and (jt < 0 or js <= jt):
        out, x = "stop", stop
    elif jt >= 0:
        out, x = "target", target
    else:
        out, x = "time", float(c[-1])
    r = (x - entry) / risk
    return {"outcome": out, "r_gross": r, "r_net": r - cost_x / risk}


class ExtensionStudy:
    def __init__(self, ev: pd.DataFrame, paths: dict, out_dir: str):
        e = ev[ev.break_dir != "none"].copy()
        # tamaño del rango por terciles (misma definición que el analista y el indicador)
        cuts = {k: g.or_vs_adr.dropna().quantile([1 / 3, 2 / 3]).values for k, g in e.groupby(["session", "or_min"])}
        e["tam_rango"] = [("n/d" if not np.isfinite(v) else "pequeño" if v < cuts[(s, n)][0] else
                           "medio" if v < cuts[(s, n)][1] else "grande")
                          for s, n, v in zip(e.session, e.or_min, e.or_vs_adr)]
        self.cuts = cuts
        self.e = e
        self.paths = paths
        self.out = out_dir
        os.makedirs(out_dir, exist_ok=True)

    # -- 1. eventos condicionados a tocar 1.618 ----------------------------------------------------
    def events(self) -> pd.DataFrame:
        rows = []
        for _, r in self.e.iterrows():
            p = self.paths[r.event_id]
            f, a = p.fav, p.adv
            j = _first(f >= T1618)
            if j < 0:
                continue
            ff, aa = f[j + 1:], a[j + 1:]
            k2 = _first(ff >= T2)
            k26 = _first(ff >= T2618)
            row = {"event_id": r.event_id, "symbol": r.symbol, "date": r.date, "anio": r.date[:4],
                   "sample": r["sample"], "session": r.session, "or_min": int(r.or_min), "tam_rango": r.tam_rango,
                   "contexto_previo": r.pre_trend,
                   "ruptura_vs_previo": ("a favor" if (r.break_dir == "up" and r.pre_trend == "alza") or
                                         (r.break_dir == "down" and r.pre_trend == "baja") else
                                         "en contra" if (r.break_dir == "up" and r.pre_trend == "baja") or
                                         (r.break_dir == "down" and r.pre_trend == "alza") else "sin tendencia"),
                   "min_a_1618": j + 1,
                   "retest_antes": bool((a[:j + 1] <= 0).any()),
                   "llega_2": bool(f[j] >= T2 or k2 >= 0),
                   "llega_2618": bool(f[j] >= T2618 or k26 >= 0),
                   "min_1618_a_2": (k2 + 1) if k2 >= 0 else (0 if f[j] >= T2 else np.nan),
                   "misma_vela_2": bool(f[j] >= T2)}
            lim = k2 if k2 >= 0 else len(aa)
            row["retroceso_antes_2"] = float(T1618 - min(a[j], aa[:lim + 1].min() if lim > 0 else a[j]))
            for name, lv in PULLS.items():
                k = _first(aa <= lv)
                before = k >= 0 and (k2 < 0 or k <= k2) and not row["misma_vela_2"]
                row[f"vuelve_{name}"] = before
                # tras ese retroceso, ¿llega luego a 2.0?
                row[f"llega_2_tras_{name}"] = bool(before and (ff[k + 1:] >= T2).any()) if before else np.nan
            row["tiempo"] = "≤ 30 min" if j + 1 <= 30 else "30-90 min" if j + 1 <= 90 else "> 90 min"
            rows.append(row)
        return pd.DataFrame(rows)

    def probabilities(self, x: pd.DataFrame) -> dict[str, pd.DataFrame]:
        def agg(g):
            r = {"n": len(g), "llega_2": 100 * g.llega_2.mean(), "llega_2618": 100 * g.llega_2618.mean()}
            for name in PULLS:
                r[f"vuelve_{name}_antes_de_2"] = 100 * g[f"vuelve_{name}"].mean()
                s = g[g[f"vuelve_{name}"]]
                r[f"2_tras_volver_{name}"] = 100 * s[f"llega_2_tras_{name}"].astype(float).mean() if len(s) >= 20 else np.nan
            r["mediana_min_1618_a_2"] = g.min_1618_a_2.median()
            return pd.Series(r)

        out = {"general": x.groupby(["session", "or_min"]).apply(agg, include_groups=False).round(1)}
        for by in ["tam_rango", "tiempo", "retest_antes", "ruptura_vs_previo", "anio", "symbol"]:
            out[by] = x.groupby(["session", "or_min", by]).apply(agg, include_groups=False).round(1)
        return out

    # -- 2. operaciones hacia 2.0 -----------------------------------------------------------------
    def trades(self) -> pd.DataFrame:
        variants = [("A", "entrada al tocar 1.618", 0.618, s, "stop") for s in (0.382, 0.272, 0.0)] + \
                   [("B", "límite en 1.272 tras tocar 1.618", 0.272, s, "limit") for s in (0.0, -0.5)]
        rows = []
        for _, r in self.e.iterrows():
            p = self.paths[r.event_id]
            f, a, c = p.fav, p.adv, p.close
            j = _first(f >= T1618)
            if j < 0:
                continue
            cost_x = 2 * C.COST_BP_PER_SIDE / 1e4 * p.price / p.range_pts
            for code, txt, entry, stop, kind in variants:
                start = 0 if kind == "stop" else j + 1
                res = _sim(f, a, c, start, entry, stop, T2, kind, cost_x)
                if res:
                    rows.append({"event_id": r.event_id, "symbol": r.symbol, "date": r.date, "anio": r.date[:4],
                                 "sample": r["sample"], "session": r.session, "or_min": int(r.or_min),
                                 "tam_rango": r.tam_rango, "variante": code,
                                 "descripcion": f"{txt} · stop {LEVEL_TXT[stop]} · objetivo 2.0",
                                 "necesita_pct": 100 * (entry - stop) / (T2 - stop), **res})
        return pd.DataFrame(rows)

    def trade_summary(self, t: pd.DataFrame) -> pd.DataFrame:
        rows = []
        for keys, g in t.groupby(["session", "or_min", "descripcion"]):
            for tam, gg in [("todos", g)] + list(g.groupby("tam_rango")):
                if tam == "n/d":
                    continue
                r = dict(zip(["session", "or_min", "descripcion"], keys))
                r["tam_rango"] = tam
                r["necesita_pct"] = round(gg.necesita_pct.iloc[0], 1)
                for smp in ("IS", "OOS"):
                    s = gg[gg["sample"] == smp]
                    r[f"{smp}_n"] = len(s)
                    r[f"{smp}_llega_2_pct"] = round(100 * (s.outcome == "target").mean(), 1) if len(s) else np.nan
                    r[f"{smp}_R_bruto"] = round(s.r_gross.mean(), 3) if len(s) else np.nan
                    r[f"{smp}_R_neto"] = round(s.r_net.mean(), 3) if len(s) else np.nan
                yrs = gg.groupby("anio").r_net.mean()
                r["anios_positivos"] = f"{int((yrs > 0).sum())}/{len(yrs)}"
                rows.append(r)
        return pd.DataFrame(rows)

    def management(self) -> pd.DataFrame:
        """
        Operación ya abierta a favor de la ruptura que llega a 1.618: ¿cobrar ahí o dejar correr a 2.0?
        Salida media (en unidades x del rango) de dejar correr hasta 2.0 con el stop movido a
        nivel roto / 1.272 / 1.382, frente a cobrar en 1.618 (x = 0.618). Sin salida: cierre de la sesión.
        """
        rows = []
        for _, r in self.e.iterrows():
            p = self.paths[r.event_id]
            f, a, c = p.fav, p.adv, p.close
            j = _first(f >= T1618)
            if j < 0:
                continue
            ff, aa, cc = f[j + 1:], a[j + 1:], c[j + 1:]
            row = {"session": r.session, "or_min": int(r.or_min), "sample": r["sample"], "tam_rango": r.tam_rango}
            for name, stop in [("stop en nivel roto", 0.0), ("stop en 1.272", 0.272), ("stop en 1.382", 0.382)]:
                if f[j] >= T2:
                    x = T2
                else:
                    ks, kt = _first(aa <= stop), _first(ff >= T2)
                    x = stop if ks >= 0 and (kt < 0 or ks <= kt) else T2 if kt >= 0 else (float(cc[-1]) if cc.size else T1618)
                row[name] = x
            rows.append(row)
        m = pd.DataFrame(rows)
        cols = ["stop en nivel roto", "stop en 1.272", "stop en 1.382"]
        out = m.groupby(["session", "or_min"])[cols].mean()
        for smp in ("IS", "OOS"):
            out[f"stop 1.272 ({smp})"] = m[m["sample"] == smp].groupby(["session", "or_min"])["stop en 1.272"].mean()
        out["cobrar en 1.618"] = T1618
        # en extensión Fibonacci (1 + x) para leerlo igual que en el gráfico
        return (out + 1).round(3)

    # -- 3. gráficos ------------------------------------------------------------------------------
    def chart_probs(self, probs):
        t = probs["tam_rango"].reset_index()
        t = t[t.tam_rango != "n/d"]
        fig, axes = plt.subplots(1, 2, figsize=(11, 4), sharey=True)
        order = ["pequeño", "medio", "grande"]
        for ax, ses in zip(axes, ["London", "NewYork"]):
            s = t[(t.session == ses) & (t.or_min == 15)].set_index("tam_rango").reindex(order)
            g = probs["general"].loc[(ses, 15)]
            xs = np.arange(4)
            bars = [("Llega a 2.0", "llega_2", style.BLUE),
                    ("…si antes volvió a 1.272", "2_tras_volver_1.272", style.AMBER),
                    ("…si antes volvió al nivel roto", "2_tras_volver_nivel roto", style.ORANGE)]
            w = 0.26
            for i, (lab, col, colr) in enumerate(bars):
                vals = list(s[col].values) + [g[col]]
                ax.bar(xs + (i - 1) * w, vals, w - 0.03, color=colr, label=lab)
                for xx, v in zip(xs + (i - 1) * w, vals):
                    if np.isfinite(v):
                        ax.text(xx, v + 1.2, f"{v:.0f}", ha="center", fontsize=7.5, color=style.INK)
            ax.set_xticks(xs, ["rango pequeño", "medio", "grande", "todos"])
            ax.set_ylim(0, 100)
            ax.set_title(f"{'Londres' if ses == 'London' else 'Nueva York'} · OR 15 min", loc="left", fontsize=10)
            ax.grid(axis="x", visible=False)
        axes[0].set_ylabel("% de días que ya tocaron 1.618")
        axes[0].legend(fontsize=8, loc="lower left")
        fig.suptitle("Una vez tocado el 1.618: probabilidad de llegar a 2.0 (y cómo baja si antes retrocede)",
                     x=0.01, ha="left", fontsize=10.5)
        fig.tight_layout()
        fig.savefig(os.path.join(self.out, "ext2_probabilidad.png"), dpi=150, bbox_inches="tight")
        plt.close(fig)

    def chart_survival(self):
        """Dado que tocó 1.618: P(extensión máxima ≥ x) para x de 1.618 a 3.0."""
        fig, ax = plt.subplots(figsize=(8, 3.8))
        xs = np.linspace(0.618, 2.0, 140)
        for ses, col in [("London", style.BLUE), ("NewYork", style.ORANGE)]:
            mx = []
            for _, r in self.e[(self.e.session == ses) & (self.e.or_min == 15)].iterrows():
                f = self.paths[r.event_id].fav
                if f.size and f.max() >= T1618:
                    mx.append(f.max())
            mx = np.array(mx)
            ax.plot(xs + 1, [100 * (mx >= v).mean() for v in xs], color=col,
                    label=f"{'Londres' if ses == 'London' else 'Nueva York'} (n={len(mx)})")
        for v in [1.618, 2.0, 2.272, 2.618]:
            ax.axvline(v, color=style.GRID, lw=1, ls="--", zorder=0)
            ax.text(v, 101, f"{v:g}", ha="center", fontsize=8, color=style.INK2)
        ax.set_xlabel("Extensión Fibonacci del rango de apertura")
        ax.set_ylabel("% de días que la alcanzan")
        ax.set_ylim(0, 105)
        ax.set_title("Días que tocaron 1.618: hasta dónde llega la extensión máxima (OR 15 min)", loc="left",
                     fontsize=10, pad=14)
        ax.legend(fontsize=8)
        fig.savefig(os.path.join(self.out, "ext2_supervivencia.png"), dpi=150, bbox_inches="tight")
        plt.close(fig)

    def chart_pullback(self, x):
        fig, ax = plt.subplots(figsize=(8, 3.6))
        bins = np.arange(-0.25, 1.75, 0.0625)
        for ses, col in [("London", style.BLUE), ("NewYork", style.ORANGE)]:
            s = x[(x.session == ses) & (x.or_min == 15) & x.llega_2 & ~x.misma_vela_2].retroceso_antes_2
            ax.hist(s.clip(upper=1.7), bins=bins, color=col, alpha=0.55, label=f"{'Londres' if ses == 'London' else 'Nueva York'}",
                    weights=np.full(len(s), 100 / max(len(s), 1)))
        for v, t in [(0.346, "1.272"), (0.618, "nivel roto"), (1.118, "mitad")]:
            ax.axvline(v, color=style.INK2, lw=0.8, ls="--")
            ax.text(v, ax.get_ylim()[1] * 0.95, " " + t, fontsize=8, color=style.INK2)
        ax.set_xlabel("Retroceso desde 1.618 antes de llegar a 2.0 (en rangos de apertura)")
        ax.set_ylabel("% de los días que llegan a 2.0")
        ax.set_title("Cuánto retrocede el precio desde 1.618 antes de alcanzar 2.0 (OR 15 min)", loc="left", fontsize=10)
        ax.legend(fontsize=8)
        fig.savefig(os.path.join(self.out, "ext2_retroceso.png"), dpi=150, bbox_inches="tight")
        plt.close(fig)

    # -- 4. ejecución -----------------------------------------------------------------------------
    def run(self) -> dict:
        x = self.events()
        probs = self.probabilities(x)
        t = self.trades()
        ts = self.trade_summary(t)
        mg = self.management()
        mg.to_csv(os.path.join(self.out, "ext2_gestion.csv"))
        x.to_csv(os.path.join(self.out, "ext2_eventos.csv"), index=False)
        for k, v in probs.items():
            v.to_csv(os.path.join(self.out, f"ext2_prob_{k}.csv"))
        ts.to_csv(os.path.join(self.out, "ext2_operaciones_resumen.csv"), index=False)
        self.chart_probs(probs)
        self.chart_survival()
        self.chart_pullback(x)
        self.report(x, probs, ts, mg)
        return {"events": x, "probs": probs, "trades": t, "summary": ts, "management": mg}

    def report(self, x, probs, ts, mg):
        cols_p = ["n", "llega_2", "llega_2618", "vuelve_1.272_antes_de_2", "2_tras_volver_1.272",
                  "vuelve_nivel roto_antes_de_2", "2_tras_volver_nivel roto", "mediana_min_1618_a_2"]
        tt = ts[ts.tam_rango == "todos"]
        cols_t = ["session", "or_min", "descripcion", "necesita_pct", "IS_n", "IS_llega_2_pct", "IS_R_bruto", "IS_R_neto",
                  "OOS_n", "OOS_llega_2_pct", "OOS_R_bruto", "OOS_R_neto", "anios_positivos"]
        rob = ts[(ts.IS_n >= 40) & (ts.IS_R_neto > 0) & (ts.OOS_R_neto > 0)]
        L = [f"# Agente de estrategia — de 1.618 a 2.0 ({C.SOURCE}, {C.START} → {C.END})\n",
             f"Días que tocaron 1.618 tras la ruptura: {len(x)} de {len(self.e)} rupturas. Se mide desde la primera "
             "vela que toca 1.618 hasta el final de la sesión. Coste 1 pb por lado.\n",
             "## Probabilidad de llegar a 2.0 una vez tocado 1.618 (%)\n",
             probs["general"][cols_p].to_markdown(floatfmt=".1f"),
             "\n`vuelve_X_antes_de_2`: % de días en que, tras tocar 1.618, el precio retrocede hasta X antes de llegar "
             "a 2.0. `2_tras_volver_X`: de esos días, % que aun así llega después a 2.0.\n",
             "\n### Según el tamaño del rango\n", probs["tam_rango"][cols_p].to_markdown(floatfmt=".1f"),
             "\n### Según cuánto tardó en llegar a 1.618 desde la ruptura\n", probs["tiempo"][cols_p].to_markdown(floatfmt=".1f"),
             "\n### Según si hubo retest del nivel roto antes de 1.618\n", probs["retest_antes"][cols_p].to_markdown(floatfmt=".1f"),
             "\n### Según la ruptura frente al contexto previo\n", probs["ruptura_vs_previo"][cols_p].to_markdown(floatfmt=".1f"),
             "\n### Por año (estabilidad)\n", probs["anio"][["n", "llega_2", "2_tras_volver_1.272"]].to_markdown(floatfmt=".1f"),
             "\n### Por índice\n", probs["symbol"][["n", "llega_2", "2_tras_volver_1.272"]].to_markdown(floatfmt=".1f"),
             "\n## Operaciones hacia 2.0 (todas las rupturas que tocan 1.618)\n",
             "`necesita_pct` = aciertos necesarios para no perder (riesgo / (riesgo + beneficio)).\n",
             tt[cols_t].to_markdown(index=False, floatfmt=".2f"),
             "\n## Gestión: con una operación abierta que llega a 1.618, ¿cobrar o dejar correr a 2.0?\n",
             "Nivel medio de salida, expresado como extensión Fibonacci, al dejar correr hasta 2.0 moviendo el stop "
             "(cobrar en 1.618 = 1.618). Un valor mayor que 1.618 favorece dejar correr.\n",
             mg.to_markdown(floatfmt=".3f"),
             f"\n## Variantes positivas en 2022-2024 y en 2025-2026 ({len(rob)} de {int((ts.IS_n >= 40).sum())}, "
             "incluidos filtros por tamaño del rango)\n",
             rob[cols_t[:3] + ["tam_rango"] + cols_t[3:]].to_markdown(index=False, floatfmt=".2f") if len(rob) else "Ninguna.",
             ]
        with open(os.path.join(self.out, "EXTENSION_2.md"), "w") as fh:
            fh.write("\n".join(L) + "\n")
