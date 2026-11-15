"""Descarga y caché de velas de 1 minuto de Dukascopy.

Cada día se guarda como el fichero .bi5 original en data/dukascopy/<INSTR>/YYYY-MM-DD.bi5.
Formato (big-endian, 24 bytes por vela): segundos desde 00:00 UTC, open, close, low, high
(enteros = precio * divisor) y volumen (float32). Las velas sin volumen son relleno y se descartan.

Instrumento por defecto: USATECHIDXUSD (CFD del Nasdaq 100, proxy del futuro NQ).
"""
from __future__ import annotations

import datetime as dt
import lzma
import struct
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "data" / "dukascopy"
URL = "https://datafeed.dukascopy.com/datafeed/{inst}/{y:04d}/{m:02d}/{d:02d}/BID_candles_min_1.bi5"
DIVISOR = {"USATECHIDXUSD": 1000.0}
PAUSE = 1.0  # segundos entre peticiones: Dukascopy responde 429 si se descarga en paralelo


def _fetch(inst: str, day: dt.date) -> Path | None:
    path = CACHE / inst / f"{day.isoformat()}.bi5"
    if path.exists():
        return path
    if day >= dt.date.today():
        return None
    path.parent.mkdir(parents=True, exist_ok=True)
    url = URL.format(inst=inst, y=day.year, m=day.month - 1, d=day.day)  # mes 0-indexado
    for attempt in range(8):
        time.sleep(PAUSE)
        try:
            with urllib.request.urlopen(url, timeout=30) as r:
                data = r.read()
            path.write_bytes(data)
            return path
        except urllib.error.HTTPError as e:
            if e.code == 404:
                path.write_bytes(b"")  # día sin datos: se cachea vacío
                return path
            time.sleep(min(15 * 2 ** attempt, 240))  # 429 u otro error: espera progresiva
        except Exception:
            time.sleep(min(15 * 2 ** attempt, 240))  # Dukascopy corta la conexión al limitar
    return None


def _parse(path: Path, day: dt.date, divisor: float) -> pd.DataFrame | None:
    raw = path.read_bytes()
    if not raw:
        return None
    buf = lzma.decompress(raw)
    rec = np.frombuffer(buf, dtype=np.dtype([("t", ">i4"), ("o", ">i4"), ("c", ">i4"),
                                             ("l", ">i4"), ("h", ">i4"), ("v", ">f4")]))
    rec = rec[rec["v"] > 0]
    if len(rec) == 0:
        return None
    base = pd.Timestamp(day, tz="UTC")
    idx = base + pd.to_timedelta(rec["t"].astype(np.int64), unit="s")
    return pd.DataFrame({"open": rec["o"] / divisor, "high": rec["h"] / divisor,
                         "low": rec["l"] / divisor, "close": rec["c"] / divisor,
                         "volume": rec["v"].astype(float)}, index=idx)


def load_minutes(start: str, end: str, inst: str = "USATECHIDXUSD", workers: int = 1) -> pd.DataFrame:
    """Velas de 1 minuto entre start y end (fechas UTC, inclusive), índice en hora de Nueva York."""
    days = [d.date() for d in pd.date_range(start, end, freq="D") if d.weekday() != 5]
    with ThreadPoolExecutor(workers) as ex:
        paths = list(ex.map(lambda d: _fetch(inst, d), days))
    missing = [d for d, p in zip(days, paths) if p is None]
    if missing:
        print(f"AVISO: {len(missing)} días no se pudieron descargar (p. ej. {missing[:3]})")
    frames = [f for d, p in zip(days, paths) if p is not None
              for f in [_parse(p, d, DIVISOR.get(inst, 1000.0))] if f is not None]
    df = pd.concat(frames).sort_index()
    df = df[~df.index.duplicated()]
    df.index = df.index.tz_convert("America/New_York")
    return df


if __name__ == "__main__":
    m = load_minutes("2026-09-01", "2026-09-03")
    print(m.between_time("09:28", "09:33"))
