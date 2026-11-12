"""
analyst.py — Agente analista: probabilidad de que cada evento se repita y en qué condiciones.

Qué hace, de forma autónoma, sobre la base de datos (tablas `events` y `gaps`):

1. Define los EVENTOS que se miden tras cada ruptura del rango de apertura (retest, retroceso al
   50 %, toque del extremo opuesto, cada escenario del árbol, etc.).
2. Define las CONDICIONES conocidas antes o en el momento de la ruptura: contexto previo a la
   apertura (alza / baja / rango), si la ruptura va a favor o en contra de ese contexto, tendencia
   diaria, dirección del día anterior, tamaño del rango, velocidad de la ruptura, día de la
   semana, gap de la apertura de NY, lo que hizo Londres ese día y lo que pasó el día anterior.
3. Para cada combinación sesión × rango × evento × condición calcula P(evento | condición), la
   compara con la probabilidad base, aplica un test de dos proporciones y corrige por pruebas
   múltiples (Benjamini-Hochberg).
4. Comprueba la ESTABILIDAD: el efecto debe tener el mismo signo en in-sample (2022-2024) y en
   out-of-sample (2025-2026) y repetirse en la mayoría de los años.
5. Mide la REPETICIÓN día a día (cadena de Markov): P(escenario hoy | escenario ayer).
6. Escribe hallazgos.csv, transiciones.csv, ANALISTA.md y gráficos en results/<fuente>/analyst/.
"""
from __future__ import annotations

import math
import os
import sys

import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config as C  # noqa: E402
import database as db  # noqa: E402
from agents import style  # noqa: E402

SCEN_LABEL = {
    "directa": "Continúa sin volver",
    "retest_continua": "Vuelve y continúa en la 1.ª dirección",
    "giro_continua": "Vuelve, rompe el otro extremo y continúa",
    "giro_rechazo": "Llega al otro extremo y es rechazado",
    "rango": "Vuelve y se queda en rango",
}
SCEN_ORDER = list(SCEN_LABEL)

EVENTS = {
    "retest": ("Vuelve al nivel roto", lambda e: e.retest.astype(bool)),
    "ret_50": ("Retrocede al 50 % del rango", lambda e: e.t_ret_0500.notna()),
    "toca_opuesto": ("Toca el extremo opuesto", lambda e: e.t_ret_1000.notna()),
    "rompe_opuesto": ("Cierra más allá del extremo opuesto", lambda e: e.opposite_break.astype(bool)),
    "ext_1618": ("Llega a la extensión 1.618", lambda e: e.t_ext_0618.notna()),
    "ext_1618_antes_50": ("1.618 antes de retroceder al 50 %",
                          lambda e: e.t_ext_0618.notna() & (e.t_ret_0500.isna() | (e.t_ext_0618 < e.t_ret_0500))),
    **{f"esc_{k}": (f"Escenario: {v}", (lambda k: lambda e: e.scenario == k)(k)) for k, v in SCEN_LABEL.items()},
}


def _rel(break_dir: pd.Series, ctx: pd.Series, up: str, down: str) -> pd.Series:
    """Relación de la ruptura con un contexto: a favor / en contra / desde rango."""
    fav = ((break_dir == "up") & (ctx == up)) | ((break_dir == "down") & (ctx == down))
    con = ((break_dir == "up") & (ctx == down)) | ((break_dir == "down") & (ctx == up))
    return pd.Series(np.select([fav, con], ["a favor", "en contra"], "sin tendencia"), index=break_dir.index)


def build_conditions(ev: pd.DataFrame, gaps: pd.DataFrame) -> pd.DataFrame:
    """Añade columnas de condición (todas conocidas al romper o antes)."""
    e = ev[ev.break_dir != "none"].copy()
    e["ruptura"] = e.break_dir.map({"up": "alcista", "down": "bajista"})
    e["contexto_previo"] = e.pre_trend
    e["ruptura_vs_previo"] = _rel(e.break_dir, e.pre_trend, "alza", "baja")
    e["tendencia_diaria"] = e.daily_trend
    e["ruptura_vs_diaria"] = _rel(e.break_dir, e.daily_trend, "alcista", "bajista")
    e["dia_anterior"] = e.prev_day_dir
    e["tam_rango"] = e.groupby(["session", "or_min", "symbol"]).or_vs_adr.transform(
        lambda s: pd.qcut(s, 3, labels=["pequeño", "medio", "grande"]) if s.notna().sum() > 10 else np.nan).astype(object)
    e["velocidad"] = np.where(e.min_to_break <= 5, "≤5 min", ">5 min")
    e["dia_semana"] = e.weekday
    e["anio"] = e.date.str[:4]

    # Repetición: lo que pasó en la sesión anterior del mismo tipo (día hábil previo)
    e = e.sort_values(["symbol", "session", "or_min", "date"])
    grp = e.groupby(["symbol", "session", "or_min"])
    e["escenario_ayer"] = grp.scenario.shift(1).map(SCEN_LABEL)
    e["ruptura_ayer"] = grp.ruptura.shift(1)
    e["igual_dir_ayer"] = np.where(e.ruptura_ayer.isna(), None,
                                   np.where(e.ruptura == e.ruptura_ayer, "misma dirección que ayer", "dirección contraria a ayer"))

    # Nueva York: lo que hizo Londres ese día y el gap de apertura
    lon = e[e.session == "London"].set_index(["symbol", "date", "or_min"])
    key = pd.MultiIndex.from_frame(e[["symbol", "date", "or_min"]])
    e["londres_escenario"] = lon.scenario.reindex(key).map(SCEN_LABEL).values
    lon_dir = lon.ruptura.reindex(key).to_numpy(dtype=object)
    e["vs_londres"] = np.where(pd.isna(lon_dir), None, np.where(e.ruptura.values == lon_dir, "igual que Londres", "contraria a Londres"))
    e.loc[e.session == "London", ["londres_escenario", "vs_londres"]] = np.nan
    g = gaps.set_index(["symbol", "date"])
    gk = pd.MultiIndex.from_frame(e[["symbol", "date"]])
    gdir = g.gap_dir.reindex(gk).to_numpy(dtype=object)
    e["gap_ny"] = gdir
    e["ruptura_vs_gap"] = np.select(
        [pd.isna(gdir), gdir == "plano",
         ((e.ruptura.values == "alcista") & (gdir == "alcista")) | ((e.ruptura.values == "bajista") & (gdir == "bajista")),
         ((e.ruptura.values == "alcista") & (gdir == "bajista")) | ((e.ruptura.values == "bajista") & (gdir == "alcista"))],
        [None, "gap plano", "a favor del gap", "hacia el cierre del gap"], None)
    e.loc[e.session == "London", ["gap_ny", "ruptura_vs_gap"]] = np.nan
    e["apertura_vs_dia_previo"] = g.open_vs_prev_range.reindex(gk).values
    e.loc[e.session == "London", "apertura_vs_dia_previo"] = np.nan
    return e


CONDITIONS = ["ruptura", "contexto_previo", "ruptura_vs_previo", "tendencia_diaria", "ruptura_vs_diaria",
              "dia_anterior", "tam_rango", "velocidad", "dia_semana", "escenario_ayer", "igual_dir_ayer",
              "londres_escenario", "vs_londres", "gap_ny", "ruptura_vs_gap", "apertura_vs_dia_previo"]


def _ztest(k1, n1, k2, n2) -> float:
    """p-valor bilateral del test de dos proporciones."""
    if min(n1, n2) == 0:
        return 1.0
    p = (k1 + k2) / (n1 + n2)
    se = math.sqrt(p * (1 - p) * (1 / n1 + 1 / n2))
    if se == 0:
        return 1.0
    z = (k1 / n1 - k2 / n2) / se
    return math.erfc(abs(z) / math.sqrt(2))


def _bh(p: np.ndarray) -> np.ndarray:
    """q-valores de Benjamini-Hochberg."""
    n = len(p)
    order = np.argsort(p)
    q = np.empty(n)
    prev = 1.0
    for rank, i in enumerate(order[::-1]):
        k = n - rank
        prev = min(prev, p[i] * n / k)
        q[i] = prev
    return q


class AnalystAgent:
    MIN_N = 40          # mínimo de casos en la condición
    MIN_LIFT = 5.0      # puntos porcentuales para considerar un efecto relevante

    def __init__(self, ev: pd.DataFrame, gaps: pd.DataFrame, out_dir: str):
        self.e = build_conditions(ev, gaps)
        self.out = out_dir
        os.makedirs(out_dir, exist_ok=True)

    # -- 1. Probabilidades condicionadas --------------------------------------------------------
    def findings(self) -> pd.DataFrame:
        rows = []
        years = sorted(self.e.anio.unique())
        for (ses, n), g in self.e.groupby(["session", "or_min"]):
            outcomes = {k: f(g).astype(bool) for k, (_, f) in EVENTS.items()}
            for cond in CONDITIONS:
                col = g[cond]
                if col.notna().sum() < self.MIN_N:
                    continue
                for val in col.dropna().unique():
                    m = (col == val).to_numpy()
                    if m.sum() < self.MIN_N or (~m).sum() < self.MIN_N:
                        continue
                    for ek, y in outcomes.items():
                        y = y.to_numpy()
                        k1, n1 = int(y[m].sum()), int(m.sum())
                        k2, n2 = int(y[~m].sum()), int((~m).sum())
                        base = y.mean()
                        p_c = k1 / n1
                        r = {"session": ses, "or_min": n, "evento": ek, "evento_txt": EVENTS[ek][0],
                             "condicion": cond, "valor": val, "n": n1, "p_cond": 100 * p_c,
                             "p_base": 100 * base, "lift_pp": 100 * (p_c - base),
                             "p_resto": 100 * k2 / n2, "p_value": _ztest(k1, n1, k2, n2)}
                        # Estabilidad IS / OOS y por año
                        for smp in ("IS", "OOS"):
                            s = (g["sample"] == smp).to_numpy()
                            mm, bb = m & s, s
                            r[f"lift_{smp}"] = (100 * (y[mm].mean() - y[bb].mean())
                                                if mm.sum() >= 15 else np.nan)
                            r[f"n_{smp}"] = int(mm.sum())
                        signs = []
                        for yr in years:
                            s = (g.anio == yr).to_numpy()
                            if (m & s).sum() >= 10:
                                signs.append(np.sign(y[m & s].mean() - y[s].mean()))
                        same = sum(1 for x in signs if x == np.sign(p_c - base))
                        r["anios_mismo_signo"] = f"{same}/{len(signs)}"
                        r["frac_anios"] = same / len(signs) if signs else np.nan
                        rows.append(r)
        f = pd.DataFrame(rows)
        f["q_value"] = _bh(f.p_value.to_numpy())
        f["estable"] = ((f.q_value < 0.05) & (f.lift_pp.abs() >= self.MIN_LIFT)
                        & (np.sign(f.lift_IS) == np.sign(f.lift_pp)) & (np.sign(f.lift_OOS) == np.sign(f.lift_pp))
                        & (f.frac_anios >= 0.75))
        return f.sort_values(["estable", "q_value"], ascending=[False, True])

    # -- 2. Repetición día a día ------------------------------------------------------------------
    def transitions(self) -> pd.DataFrame:
        rows = []
        for (ses, n), g in self.e.groupby(["session", "or_min"]):
            g = g.dropna(subset=["escenario_ayer"])
            base = g.scenario.value_counts(normalize=True)
            ct = pd.crosstab(g.escenario_ayer, g.scenario, normalize="index") * 100
            cnt = g.escenario_ayer.value_counts()
            for prev, row in ct.iterrows():
                for cur, v in row.items():
                    rows.append({"session": ses, "or_min": n, "ayer": prev, "hoy": SCEN_LABEL[cur],
                                 "n_ayer": int(cnt[prev]), "p": v, "p_base": 100 * base.get(cur, 0),
                                 "lift_pp": v - 100 * base.get(cur, 0)})
        return pd.DataFrame(rows)

    # -- 3. Tablas de escenarios por contexto ----------------------------------------------------
    def scenario_by(self, cond: str) -> pd.DataFrame:
        t = (self.e.groupby(["session", "or_min", cond]).scenario.value_counts(normalize=True)
             .mul(100).unstack().reindex(columns=SCEN_ORDER).fillna(0))
        t["n"] = self.e.groupby(["session", "or_min", cond]).size()
        return t.round(1)

    # -- 4. Gráficos ----------------------------------------------------------------------------
    def chart_scenarios(self, cond: str, fname: str, title: str):
        t = self.scenario_by(cond)
        fig, axes = plt.subplots(2, 2, figsize=(11, 6.4), sharex=True)
        for ax, ((ses, n), sub) in zip(axes.ravel(), t.groupby(level=[0, 1])):
            sub = sub.droplevel([0, 1])
            left = np.zeros(len(sub))
            for k, col in zip(SCEN_ORDER, style.SCEN_COLORS):
                ax.barh(range(len(sub)), sub[k], left=left, color=col, height=0.62,
                        edgecolor=style.SURFACE, linewidth=1.5, label=SCEN_LABEL[k])
                for i, (l, v) in enumerate(zip(left, sub[k])):
                    if v >= 8:
                        ax.text(l + v / 2, i, f"{v:.0f}", ha="center", va="center", fontsize=7.5, color="white")
                left += sub[k].to_numpy()
            ax.set_yticks(range(len(sub)), [f"{i} (n={int(c)})" for i, c in zip(sub.index, sub.n)])
            ax.set_title(f"{ses} · OR {n} min", loc="left", fontsize=10)
            ax.grid(axis="y", visible=False)
            ax.set_xlim(0, 100)
        for ax in axes[-1]:
            ax.set_xlabel("% de rupturas")
        h, l = axes[0, 0].get_legend_handles_labels()
        fig.legend(h, l, loc="lower center", ncol=3, fontsize=8, bbox_to_anchor=(0.5, -0.06))
        fig.suptitle(title, x=0.01, ha="left")
        fig.tight_layout()
        fig.savefig(os.path.join(self.out, fname), dpi=150, bbox_inches="tight")
        plt.close(fig)

    def chart_transitions(self, tr: pd.DataFrame):
        fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))
        for ax, ses in zip(axes, C.SESSIONS):
            t = tr[(tr.session == ses) & (tr.or_min == 15)].pivot(index="ayer", columns="hoy", values="lift_pp")
            order = [SCEN_LABEL[k] for k in SCEN_ORDER]
            t = t.reindex(index=[o for o in order if o in t.index], columns=order)
            lim = max(10, np.nanmax(np.abs(t.values)))
            ax.imshow(t.values, cmap=style.DIV, vmin=-lim, vmax=lim, aspect="auto")
            for (i, j), v in np.ndenumerate(t.values):
                if np.isfinite(v):
                    ax.text(j, i, f"{v:+.0f}", ha="center", va="center", fontsize=8, color=style.INK)
            short = ["Directa", "Retest+cont.", "Giro+cont.", "Giro rech.", "Rango"]
            ax.set_xticks(range(len(order)), short, rotation=30, ha="right")
            ax.set_yticks(range(len(t.index)), [short[order.index(i)] for i in t.index])
            ax.set_xlabel("Escenario HOY")
            ax.set_ylabel("Escenario AYER")
            ax.grid(False)
            ax.set_title(f"{ses} · OR 15 min: diferencia vs probabilidad base (pp)", loc="left", fontsize=10)
        fig.tight_layout()
        fig.savefig(os.path.join(self.out, "repeticion_escenarios.png"), dpi=150, bbox_inches="tight")
        plt.close(fig)

    # -- 5. Informe -----------------------------------------------------------------------------
    def run(self) -> dict:
        f = self.findings()
        tr = self.transitions()
        f.to_csv(os.path.join(self.out, "hallazgos.csv"), index=False, float_format="%.4f")
        tr.to_csv(os.path.join(self.out, "transiciones.csv"), index=False, float_format="%.2f")
        tabs = {c: self.scenario_by(c) for c in ["contexto_previo", "ruptura_vs_previo", "tendencia_diaria",
                                                  "ruptura_vs_diaria", "ruptura_vs_gap", "vs_londres"]}
        for c, t in tabs.items():
            t.to_csv(os.path.join(self.out, f"escenarios_por_{c}.csv"))
        self.chart_scenarios("contexto_previo", "escenarios_por_contexto_previo.png",
                             "Escenario tras la ruptura según el contexto previo a la apertura")
        self.chart_scenarios("ruptura_vs_previo", "escenarios_ruptura_vs_previo.png",
                             "Escenario según si la ruptura va a favor o en contra del movimiento previo")
        self.chart_transitions(tr)
        self.write_report(f, tr, tabs)
        return {"findings": f, "transitions": tr, "tables": tabs}

    def write_report(self, f: pd.DataFrame, tr: pd.DataFrame, tabs: dict):
        st = f[f.estable]
        base = (self.e.groupby(["session", "or_min"]).scenario.value_counts(normalize=True).mul(100)
                .unstack().reindex(columns=SCEN_ORDER).round(1).rename(columns=SCEN_LABEL))
        cols = ["session", "or_min", "evento_txt", "condicion", "valor", "n", "p_cond", "p_base", "lift_pp",
                "lift_IS", "lift_OOS", "anios_mismo_signo", "q_value"]
        rep = tr[(tr.n_ayer >= 60)].copy()
        rep = rep[rep.ayer == rep.hoy].sort_values("lift_pp", ascending=False)
        L = [f"# Agente analista — {C.SOURCE} ({C.START} → {C.END})\n",
             f"Rupturas analizadas: {len(self.e)}. Pruebas: {len(f)}. Hallazgos estables: {len(st)} "
             f"(q < 0,05 tras Benjamini-Hochberg, |efecto| ≥ {self.MIN_LIFT:g} pp, mismo signo en IS "
             f"y OOS y en ≥ 75 % de los años).\n",
             "## Probabilidad base de cada escenario (%)\n", base.reset_index().to_markdown(index=False, floatfmt=".1f"),
             "\n## Hallazgos estables (ordenados por significación)\n",
             st[cols].head(60).to_markdown(index=False, floatfmt=".1f") if len(st) else "Ninguno.",
             "\n## Repetición: P(mismo escenario hoy que ayer) frente a la base\n",
             rep[["session", "or_min", "hoy", "n_ayer", "p", "p_base", "lift_pp"]].to_markdown(index=False, floatfmt=".1f"),
             ]
        for c, t in tabs.items():
            L += [f"\n## Escenarios según `{c}` (%)\n",
                  t.rename(columns=SCEN_LABEL).reset_index().to_markdown(index=False, floatfmt=".1f")]
        with open(os.path.join(self.out, "ANALISTA.md"), "w") as fh:
            fh.write("\n".join(L) + "\n")


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default=C.SOURCE)
    a = ap.parse_args()
    C.use_source(a.source)
    con = db.connect(db.db_light_path())
    ev = pd.read_sql("SELECT * FROM events", con)
    gaps = pd.read_sql("SELECT * FROM gaps", con)
    out = os.path.join(db.results_dir(), "analyst")
    res = AnalystAgent(ev, gaps, out).run()
    f = res["findings"]
    print(f"[analista] {len(f)} pruebas, {int(f.estable.sum())} hallazgos estables -> {out}")


if __name__ == "__main__":
    main()
