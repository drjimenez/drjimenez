"""
build_data.py — Prepara los archivos CSV del dashboard a partir de la base de datos ligera.

Cada archivo trae las probabilidades YA calculadas para cada combinación de filtros, de modo que
cada número del dashboard sale de una celda (sin cálculos en el navegador):

  escenarios.csv   árbol de escenarios tras la ruptura del rango de apertura
                   clave = sesion|or_min|simbolo|ruptura|contexto_previo|tendencia_diaria|anio|umbral
  gap_niveles.csv  probabilidad de tocar cada nivel Fibonacci del gap cierre NY → apertura NY
                   clave = simbolo|gap_dir|gap_size|gap_vs_tendencia|anio
  hallazgos.csv    hallazgos estables del agente analista
  patrones.csv     mejor variante de cada patrón del agente de estrategia (IS y OOS)
  aperturas.csv    registro de aperturas con las probabilidades conocidas en cada momento (walk-forward)
  calibracion.csv  probabilidad pronosticada frente a frecuencia real; brier.csv: error del pronóstico

Uso: python3 orb/dashboard/build_data.py [--source dukascopy]
"""
from __future__ import annotations

import itertools
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import config as C  # noqa: E402
import database as db  # noqa: E402
from agents.analyst import SCEN_LABEL, build_conditions  # noqa: E402

ALL = "todos"
SCEN = list(SCEN_LABEL)
THRESH = {"1.272": "scenario_1272", "1.618": "scenario_1618", "2.0": "scenario_20"}


def _combos(df: pd.DataFrame, dims: list[str]):
    """Itera todas las combinaciones de valores (más 'todos') de las dimensiones."""
    vals = [[ALL] + sorted(df[d].dropna().astype(str).unique().tolist()) for d in dims]
    for combo in itertools.product(*vals):
        m = np.ones(len(df), bool)
        for d, v in zip(dims, combo):
            if v != ALL:
                m &= (df[d].astype(str) == v).to_numpy()
        yield combo, m


def scenarios_cube(ev: pd.DataFrame, gaps: pd.DataFrame) -> pd.DataFrame:
    e = build_conditions(ev, gaps)
    e["anio"] = e.date.str[:4]
    e["or_min"] = e.or_min.astype(str)
    e = e[e.contexto_previo != "n/d"]
    dims = ["symbol", "ruptura", "contexto_previo", "tendencia_diaria", "anio"]
    rows = []
    for (ses, n), g in e.groupby(["session", "or_min"]):
        g = g.reset_index(drop=True)
        for combo, m in _combos(g, dims):
            k = int(m.sum())
            if k < 15:
                continue
            sub = g[m]
            for th, col in THRESH.items():
                sc = sub[col].value_counts(normalize=True)
                r = {"clave": "|".join([ses, n, *combo, th]), "sesion": ses, "or_min": n,
                     **dict(zip(["simbolo", "ruptura", "contexto_previo", "tendencia_diaria", "anio"], combo)),
                     "umbral": th, "n": k}
                for s in SCEN:
                    r[f"p_{s}"] = round(100 * sc.get(s, 0.0), 1)
                ret = 100 - r["p_directa"]
                r["p_vuelve"] = round(ret, 1)
                # condicionadas a que vuelva al nivel roto
                for s in ["retest_continua", "giro_continua", "giro_rechazo", "rango"]:
                    r[f"c_{s}"] = round(100 * r[f"p_{s}"] / ret, 1) if ret > 0 else np.nan
                r["c_toca_opuesto"] = (round(100 * (r["p_giro_continua"] + r["p_giro_rechazo"]) / ret, 1)
                                       if ret > 0 else np.nan)
                r["p_ret_50"] = round(100 * sub.t_ret_0500.notna().mean(), 1)
                r["p_toca_opuesto"] = round(100 * sub.t_ret_1000.notna().mean(), 1)
                r["p_ext_1618"] = round(100 * sub.t_ext_0618.notna().mean(), 1)
                r["mediana_min_retest"] = sub.min_to_retest.median()
                rows.append(r)
    return pd.DataFrame(rows)


def gap_cube(gaps: pd.DataFrame) -> pd.DataFrame:
    g = gaps[gaps.gap_dir != "plano"].copy()
    s = np.sign(g.gap)
    g["gap_vs_tendencia"] = np.select(
        [((s > 0) & (g.daily_trend == "alcista")) | ((s < 0) & (g.daily_trend == "bajista")),
         ((s > 0) & (g.daily_trend == "bajista")) | ((s < 0) & (g.daily_trend == "alcista"))],
        ["a favor", "en contra"], "lateral")
    g["anio"] = g.date.str[:4]
    dims = ["symbol", "gap_dir", "gap_size", "gap_vs_tendencia", "anio"]
    rows = []
    for combo, m in _combos(g.reset_index(drop=True), dims):
        k = int(m.sum())
        if k < 15:
            continue
        sub = g.reset_index(drop=True)[m]
        r = {"clave": "|".join(combo), **dict(zip(["simbolo", "gap_dir", "gap_size", "gap_vs_tendencia", "anio"], combo)),
             "n": k, "gap_medio_pb": round(sub.gap_bp.abs().median(), 1)}
        for x in reversed(C.GAP_AWAY_LEVELS):
            r[f"aleja_{x:g}"] = round(100 * sub[f"t_away_{db_lvl(x)}"].notna().mean(), 1)
        for x in C.GAP_FILL_LEVELS:
            r[f"ret_{x:g}"] = round(100 * sub[f"t_fill_{db_lvl(x)}"].notna().mean(), 1)
        f, a = sub.t_fill_0500, sub.t_away_0272
        r["ret50_antes_aleja0272"] = round(100 * (f.notna() & (a.isna() | (f < a))).mean(), 1)
        rows.append(r)
    return pd.DataFrame(rows)


def db_lvl(x: float) -> str:
    return f"{int(round(x * 1000)):04d}"


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default=C.SOURCE)
    a = ap.parse_args()
    C.use_source(a.source)
    out = os.path.join(db.results_dir(), "dashboard")
    os.makedirs(out, exist_ok=True)
    con = db.connect(db.db_light_path())
    ev = pd.read_sql("SELECT * FROM events", con)
    gaps = pd.read_sql("SELECT * FROM gaps", con)
    sc = scenarios_cube(ev, gaps)
    sc.to_csv(os.path.join(out, "escenarios.csv"), index=False)
    gc = gap_cube(gaps)
    gc.to_csv(os.path.join(out, "gap_niveles.csv"), index=False)

    res = db.results_dir()
    f = pd.read_csv(os.path.join(res, "analyst", "hallazgos.csv"))
    f = f[f.estable].sort_values("q_value").head(40)
    f = f[["session", "or_min", "evento_txt", "condicion", "valor", "n", "p_cond", "p_base", "lift_pp",
           "lift_IS", "lift_OOS", "anios_mismo_signo", "q_value"]].round(2)
    f.insert(0, "id", range(1, len(f) + 1))
    f.to_csv(os.path.join(out, "hallazgos.csv"), index=False)

    p = pd.read_csv(os.path.join(res, "strategy", "patrones_resultados.csv"))
    p = p[p.IS_n >= 40]
    best = p.sort_values("IS_exp_R", ascending=False).groupby("pattern").head(2).sort_values(["pattern", "IS_exp_R"],
                                                                                              ascending=[True, False])
    best = best[["pattern", "pattern_txt", "variant", "filtro", "IS_n", "IS_win", "IS_exp_R", "OOS_n", "OOS_win",
                 "OOS_exp_R", "anios_positivos"]].round(3)
    best.insert(0, "id", [f"{a}-{i}" for i, a in enumerate(best.pattern)])
    best.to_csv(os.path.join(out, "patrones.csv"), index=False)
    # Registro de aperturas del agente de pronóstico (walk-forward)
    fc = os.path.join(res, "forecast")
    ap = pd.read_csv(os.path.join(fc, "aperturas.csv"))
    ap.drop(columns=["calentamiento"]).to_csv(os.path.join(out, "aperturas.csv"), index=False)
    pd.read_csv(os.path.join(fc, "calibracion.csv")).to_csv(os.path.join(out, "calibracion.csv"), index=False)
    pd.read_csv(os.path.join(fc, "brier.csv")).to_csv(os.path.join(out, "brier.csv"), index=False)
    for name in ["escenarios", "gap_niveles", "hallazgos", "patrones", "aperturas", "calibracion", "brier"]:
        size = os.path.getsize(os.path.join(out, f"{name}.csv"))
        print(f"[dashboard] {name}.csv {size / 1024:.0f} KB")


if __name__ == "__main__":
    main()
