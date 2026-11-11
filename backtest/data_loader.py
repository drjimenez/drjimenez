"""
data_loader.py — Descarga y caché de klines desde el archivo público de Binance
(https://data.binance.vision), según docs/SPEC.md.

- Spot:          data/spot/monthly/klines/{SYM}/{TF}/{SYM}-{TF}-{YYYY-MM}.zip
- Futuros USDⓈ-M: data/futures/um/monthly/klines/{SYM}/{TF}/{SYM}-{TF}-{YYYY-MM}.zip
- Mes en curso (noviembre 2026): archivos diarios .../daily/klines/.../{SYM}-{TF}-{YYYY-MM-DD}.zip

Notas de formato:
- Los CSV de spot desde 2025 traen timestamps en MICROsegundos; se detecta por magnitud.
- Los CSV de futuros traen cabecera; los de spot no.

Se descarga 15m y se derivan 1h / 4h / 1D por resample en UTC (velas alineadas a 00:00 UTC,
igual que TradingView para cripto).
"""
from __future__ import annotations

import io
import os
import time
import zipfile
import urllib.request
import urllib.error
from datetime import date, timedelta

import pandas as pd

BASE_URL = "https://data.binance.vision"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, "data")
RAW_DIR = os.path.join(DATA_DIR, "raw")
CACHE_DIR = os.path.join(DATA_DIR, "cache")

# Universo de SPEC: símbolo -> (mercado, clase de activo)
UNIVERSE = {
    "EURUSDT": ("spot", "Forex"),
    "BTCUSDT": ("spot", "Cripto"),
    "ETHUSDT": ("spot", "Cripto"),
    "SOLUSDT": ("spot", "Cripto"),
    "SPYUSDT": ("futures/um", "Indices"),
    "QQQUSDT": ("futures/um", "Indices"),
    "XAUUSDT": ("futures/um", "Commodities"),
    "XAGUSDT": ("futures/um", "Commodities"),
    "CLUSDT": ("futures/um", "Commodities"),
}

START = "2026-04-01"
END = "2026-11-10"  # inclusive (último día descargado)

COLS = ["open_time", "open", "high", "low", "close", "volume", "close_time",
        "quote_volume", "count", "taker_buy_volume", "taker_buy_quote_volume", "ignore"]


def _months_and_days(start: str, end: str):
    """Meses completos se piden como monthly; el mes en curso (el de `end`) como daily."""
    s = pd.Timestamp(start)
    e = pd.Timestamp(end)
    months, days = [], []
    cur = pd.Timestamp(year=s.year, month=s.month, day=1)
    last_month = pd.Timestamp(year=e.year, month=e.month, day=1)
    while cur < last_month:
        months.append(cur.strftime("%Y-%m"))
        cur = cur + pd.offsets.MonthBegin(1)
    d = last_month
    while d <= e:
        days.append(d.strftime("%Y-%m-%d"))
        d += pd.Timedelta(days=1)
    return months, days


def _download(url: str, dest: str, retries: int = 3) -> bool:
    if os.path.exists(dest) and os.path.getsize(dest) > 0:
        return True
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                data = r.read()
            with open(dest + ".tmp", "wb") as f:
                f.write(data)
            os.replace(dest + ".tmp", dest)
            return True
        except urllib.error.HTTPError as ex:
            if ex.code == 404:
                return False
            time.sleep(1 + attempt)
        except Exception:
            time.sleep(1 + attempt)
    return False


def _read_zip(path: str) -> pd.DataFrame:
    with zipfile.ZipFile(path) as z:
        name = z.namelist()[0]
        raw = z.read(name).decode()
    first = raw.split("\n", 1)[0]
    header = 0 if first.startswith("open_time") else None
    df = pd.read_csv(io.StringIO(raw), header=header, names=None if header == 0 else COLS)
    df.columns = COLS[: len(df.columns)]
    return df[["open_time", "open", "high", "low", "close", "volume"]]


def _to_utc(ts: pd.Series) -> pd.DatetimeIndex:
    # Detección de unidad por magnitud: ms ~1.7e12, us ~1.7e15, ns ~1.7e18
    ts = ts.astype("int64")
    ms =ts.where(ts < 1e14, ts // 1000)          # us -> ms
    ms = ms.where(ms < 1e14, ms // 1000)          # (ns -> us -> ms)
    return pd.to_datetime(ms, unit="ms", utc=True)


def load_symbol(symbol: str, tf: str = "15m", start: str = START, end: str = END,
                verbose: bool = True) -> pd.DataFrame:
    """Devuelve DataFrame OHLCV indexado por open_time (UTC) para [start, end]."""
    market, _ = UNIVERSE.get(symbol, ("spot", "?"))
    cache = os.path.join(CACHE_DIR, f"{symbol}-{tf}-{start}-{end}.pkl")
    if os.path.exists(cache):
        return pd.read_pickle(cache)
    months, days = _months_and_days(start, end)
    frames, missing = [], []
    for m in months:
        rel = f"data/{market}/monthly/klines/{symbol}/{tf}/{symbol}-{tf}-{m}.zip"
        dest = os.path.join(RAW_DIR, rel)
        if _download(f"{BASE_URL}/{rel}", dest):
            frames.append(_read_zip(dest))
        else:
            missing.append(m)
    for d in days:
        rel = f"data/{market}/daily/klines/{symbol}/{tf}/{symbol}-{tf}-{d}.zip"
        dest = os.path.join(RAW_DIR, rel)
        if _download(f"{BASE_URL}/{rel}", dest):
            frames.append(_read_zip(dest))
        else:
            missing.append(d)
    if verbose and missing:
        print(f"[data] {symbol} {tf}: sin archivo para {missing}")
    if not frames:
        return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])
    df = pd.concat(frames, ignore_index=True)
    df.index = _to_utc(df["open_time"])
    df.index.name = "time"
    df = df.drop(columns="open_time").astype(float)
    df = df[~df.index.duplicated(keep="first")].sort_index()
    df = df.loc[pd.Timestamp(start, tz="UTC"): pd.Timestamp(end, tz="UTC") + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)]
    os.makedirs(CACHE_DIR, exist_ok=True)
    df.to_pickle(cache)
    if verbose:
        print(f"[data] {symbol} {tf}: {len(df)} velas {df.index[0]} -> {df.index[-1]}")
    return df


def resample(df: pd.DataFrame, rule: str) -> pd.DataFrame:
    """Resample OHLCV en UTC, velas alineadas a 00:00 UTC (rule: '1h', '4h', '1D')."""
    if df.empty:
        return df
    out = df.resample(rule, origin="epoch", label="left", closed="left").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"})
    return out.dropna(subset=["open"])


def load_all(symbols=None, verbose=True) -> dict:
    symbols = symbols or list(UNIVERSE)
    return {s: load_symbol(s, verbose=verbose) for s in symbols}


if __name__ == "__main__":
    data = load_all()
    for s, df in data.items():
        print(s, UNIVERSE[s], len(df), df.index.min(), df.index.max())
