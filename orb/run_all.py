"""
run_all.py — Ejecuta todo el flujo con una fuente de datos:

  1. Descarga (Dukascopy, con caché) y base de datos: velas, eventos ORB, gaps, rejilla de reglas
  2. Agente analista: probabilidades condicionadas, estabilidad, repetición
  3. Agente de estrategia: Fibonacci cierre NY -> apertura NY, patrones, gráficos
  3b. Agente de pronóstico: probabilidades en el momento de cada apertura (backtesting)
  4. Archivos del dashboard

Uso:  python3 orb/run_all.py                 (dukascopy, 2022 -> hoy)
      python3 orb/run_all.py --source binance
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))


def step(name: str, args: list[str]) -> None:
    t0 = time.time()
    print(f"\n=== {name} ===", flush=True)
    subprocess.run([sys.executable, *args], check=True, cwd=os.path.dirname(HERE))
    print(f"=== {name}: {time.time() - t0:.0f} s ===", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default="dukascopy")
    a = ap.parse_args()
    s = ["--source", a.source]
    step("Base de datos y estudio ORB", [os.path.join(HERE, "run_study.py"), *s])
    step("Agente analista", [os.path.join(HERE, "agents", "analyst.py"), *s])
    step("Agente de estrategia", [os.path.join(HERE, "agents", "strategy.py"), *s])
    step("Agente de pronóstico (walk-forward)", [os.path.join(HERE, "agents", "forecaster.py"), *s])
    step("Datos del dashboard", [os.path.join(HERE, "dashboard", "build_data.py"), *s])


if __name__ == "__main__":
    main()
