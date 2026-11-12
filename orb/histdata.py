"""
histdata.py — Velas de 1 minuto de HistData.com (gratuitas) para Nasdaq 100 y S&P 500.

  NAS100 -> NSXUSD      US500 -> SPXUSD

Un archivo ZIP por año (años cerrados) o por mes (año en curso), con un CSV:
    AAAAMMDD HHMMSS;open;high;low;close;volume
Las marcas de tiempo están en hora de Nueva York (con horario de verano). Comprobado contra el
datafeed de Dukascopy: los precios coinciden minuto a minuto, así que es la misma serie (CFD).

Los días del mes en curso que HistData aún no publica se completan con Dukascopy.
Caché de los ZIP en orb/data/raw/histdata/.

Uso:  python3 orb/histdata.py            (descarga 2022 -> mes anterior al actual)
"""
from __future__ import annotations

import io
import os
import re
import time
import urllib.parse
import urllib.request
import zipfile
from datetime import date, timedelta

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "data", "raw", "histdata")
CACHE = os.path.join(HERE, "data", "cache")
PAGE = "https://www.histdata.com/download-free-forex-historical-data/?/ascii/1-minute-bar-quotes/{pair}/{period}"
GET = "https://www.histdata.com/get.php"
PAIRS = {"NAS100": "NSXUSD", "US500": "SPXUSD"}
PAUSE = 2.0


def _periods(start: str, end: str) -> list[str]:
    """Años completos como 'AAAA'; el año de `end` mes a mes ('AAAA/M')."""
    s, e = date.fromisoformat(start), date.fromisoformat(end)
    out = [str(y) for y in range(s.year, e.year)]
    out += [f"{e.year}/{m}" for m in range(1, e.month + 1)]
    return out


def _fetch(pair: str, period: str) -> str | None:
    dest = os.path.join(RAW, pair, period.replace("/", "-") + ".zip")
    if os.path.exists(dest):
        return dest if os.path.getsize(dest) > 0 else None
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    page = PAGE.format(pair=pair.lower(), period=period)
    html = urllib.request.urlopen(page, timeout=60).read().decode("utf-8", "ignore")
    fields = dict(re.findall(r'<input type="hidden" name="(\w+)" id="\w+" value="([^"]*)"', html))
    if "tk" not in fields:
        return None
    req = urllib.request.Request(GET, data=urllib.parse.urlencode(
        {k: fields[k] for k in ("tk", "date", "datemonth", "platform", "timeframe", "fxpair")}).encode(),
        headers={"Referer": page})          # el formulario de la página envía su propia URL
    data = urllib.request.urlopen(req, timeout=180).read()
    time.sleep(PAUSE)
    if not data.startswith(b"PK"):
        open(dest, "wb").close()             # periodo aún no publicado
        return None
    with open(dest + ".tmp", "wb") as f:
        f.write(data)
    os.replace(dest + ".tmp", dest)
    return dest


def _read(path: str) -> pd.DataFrame:
    with zipfile.ZipFile(path) as z:
        name = next(n for n in z.namelist() if n.endswith(".csv"))
        df = pd.read_csv(io.BytesIO(z.read(name)), sep=";", header=None,
                         names=["t", "open", "high", "low", "close", "volume"])
    ts = pd.to_datetime(df.t, format="%Y%m%d %H%M%S").dt.tz_localize(
        "America/New_York", ambiguous="NaT", nonexistent="NaT")
    df.index = pd.DatetimeIndex(ts).tz_convert("UTC")
    df.index.name = "time"
    return df.loc[df.index.notna(), ["open", "high", "low", "close", "volume"]].astype(float)


def load(symbol: str, start: str, end: str) -> pd.DataFrame:
    cache = os.path.join(CACHE, f"histdata-{symbol}-1m-{start}-{end}.pkl")
    if os.path.exists(cache):
        return pd.read_pickle(cache)
    pair = PAIRS[symbol]
    frames = []
    for per in _periods(start, end):
        p = _fetch(pair, per)
        if p:
            frames.append(_read(p))
            print(f"[histdata] {pair} {per}: ok", flush=True)
        else:
            print(f"[histdata] {pair} {per}: no publicado", flush=True)
    df = pd.concat(frames).sort_index()
    df = df[~df.index.duplicated()]
    # Días posteriores al último publicado -> Dukascopy (misma serie)
    last = df.index.max().tz_convert("America/New_York").date()
    if last < date.fromisoformat(end):
        import dukascopy
        s = (last + timedelta(days=1)).isoformat()
        print(f"[histdata] {symbol}: completando {s} -> {end} con Dukascopy", flush=True)
        dk = dukascopy.load(symbol, s, end)
        df = pd.concat([df, dk[["open", "high", "low", "close", "volume"]]]).sort_index()
        df = df[~df.index.duplicated()]
    df = df.loc[pd.Timestamp(start, tz="UTC"): pd.Timestamp(end, tz="UTC") + pd.Timedelta(days=1)]
    os.makedirs(CACHE, exist_ok=True)
    df.to_pickle(cache)
    return df


if __name__ == "__main__":
    import config as C
    for s in PAIRS:
        d = load(s, C.SOURCES["dukascopy"]["start"], C.SOURCES["dukascopy"]["end"])
        print(s, len(d), d.index.min(), d.index.max())
