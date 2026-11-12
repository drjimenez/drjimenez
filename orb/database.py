"""
database.py — Carga de velas de 1 minuto y base de datos SQLite del estudio ORB.

Fuentes de datos:
  * Binance (por defecto): perpetuos QQQUSDT / SPYUSDT, descarga y caché en data/.
  * CSV propio (MT5, TradingView, NinjaTrader...): import_csv(), con la zona horaria del archivo.

Tablas:
  bars_1m         velas de 1 minuto en UTC
  events          una fila por (símbolo, día, sesión, minutos de OR) con todas las mediciones
  strategy_grid   resultados de cada regla (entrada/stop/objetivo) por muestra IS/OOS
  trades          operaciones de las reglas seleccionadas
"""
from __future__ import annotations

import os
import sqlite3
import sys

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "backtest"))
import data_loader as dl  # noqa: E402  (descargador ya existente del repo)

import config as C  # noqa: E402



def db_path() -> str:
    """Base de datos completa con velas de 1 minuto (no versionada)."""
    return os.path.join(HERE, "data", f"orb_{C.SOURCE}.sqlite")


def db_light_path() -> str:
    """Base de datos de eventos sin velas (versionada en results/<fuente>/)."""
    return os.path.join(results_dir(), "orb_study.sqlite")


def results_dir() -> str:
    return os.path.join(HERE, "results", C.SOURCE)


def load_bars(symbol: str) -> pd.DataFrame:
    """Velas de 1 minuto en UTC de la fuente activa (C.SOURCE)."""
    if C.SOURCE == "dukascopy":
        # Serie CFD de Dukascopy: años/meses cerrados desde HistData (mismos precios, archivos
        # grandes y rápidos de bajar) y los últimos días desde el datafeed de Dukascopy.
        import histdata
        return histdata.load(symbol, C.START, C.END)
    return load_binance(symbol)


def load_binance(symbol: str) -> pd.DataFrame:
    dl.UNIVERSE.setdefault(symbol, ("futures/um", "Indices"))
    return dl.load_symbol(symbol, "1m", C.START, C.END)


def import_csv(path: str, tz: str = "UTC") -> pd.DataFrame:
    """
    Lee un CSV de velas de 1 minuto y lo devuelve indexado en UTC.

    Formatos reconocidos:
      * MT5 (Exportar barras):  <DATE> <TIME> <OPEN> <HIGH> <LOW> <CLOSE> <TICKVOL> ...
        (separado por tabuladores; fechas 2026.05.01, hora del servidor del bróker -> pasa tz,
        p. ej. 'Etc/GMT-2' o 'Europe/Athens' para servidores en UTC+2/+3 con DST)
      * TradingView (Exportar datos del gráfico): time,open,high,low,close,Volume
        (time en segundos Unix -> UTC, o ISO con zona)
      * Genérico: columnas datetime/date+time, open, high, low, close[, volume]
    """
    df = pd.read_csv(path, sep=None, engine="python")
    df.columns = [c.strip("<>").strip().lower() for c in df.columns]
    if "date" in df.columns and "time" in df.columns:
        ts = pd.to_datetime(df["date"].astype(str).str.replace(".", "-") + " " + df["time"].astype(str))
        ts = ts.dt.tz_localize(tz, ambiguous="NaT", nonexistent="shift_forward")
    else:
        col = next(c for c in ("time", "datetime", "timestamp", "date") if c in df.columns)
        s = df[col]
        if pd.api.types.is_numeric_dtype(s):
            ts = pd.to_datetime(s.astype("int64"), unit="s" if s.max() < 1e11 else "ms", utc=True)
        else:
            ts = pd.to_datetime(s, utc=False)
            ts = ts.dt.tz_localize(tz) if ts.dt.tz is None else ts
    vol = next((c for c in ("volume", "tickvol", "vol") if c in df.columns), None)
    out = pd.DataFrame({
        "open": df["open"].astype(float), "high": df["high"].astype(float),
        "low": df["low"].astype(float), "close": df["close"].astype(float),
        "volume": df[vol].astype(float) if vol else 0.0,
    })
    out.index = pd.DatetimeIndex(ts).tz_convert("UTC")
    out.index.name = "time"
    out = out[out.index.notna()]
    return out[~out.index.duplicated()].sort_index()


def connect(path: str | None = None) -> sqlite3.Connection:
    path = path or db_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    return sqlite3.connect(path)


def write_bars(con: sqlite3.Connection, symbol: str, bars: pd.DataFrame) -> None:
    con.execute("""CREATE TABLE IF NOT EXISTS bars_1m (
        symbol TEXT, ts_utc TEXT, open REAL, high REAL, low REAL, close REAL, volume REAL,
        PRIMARY KEY (symbol, ts_utc))""")
    con.execute("DELETE FROM bars_1m WHERE symbol = ?", (symbol,))
    df = bars[["open", "high", "low", "close", "volume"]].copy()
    df.insert(0, "ts_utc", df.index.strftime("%Y-%m-%d %H:%M"))
    df.insert(0, "symbol", symbol)
    con.executemany("INSERT INTO bars_1m VALUES (?,?,?,?,?,?,?)", df.itertuples(index=False))
    con.commit()


def write_table(con: sqlite3.Connection, name: str, df: pd.DataFrame) -> None:
    df.to_sql(name, con, if_exists="replace", index=False)


VIEWS = {
    # Resumen de dirección de ruptura y retrocesos por sesión / rango
    "v_breakout_summary": """
        SELECT session, or_min, symbol, COUNT(*) AS days,
               ROUND(100.0*AVG(break_dir='up'),1)   AS pct_up,
               ROUND(100.0*AVG(break_dir='down'),1) AS pct_down,
               ROUND(100.0*AVG(break_dir='none'),1) AS pct_none,
               ROUND(100.0*AVG(CASE WHEN break_dir!='none' THEN retest END),1) AS pct_retest,
               ROUND(100.0*AVG(CASE WHEN break_dir!='none' THEN t_ret_0500 IS NOT NULL END),1) AS pct_ret_50,
               ROUND(100.0*AVG(CASE WHEN break_dir!='none' THEN opposite_break END),1) AS pct_failed
        FROM events GROUP BY session, or_min, symbol""",
    # Ejemplo de consulta de probabilidad: ¿llega a 1.618 antes de retroceder al 50%?
    "v_ext1618_before_ret50": """
        SELECT session, or_min, COUNT(*) AS breaks,
               ROUND(100.0*AVG(t_ext_0618 IS NOT NULL AND (t_ret_0500 IS NULL OR t_ext_0618 < t_ret_0500)),1)
                 AS pct_ext1618_before_ret50
        FROM events WHERE break_dir != 'none' GROUP BY session, or_min""",
}


def write_views(con: sqlite3.Connection) -> None:
    for name, sql in VIEWS.items():
        con.execute(f"DROP VIEW IF EXISTS {name}")
        con.execute(f"CREATE VIEW {name} AS {sql}")
    con.commit()
