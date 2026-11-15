"""Descarga y caché de velas de 1 minuto de histdata.com (ASCII, M1), p. ej. NSXUSD (Nasdaq 100).

histdata publica un ZIP por mes (o por año, si el año está cerrado). Aunque su documentación
habla de EST fijo, para NSXUSD las horas son UTC-5 más el horario de verano europeo. Comprobado
cruzando con Dukascopy: es la misma serie, con diferencia 0 tras esta conversión, incluidas las
semanas de marzo y octubre/noviembre en que EE. UU. y Europa cambian de hora en fechas distintas.
Caché: data/histdata/<PAIR>/<YYYYMM>.zip
"""
from __future__ import annotations

import io
import re
import time
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "data" / "histdata"
PAGE = "https://www.histdata.com/download-free-forex-historical-data/?/ascii/1-minute-bar-quotes/{p}/{y}/{m}"
PAGE_Y = "https://www.histdata.com/download-free-forex-historical-data/?/ascii/1-minute-bar-quotes/{p}/{y}"
GET = "https://www.histdata.com/get.php"
UA = {"User-Agent": "Mozilla/5.0 (research script)"}


def _fetch_month(pair: str, y: int, m: int | None) -> Path | None:
    """m=None descarga el año completo (histdata publica años cerrados en un solo ZIP)."""
    tag = f"{y}" if m is None else f"{y}{m:02d}"
    path = CACHE / pair.upper() / f"{tag}.zip"
    if path.exists() and path.stat().st_size > 0:
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    page_url = PAGE.format(p=pair.lower(), y=y, m=m) if m else PAGE_Y.format(p=pair.lower(), y=y)
    for attempt in range(4):
        try:
            html = urllib.request.urlopen(urllib.request.Request(page_url, headers=UA), timeout=60).read().decode("utf-8", "ignore")
            tk = re.search(r'name="tk" id="tk" value="([0-9a-f]+)"', html)
            if not tk:
                return None
            form = {"tk": tk.group(1), "date": str(y), "datemonth": tag, "platform": "ASCII",
                    "timeframe": "M1", "fxpair": pair.upper()}
            req = urllib.request.Request(GET, data=urllib.parse.urlencode(form).encode(),
                                         headers={**UA, "Referer": page_url})
            data = urllib.request.urlopen(req, timeout=120).read()
            if data[:2] != b"PK":
                return None
            path.write_bytes(data)
            time.sleep(3)
            return path
        except Exception:
            time.sleep(10 * (attempt + 1))
    return None


def to_new_york(naive: pd.Series) -> pd.DatetimeIndex:
    """histdata: UTC-5 más 1 h cuando rige el horario de verano europeo (comprobado contra
    Dukascopy, también en las semanas de marzo y octubre en que EE. UU. y Europa no coinciden)."""
    utc = (naive + pd.Timedelta(hours=5)).dt.tz_localize("UTC")
    eu_dst = utc.dt.tz_convert("Europe/London").map(lambda t: t.dst() != pd.Timedelta(0))
    utc = utc - pd.to_timedelta(eu_dst.astype(int), unit="h")
    return pd.DatetimeIndex(utc).tz_convert("America/New_York")


def load_minutes(start: str, end: str, pair: str = "NSXUSD") -> pd.DataFrame:
    this_year = pd.Timestamp.now().year
    units = []
    for per in pd.period_range(start, end, freq="M"):
        u = (per.year, None) if per.year < this_year else (per.year, per.month)
        if u not in units:
            units.append(u)
    frames = []
    for y, m in units:
        p = _fetch_month(pair, y, m)
        if p is None:
            print(f"AVISO: sin datos histdata para {y}-{m}")
            continue
        with zipfile.ZipFile(p) as z:
            name = next(n for n in z.namelist() if n.endswith(".csv"))
            df = pd.read_csv(io.BytesIO(z.read(name)), sep=";", header=None,
                             names=["ts", "open", "high", "low", "close", "volume"])
        df.index = to_new_york(pd.to_datetime(df["ts"], format="%Y%m%d %H%M%S"))
        frames.append(df[["open", "high", "low", "close", "volume"]])
    out = pd.concat(frames).sort_index()
    out = out[~out.index.duplicated()]
    s, e = pd.Timestamp(start, tz="America/New_York"), pd.Timestamp(end, tz="America/New_York") + pd.Timedelta(days=1)
    return out[(out.index >= s) & (out.index < e)]


if __name__ == "__main__":
    m = load_minutes("2026-09-01", "2026-09-03")
    print(m.between_time("09:28", "09:32"))
