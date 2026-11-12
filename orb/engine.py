"""
engine.py — Extracción de eventos ORB y simulación de reglas con niveles Fibonacci.

Definiciones (todas en velas de 1 minuto):

* Rango de apertura (OR): máximo (H) y mínimo (L) de las N primeras velas desde la apertura
  local de la sesión. R = H − L.
* Ruptura: la PRIMERA vela posterior al OR cuyo CIERRE queda por encima de H (alcista) o por
  debajo de L (bajista), dentro del horizonte de la sesión. Si no hay cierre fuera: 'none'.
* Coordenada normalizada x (orientada en la dirección de la ruptura):
      ruptura alcista: x = (precio − H) / R        ruptura bajista: x = (L − precio) / R
  x > 0 es extensión a favor; x = 0 es el nivel roto; x = −0.5 la mitad del rango; x = −1 el
  extremo opuesto. Así, los retrocesos Fibonacci son x = −nivel y las extensiones x = +nivel.
* Retroceso a un nivel L_f: alguna vela posterior a la de ruptura tiene x_adverso ≤ −L_f.
* Extensión E: alguna vela posterior a la de ruptura tiene x_favorable ≥ E.

Para cada evento se guardan los minutos (desde la vela de ruptura) hasta el primer toque de
cada nivel de retroceso y de extensión. Con esas columnas se puede calcular en la base de datos
cualquier probabilidad del tipo "¿llega a la extensión E antes de retroceder al nivel F?".
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

import config as C


def _lvl(x: float) -> str:
    return f"{int(round(x * 1000)):04d}"


@dataclass
class Path:
    """Trayectoria normalizada tras la vela de ruptura (excluida)."""
    fav: np.ndarray     # extremo favorable (x del high en largo / del low en corto)
    adv: np.ndarray     # extremo adverso
    close: np.ndarray   # cierre
    break_x: float      # x del cierre de la vela de ruptura (precio de entrada 'break')
    price: float        # precio de referencia (para convertir costes en bp a unidades de R)
    range_pts: float


def session_days(session: str, start: str = C.START, end: str = C.END):
    hol = C.HOLIDAYS.get(session, set())
    d = date.fromisoformat(start)
    e = date.fromisoformat(end)
    while d <= e:
        if d.weekday() < 5 and d.isoformat() not in hol:
            yield d
        d += timedelta(days=1)


def _utc_minute(d: date, hhmm: str, tz: str) -> np.datetime64:
    hh, mm = map(int, hhmm.split(":"))
    loc = datetime.combine(d, time(hh, mm), tzinfo=ZoneInfo(tz))
    return np.datetime64(loc.astimezone(ZoneInfo("UTC")).replace(tzinfo=None), "m")


def _first(mask: np.ndarray) -> int:
    idx = np.flatnonzero(mask)
    return int(idx[0]) if idx.size else -1


def extract_events(symbol: str, bars: pd.DataFrame):
    """Devuelve (DataFrame de eventos, dict event_id -> Path)."""
    t = bars.index.tz_convert("UTC").tz_localize(None).values.astype("datetime64[m]")
    o = bars["open"].to_numpy(float)
    h = bars["high"].to_numpy(float)
    lo = bars["low"].to_numpy(float)
    c = bars["close"].to_numpy(float)

    rows, paths = [], {}
    for session, sc in C.SESSIONS.items():
        for d in session_days(session):
            t0 = _utc_minute(d, sc["open"], sc["tz"])
            t_end = _utc_minute(d, sc["horizon_end"], sc["tz"])
            i0 = int(np.searchsorted(t, t0))
            i_end = int(np.searchsorted(t, t_end))
            for n in C.OR_MINUTES:
                i_or = int(np.searchsorted(t, t0 + np.timedelta64(n, "m")))
                # Rango completo: exactamente n velas consecutivas
                if i_or - i0 != n or i_end - i_or < 30:
                    continue
                H, L = h[i0:i_or].max(), lo[i0:i_or].min()
                R = H - L
                if R <= 0:
                    continue
                ph, pl, pc = h[i_or:i_end], lo[i_or:i_end], c[i_or:i_end]
                pt = t[i_or:i_end]
                k_up, k_dn = _first(pc > H), _first(pc < L)
                touch_up, touch_dn = _first(ph > H), _first(pl < L)
                if touch_up < 0 and touch_dn < 0:
                    first_touch = "none"
                elif touch_dn < 0 or (0 <= touch_up < touch_dn):
                    first_touch = "up"
                elif touch_up < 0 or touch_dn < touch_up:
                    first_touch = "down"
                else:
                    first_touch = "both"   # misma vela toca ambos lados

                ev = {
                    "event_id": f"{symbol}|{d.isoformat()}|{session}|{n}",
                    "symbol": symbol, "date": d.isoformat(), "session": session, "or_min": n,
                    "weekday": d.strftime("%a"), "month": d.strftime("%Y-%m"),
                    "sample": "IS" if d.isoformat() <= C.IS_END else "OOS",
                    "open_price": o[i0], "or_high": H, "or_low": L, "or_range": R,
                    "or_range_bp": R / o[i0] * 1e4,
                    "first_touch": first_touch,
                }
                if k_up < 0 and k_dn < 0:
                    ev.update({"break_dir": "none"})
                    rows.append(ev)
                    continue
                if k_dn < 0 or (0 <= k_up < k_dn):
                    k, sgn, lvl = k_up, 1.0, H
                else:
                    k, sgn, lvl = k_dn, -1.0, L
                if sgn > 0:
                    fav, adv, cl = (ph - H) / R, (pl - H) / R, (pc - H) / R
                else:
                    fav, adv, cl = (L - pl) / R, (L - ph) / R, (L - pc) / R
                bx = cl[k]
                f, a, cc = fav[k + 1:], adv[k + 1:], cl[k + 1:]
                ev.update({
                    "break_dir": "up" if sgn > 0 else "down",
                    "break_time_utc": str(pt[k]),
                    "min_to_break": k + 1,                 # minutos tras cerrar el OR
                    "break_x": bx,
                    "max_ext": float(f.max()) if f.size else np.nan,
                    "max_retrace": float(-a.min()) if a.size else np.nan,
                    "close_x": float(cc[-1]) if cc.size else float(bx),
                })
                if f.size:
                    ipk = int(np.argmax(f))
                    ev["retrace_before_peak"] = float(-a[: ipk + 1].min())
                    ev["min_to_peak"] = ipk + 1
                    ev["retest"] = bool((a <= 0).any())
                    # Ruptura fallida: cierre más allá del extremo opuesto
                    ev["opposite_break"] = bool((cc < -1).any())
                    for e in C.EXT_LEVELS:
                        j = _first(f >= e)
                        ev[f"t_ext_{_lvl(e)}"] = j + 1 if j >= 0 else np.nan
                    for r in C.RETRACE_LEVELS:
                        j = _first(a <= -r)
                        ev[f"t_ret_{_lvl(r)}"] = j + 1 if j >= 0 else np.nan
                rows.append(ev)
                paths[ev["event_id"]] = Path(f, a, cc, float(bx), float(lvl), float(R))
    return pd.DataFrame(rows), paths


# --------------------------------------------------------------------------------------------
# Simulación de reglas
# --------------------------------------------------------------------------------------------

def simulate(p: Path, entry, stop: float, target: float, cost_bp: float = C.COST_BP_PER_SIDE):
    """
    Simula una operación a favor de la ruptura sobre la trayectoria normalizada.

    entry  : 'break' -> entrada al cierre de la vela de ruptura (x = break_x)
             float   -> orden límite en el retroceso x = −entry, activa desde la vela siguiente
                        a la ruptura y cancelada si el objetivo se alcanza antes del fill.
    stop   : nivel de retroceso (x = −stop).    target: extensión (x = +target).
    Supuestos conservadores: si en una misma vela se tocan stop y objetivo, cuenta el stop; en
    la vela del fill sólo se evalúa el stop. Sin salida: cierre al final del horizonte.
    Devuelve dict o None si no hay operación.
    """
    sx, tx = -stop, target
    n = p.fav.size
    if n == 0:
        return None
    if entry == "break":
        ex, i = p.break_x, 0
        if ex <= sx or ex >= tx:
            return None
        fill_bar_check_target = True
    else:
        ex = -float(entry)
        if ex <= sx:
            return None
        hit_fill = p.adv <= ex
        hit_tgt = p.fav >= tx
        jf, jt = _first(hit_fill), _first(hit_tgt)
        if jf < 0 or (0 <= jt < jf):
            return None          # nunca se llena o el objetivo llega antes (orden cancelada)
        i = jf
        fill_bar_check_target = False
    risk = ex - sx
    stop_hit = p.adv[i:] <= sx
    tgt_hit = p.fav[i:] >= tx
    if not fill_bar_check_target:
        tgt_hit = tgt_hit.copy()
        tgt_hit[0] = False
    js, jt = _first(stop_hit), _first(tgt_hit)
    if js >= 0 and (jt < 0 or js <= jt):
        out, xx, j = "stop", sx, js
    elif jt >= 0:
        out, xx, j = "target", tx, jt
    else:
        out, xx, j = "time", float(p.close[-1]), n - 1 - i
    r_gross = (xx - ex) / risk
    # coste ida y vuelta en unidades de x, convertido a R
    cost_x = 2 * cost_bp / 1e4 * p.price / p.range_pts
    return {"outcome": out, "r_gross": r_gross, "r_net": r_gross - cost_x / risk,
            "entry_x": ex, "risk_x": risk, "bars_in_trade": j + 1}


def flip(p: Path) -> Path:
    """Trayectoria vista desde el lado contrario (para el modelo de reversión / fade)."""
    return Path(-p.adv, -p.fav, -p.close, -p.break_x, p.price, p.range_pts)
