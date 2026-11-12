"""
dukascopy.py — Descarga velas de 1 minuto (BID) del datafeed público de Dukascopy.

Instrumentos:  USATECHIDXUSD (CFD Nasdaq 100)   USA500IDXUSD (CFD S&P 500)
Formato:       un archivo LZMA por día UTC con 1440 registros de 24 bytes big-endian:
               segundos desde 00:00 UTC (int32), open, close, low, high (int32, precio × 1000),
               volumen (float32).
URL:           /datafeed/{INSTR}/{AAAA}/{MM-1}/{DD}/BID_candles_min_1.bi5   (el mes empieza en 00)

El servidor limita la velocidad (HTTP 429), así que se descarga con pocas conexiones, pausas y
reintentos con espera creciente. Los archivos se guardan en orb/data/raw/dukascopy/ (caché): si
se interrumpe, al volver a ejecutar sólo se piden los días que faltan.

Uso:  python3 orb/dukascopy.py 2022-01-01 2026-11-11
"""
from __future__ import annotations

import lzma
import os
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, timedelta

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "data", "raw", "dukascopy")
CACHE = os.path.join(HERE, "data", "cache")
URL = "https://datafeed.dukascopy.com/datafeed/{i}/{y}/{m:02d}/{d:02d}/BID_candles_min_1.bi5"
INSTRUMENTS = {"NAS100": "USATECHIDXUSD", "US500": "USA500IDXUSD"}
SCALE = 1000.0
WORKERS = 1
PAUSE = 2.0   # segundos entre peticiones (el servidor penaliza las ráfagas)


def _path(instr: str, d: date) -> str:
    return os.path.join(RAW, instr, f"{d.isoformat()}.bi5")


def _fetch(instr: str, d: date, retries: int = 8) -> str:
    dest = _path(instr, d)
    if os.path.exists(dest):
        return "cached"
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    url = URL.format(i=instr, y=d.year, m=d.month - 1, d=d.day)
    wait = 3.0
    for _ in range(retries):
        try:
            with urllib.request.urlopen(url, timeout=90) as r:
                data = r.read()
            with open(dest + ".tmp", "wb") as f:
                f.write(data)
            os.replace(dest + ".tmp", dest)       # archivo vacío = día sin cotización
            time.sleep(PAUSE)
            return "ok"
        except urllib.error.HTTPError as ex:
            if ex.code == 404:
                open(dest, "wb").close()
                return "404"
        except Exception:
            pass
        time.sleep(wait)
        wait = min(wait * 2, 30)
    return "fail"


def days(start: str, end: str):
    d, e = date.fromisoformat(start), date.fromisoformat(end)
    while d <= e:
        if d.weekday() < 5:           # sólo días laborables (las sesiones estudiadas)
            yield d
        d += timedelta(days=1)


def download(start: str, end: str, symbols=None) -> None:
    jobs = [(INSTRUMENTS[s], d) for s in (symbols or INSTRUMENTS) for d in days(start, end)
            if not os.path.exists(_path(INSTRUMENTS[s], d))]
    print(f"[dukascopy] {len(jobs)} archivos pendientes", flush=True)
    done, fails, t0 = 0, [], time.time()
    with ThreadPoolExecutor(WORKERS) as ex:
        futs = {ex.submit(_fetch, i, d): (i, d) for i, d in jobs}
        for f in as_completed(futs):
            done += 1
            if f.result() == "fail":
                fails.append(futs[f])
            if done % 25 == 0 or done == len(jobs):
                rate = done / max(time.time() - t0, 1)
                print(f"[dukascopy] {done}/{len(jobs)}  {rate:.2f} arch/s  fallos={len(fails)}", flush=True)
    if fails:
        print(f"[dukascopy] fallidos (vuelve a ejecutar para reintentar): {fails[:10]}...")


def _read(path: str, d: date) -> pd.DataFrame | None:
    raw = open(path, "rb").read()
    if not raw:
        return None
    b = lzma.decompress(raw)
    a = np.frombuffer(b, dtype=">i4").reshape(-1, 6)
    vol = np.frombuffer(b, dtype=">f4").reshape(-1, 6)[:, 5]
    t = pd.Timestamp(d, tz="UTC") + pd.to_timedelta(a[:, 0], unit="s")
    df = pd.DataFrame({"open": a[:, 1] / SCALE, "high": a[:, 4] / SCALE, "low": a[:, 3] / SCALE,
                       "close": a[:, 2] / SCALE, "volume": vol.astype(float)}, index=t)
    # Dukascopy rellena los minutos sin operaciones con velas planas de volumen 0: se eliminan
    flat = (df.volume <= 0) & (df.high == df.low)
    return df[~flat]


def load(symbol: str, start: str, end: str) -> pd.DataFrame:
    """Velas de 1 minuto en UTC (desde la caché local; descarga lo que falte)."""
    instr = INSTRUMENTS[symbol]
    cache = os.path.join(CACHE, f"duka-{symbol}-1m-{start}-{end}.pkl")
    if os.path.exists(cache):
        return pd.read_pickle(cache)
    download(start, end, [symbol])
    frames = []
    for d in days(start, end):
        p = _path(instr, d)
        if os.path.exists(p):
            df = _read(p, d)
            if df is not None and len(df):
                frames.append(df)
    out = pd.concat(frames).sort_index()
    out = out[~out.index.duplicated()]
    out.index.name = "time"
    os.makedirs(CACHE, exist_ok=True)
    out.to_pickle(cache)
    return out


if __name__ == "__main__":
    download(sys.argv[1], sys.argv[2], sys.argv[3:] or None)
