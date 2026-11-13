"""
forecaster.py — Agente de pronóstico: probabilidad de cada condición en el momento de cada apertura,
calculada SOLO con el historial anterior (walk-forward, sin mirar el futuro). Sirve de backtesting:
cada fila dice qué probabilidades se conocían en ese momento y qué pasó después.

Etapas de cada apertura (Londres 08:00, Nueva York 09:30, hora local):
  1. Apertura          se conoce el contexto previo (alza / baja / rango) y la tendencia diaria
                       -> P(la primera ruptura es alcista)
  2. Cierre del rango  se conoce el tamaño del rango frente al rango medio diario (tercil calculado
                       con los días anteriores)
  3. Ruptura           se conoce la dirección y si va a favor o en contra del contexto previo
                       -> P(vuelve al nivel roto), P(toca el 50 %), P(toca el extremo opuesto),
                          P(llega a 1.618), P(vuelve y continúa), P(rompe el otro extremo y continúa)

Cada probabilidad es una frecuencia histórica condicionada con suavizado jerárquico:
    p = (k + M · p_padre) / (n + M)
con el padre = la misma pregunta con una condición menos. Se usan todos los días ANTERIORES de
ambos índices (nunca el mismo día).

Salidas en results/<fuente>/forecast/: aperturas.csv (una fila por apertura), calibracion.csv,
PRONOSTICO.md y calibracion.png.
"""
from __future__ import annotations

import bisect
import os
import sys
from collections import defaultdict

import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config as C  # noqa: E402
import database as db  # noqa: E402
from agents import style  # noqa: E402

M = 20                 # fuerza del suavizado hacia la condición padre
# Condiciones usadas. El agente analista encontró que el tamaño del rango es la condición estable;
# el contexto previo y la relación ruptura/contexto apenas cambian las probabilidades.
OPEN_DEPTH = 2         # 1 = sesión · 2 = + contexto previo · 3 = + tendencia diaria
BRK_DEPTH = 2          # 1 = sesión · 2 = + tamaño del rango · 3 = + ruptura a favor/en contra del contexto
WARMUP_DAYS = 120      # días iniciales que no cuentan en la calibración

EVENTS = {
    "vuelve": "Vuelve al nivel roto",
    "toca50": "Toca el 50 % del rango",
    "opuesto": "Toca el extremo opuesto",
    "ext1618": "Llega a la extensión 1.618",
    "continua": "Vuelve y continúa en la 1.ª dirección",
    "giro": "Rompe el otro extremo y continúa",
}
SCEN_TXT = {
    "directa": "Continúa sin volver", "retest_continua": "Vuelve y continúa",
    "giro_continua": "Rompe el otro extremo y continúa", "giro_rechazo": "Rechazado en el otro extremo",
    "rango": "Se queda en rango",
}


def outcomes(e: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame({
        "up": e.break_dir == "up",
        "vuelve": e.retest.astype(float) > 0,
        "toca50": e.t_ret_0500.notna(),
        "opuesto": e.t_ret_1000.notna(),
        "ext1618": e.t_ext_0618.notna(),
        "continua": e.scenario == "retest_continua",
        "giro": e.scenario == "giro_continua",
    }, index=e.index)


class Counter:
    """Frecuencias acumuladas jerárquicas: claves de más general a más concreta."""

    def __init__(self):
        self.k = defaultdict(float)
        self.n = defaultdict(float)

    def prob(self, keys: list[tuple], ev: str, prior: float) -> tuple[float, int]:
        p, n_last = prior, 0
        for key in keys:
            n = self.n[key]
            k = self.k[(key, ev)]
            p = (k + M * p) / (n + M)
            n_last = int(n)
        return p, n_last

    def add(self, keys: list[tuple], ev: str, y: bool):
        for key in keys:
            self.k[(key, ev)] += float(y)

    def add_n(self, keys: list[tuple]):
        for key in keys:
            self.n[key] += 1


class ForecastAgent:
    def __init__(self, ev: pd.DataFrame, out_dir: str):
        e = ev[ev.break_dir != "none"].copy()
        e = e[(e.pre_trend != "n/d")].sort_values(["date", "session", "or_min", "symbol"]).reset_index(drop=True)
        self.e = e
        self.y = outcomes(e)
        self.out = out_dir
        os.makedirs(out_dir, exist_ok=True)

    def run(self) -> pd.DataFrame:
        e, Y = self.e, self.y
        cnt_open, cnt_brk = Counter(), Counter()
        sizes = defaultdict(list)            # (session, or_min) -> or_vs_adr anteriores ordenados
        rows = []
        for d, g in e.groupby("date", sort=True):
            # 1) pronóstico con lo anterior
            for i, r in g.iterrows():
                so = (r.session, int(r.or_min))
                hist = sizes[so]
                if np.isfinite(r.or_vs_adr) and len(hist) >= 30:
                    c1, c2 = hist[len(hist) // 3], hist[2 * len(hist) // 3]
                    ter = "pequeño" if r.or_vs_adr < c1 else "medio" if r.or_vs_adr < c2 else "grande"
                else:
                    ter = "n/d"
                rel = ("a favor" if (r.break_dir == "up" and r.pre_trend == "alza") or (r.break_dir == "down" and r.pre_trend == "baja")
                       else "en contra" if (r.break_dir == "up" and r.pre_trend == "baja") or (r.break_dir == "down" and r.pre_trend == "alza")
                       else "sin tendencia")
                k_open = [("o",) + so, ("o",) + so + (r.pre_trend,), ("o",) + so + (r.pre_trend, r.daily_trend)][:OPEN_DEPTH]
                k_brk = [("b",) + so, ("b",) + so + (ter,), ("b",) + so + (ter, rel)][:BRK_DEPTH]
                p_up, n_open = cnt_open.prob(k_open, "up", 0.5)
                row = {"id": r.event_id, "fecha": d, "mes": d[:7], "sesion": r.session, "or_min": int(r.or_min),
                       "simbolo": r.symbol, "contexto_previo": r.pre_trend, "tendencia_diaria": r.daily_trend,
                       "tam_rango": ter, "ruptura": "alcista" if r.break_dir == "up" else "bajista",
                       "hora_ruptura": pd.Timestamp(r.break_time_utc).tz_localize("UTC").tz_convert(
                           C.SESSIONS[r.session]["tz"]).strftime("%H:%M"),
                       "ruptura_vs_previo": rel,
                       "p_alcista": round(100 * p_up, 1), "n_hist": int(cnt_brk.n[k_brk[0]])}
                for ev_ in EVENTS:
                    p, _ = cnt_brk.prob(k_brk, ev_, 0.5)
                    row[f"p_{ev_}"] = round(100 * p, 1)
                    row[f"r_{ev_}"] = int(Y.at[i, ev_])
                row["r_alcista"] = int(Y.at[i, "up"])
                row["escenario_real"] = SCEN_TXT.get(r.scenario, r.scenario)
                rows.append(row)
            # 2) se añade el día al historial (después de pronosticar todo el día)
            for i, r in g.iterrows():
                so = (r.session, int(r.or_min))
                row = next(x for x in rows[-len(g):] if x["id"] == r.event_id)
                ter, rel = row["tam_rango"], row["ruptura_vs_previo"]
                k_open = [("o",) + so, ("o",) + so + (r.pre_trend,), ("o",) + so + (r.pre_trend, r.daily_trend)][:OPEN_DEPTH]
                k_brk = [("b",) + so, ("b",) + so + (ter,), ("b",) + so + (ter, rel)][:BRK_DEPTH]
                cnt_open.add_n(k_open)
                cnt_open.add(k_open, "up", bool(Y.at[i, "up"]))
                cnt_brk.add_n(k_brk)
                for ev_ in EVENTS:
                    cnt_brk.add(k_brk, ev_, bool(Y.at[i, ev_]))
                if np.isfinite(r.or_vs_adr):
                    bisect.insort(sizes[so], float(r.or_vs_adr))
        df = pd.DataFrame(rows)
        first = pd.Timestamp(df.fecha.min())
        df["calentamiento"] = (pd.to_datetime(df.fecha) - first).dt.days < WARMUP_DAYS
        return df

    # -- Calibración y comparación con la probabilidad base ---------------------------------------
    def calibration(self, df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
        x = df[~df.calentamiento]
        rows, summ = [], []
        bins = np.arange(0, 101, 10)
        for ev_, txt in {"alcista": "Primera ruptura alcista", **EVENTS}.items():
            p, y = x[f"p_{ev_}"] / 100, x[f"r_{ev_}"]
            b = pd.cut(x[f"p_{ev_}"], bins, right=False, labels=[f"{a}-{a + 10}" for a in bins[:-1]])
            for (ses, lab), g in pd.DataFrame({"s": x.sesion, "b": b, "p": p, "y": y}).groupby(["s", "b"], observed=True):
                if len(g) >= 20:
                    rows.append({"evento": ev_, "evento_txt": txt, "sesion": ses, "tramo": lab, "n": len(g),
                                 "prob_media": round(100 * g.p.mean(), 1), "frecuencia_real": round(100 * g.y.mean(), 1)})
            # Brier del modelo frente a la frecuencia base acumulada (sin condiciones)
            base = y.groupby([x.sesion, x.or_min]).transform(lambda s: s.shift(1).expanding().mean()).fillna(0.5)
            bm, bb = ((p - y) ** 2).mean(), ((base - y) ** 2).mean()
            summ.append({"evento": ev_, "evento_txt": txt, "n": len(x), "brier_modelo": round(bm, 4),
                         "brier_base": round(bb, 4), "mejora_pct": round(100 * (1 - bm / bb), 2),
                         "frecuencia_real": round(100 * y.mean(), 1)})
        cal = pd.DataFrame(rows)
        cal.insert(0, "clave", cal.evento + "|" + cal.sesion + "|" + cal.tramo.astype(str))
        return cal, pd.DataFrame(summ)

    def chart(self, cal: pd.DataFrame):
        evs = ["alcista"] + list(EVENTS)
        fig, axes = plt.subplots(2, 4, figsize=(13, 6.4), sharex=True, sharey=True)
        for ax, ev_ in zip(axes.ravel(), evs):
            for ses, col in [("London", style.BLUE), ("NewYork", style.ORANGE)]:
                s = cal[(cal.evento == ev_) & (cal.sesion == ses)]
                ax.plot(s.prob_media, s.frecuencia_real, marker="o", ms=4, color=col, lw=1.5, label=ses)
            ax.plot([0, 100], [0, 100], color=style.GRID, lw=1, ls="--", zorder=0)
            ax.set_title(("Primera ruptura alcista" if ev_ == "alcista" else EVENTS[ev_]), loc="left", fontsize=9)
        axes.ravel()[-1].set_visible(False)
        axes[0, 0].legend(fontsize=8)
        for ax in axes[-1]:
            ax.set_xlabel("Probabilidad pronosticada (%)")
        for ax in axes[:, 0]:
            ax.set_ylabel("Frecuencia real (%)")
        fig.suptitle("Calibración del pronóstico walk-forward (sobre la diagonal = bien calibrado)", x=0.01, ha="left")
        fig.tight_layout()
        fig.savefig(os.path.join(self.out, "calibracion.png"), dpi=150, bbox_inches="tight")
        plt.close(fig)


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default=C.SOURCE)
    a = ap.parse_args()
    C.use_source(a.source)
    con = db.connect(db.db_light_path())
    ev = pd.read_sql("SELECT * FROM events", con)
    out = os.path.join(db.results_dir(), "forecast")
    ag = ForecastAgent(ev, out)
    df = ag.run()
    cal, summ = ag.calibration(df)
    df.to_csv(os.path.join(out, "aperturas.csv"), index=False)
    cal.to_csv(os.path.join(out, "calibracion.csv"), index=False)
    summ.to_csv(os.path.join(out, "brier.csv"), index=False)
    ag.chart(cal)
    with open(os.path.join(out, "PRONOSTICO.md"), "w") as fh:
        fh.write(f"# Agente de pronóstico (walk-forward) — {C.SOURCE}\n\n"
                 f"Aperturas con ruptura: {len(df)}. Calibración sin los primeros {WARMUP_DAYS} días.\n\n"
                 "Brier: error cuadrático medio de la probabilidad (menor es mejor). `mejora_pct` compara "
                 "el modelo condicionado con la frecuencia base acumulada sin condiciones.\n\n"
                 + summ.to_markdown(index=False) + "\n")
    print(f"[pronostico] {len(df)} aperturas -> {out}")
    print(summ.to_string(index=False))


if __name__ == "__main__":
    main()
