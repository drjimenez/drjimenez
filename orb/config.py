"""
config.py — Parámetros del estudio ORB (Opening Range Breakout) con niveles Fibonacci.

Todas las horas de apertura se expresan en hora LOCAL de cada bolsa y se convierten a UTC
día a día con zoneinfo, de modo que los cambios de horario de verano (DST) de Londres y
Nueva York, que no coinciden en fechas, se respetan automáticamente.
"""
from __future__ import annotations

# --- Período (al menos 6 meses) -------------------------------------------------------------
START = "2026-05-01"
END = "2026-11-11"          # inclusive
# Partición para validar sin sobreajuste: se eligen reglas en IS y se comprueban en OOS.
IS_END = "2026-08-31"       # In-sample: mayo-agosto (4 meses). Out-of-sample: sept-nov.

# --- Instrumentos ----------------------------------------------------------------------------
# Proxies con datos de 1 minuto públicos y gratuitos (perpetuos TradFi de Binance, 24/7).
#   QQQUSDT -> Nasdaq 100     SPYUSDT -> S&P 500
# Para usar datos de tu bróker (NAS100 / US500 / NQ / ES) ver orb/README.md (importar CSV).
SYMBOLS = {
    "QQQUSDT": "Nasdaq 100 (proxy QQQ)",
    "SPYUSDT": "S&P 500 (proxy SPY)",
}

# --- Sesiones ----------------------------------------------------------------------------------
# open: hora local de apertura; horizon_end: hasta cuándo se sigue el precio tras el rango.
SESSIONS = {
    "London": {"tz": "Europe/London", "open": "08:00", "horizon_end": "12:00"},
    "NewYork": {"tz": "America/New_York", "open": "09:30", "horizon_end": "16:00"},
}

# Festivos 2026 (la bolsa correspondiente cierra -> el día se excluye de esa sesión)
HOLIDAYS = {
    "London": {"2026-05-04", "2026-05-25", "2026-08-31", "2026-12-25", "2026-12-28"},
    "NewYork": {"2026-05-25", "2026-06-19", "2026-07-03", "2026-09-07", "2026-11-26",
                "2026-12-25"},
}

# --- Rango de apertura --------------------------------------------------------------------------
OR_MINUTES = [15, 20]

# --- Fibonacci (en unidades del rango de apertura R = máximo − mínimo) --------------------------
# Retroceso: 0 = nivel roto (máximo si rompe al alza), 0.5 = mitad del rango, 1 = extremo opuesto.
RETRACE_LEVELS = [0.0, 0.236, 0.382, 0.5, 0.618, 0.786, 1.0]
# Extensión medida desde el nivel roto: 0.272 ≙ Fib 1.272, 0.618 ≙ 1.618, 1.0 ≙ 2.0, 1.618 ≙ 2.618
EXT_LEVELS = [0.272, 0.618, 1.0, 1.618]
EXT_LABEL = {0.272: "1.272", 0.618: "1.618", 1.0: "2.0", 1.618: "2.618"}

# --- Simulación de estrategias ------------------------------------------------------------------
ENTRIES = ["break", 0.0, 0.236, 0.382, 0.5]   # 'break' = cierre de la vela que rompe; nº = límite en retroceso
STOPS = [0.382, 0.5, 0.618, 0.786, 1.0]       # stop en ese nivel de retroceso (1.0 = extremo opuesto)
TARGETS = [0.272, 0.618, 1.0, 1.618]          # objetivo en extensión Fibonacci
COST_BP_PER_SIDE = 1.0                         # comisión + spread/slippage por lado (puntos básicos)
MIN_TRADES_IS = 25                             # mínimo de operaciones para considerar una regla

# Modelo de REVERSIÓN (fade): se opera en contra de la ruptura.
#   entrada: 'break' (al cierre de la vela que rompe) o límite en la extensión x = +nivel
#   stop: extensión x = +nivel (más allá de la entrada); objetivo: retroceso x = −nivel
#   (0 = vuelta al nivel roto, 0.5 = mitad del rango, 1.0 = extremo opuesto)
FADE_ENTRIES = ["break", 0.272, 0.618]
FADE_STOPS = [0.618, 1.0, 1.618]
FADE_TARGETS = [0.0, 0.5, 1.0]

# --- Contexto previo a cada apertura -----------------------------------------------------------
# Ventana "pre": desde pre_start (hora local) hasta la apertura. Londres: sesión asiática;
# Nueva York: mañana europea + premarket. Tendencia = (cierre − apertura) / (máx − mín) de la ventana:
#   ≥ +TREND_EFF -> alza   ≤ −TREND_EFF -> baja   en otro caso -> rango
SESSIONS["London"]["pre_start"] = "00:00"
SESSIONS["NewYork"]["pre_start"] = "04:00"
TREND_EFF = 0.4

# --- Escenarios tras la ruptura ---------------------------------------------------------------
SCEN_EXT = 0.272          # extensión 1.272 para considerar que "continúa"

# --- Gap Fibonacci: cierre NY anterior -> apertura NY ------------------------------------------
GAP_FLAT_ADR = 0.10       # |gap| < 10 % del rango diario medio (20 días) -> "plano" (sin Fibonacci)
GAP_FILL_LEVELS = [0.236, 0.382, 0.5, 0.618, 0.786, 1.0, 1.272, 1.618]
GAP_AWAY_LEVELS = [0.272, 0.618, 1.0]

# --- Fuentes de datos ---------------------------------------------------------------------------
SOURCES = {
    # CFD de Dukascopy, 1 minuto, datos reales del índice (cotizan casi 24 h)
    "dukascopy": {"start": "2022-01-03", "end": "2026-11-11", "is_end": "2024-12-31",
                  "symbols": {"NAS100": "Nasdaq 100 (CFD Dukascopy)", "US500": "S&P 500 (CFD Dukascopy)"}},
    # Perpetuos de Binance (estudio inicial de 6 meses)
    "binance": {"start": "2026-05-01", "end": "2026-11-11", "is_end": "2026-08-31",
                "symbols": {"QQQUSDT": "Nasdaq 100 (proxy QQQ)", "SPYUSDT": "S&P 500 (proxy SPY)"}},
}
SOURCE = "dukascopy"


def use_source(name: str) -> None:
    """Activa una fuente: ajusta período, partición IS/OOS y símbolos."""
    global SOURCE, START, END, IS_END, SYMBOLS
    s = SOURCES[name]
    SOURCE, START, END, IS_END, SYMBOLS = name, s["start"], s["end"], s["is_end"], dict(s["symbols"])


# Festivos completos 2022-2026 (NYSE y Bolsa de Londres)
HOLIDAYS["NewYork"] |= {
    "2022-01-17", "2022-02-21", "2022-04-15", "2022-05-30", "2022-06-20", "2022-07-04",
    "2022-09-05", "2022-11-24", "2022-12-26",
    "2023-01-02", "2023-01-16", "2023-02-20", "2023-04-07", "2023-05-29", "2023-06-19",
    "2023-07-04", "2023-09-04", "2023-11-23", "2023-12-25",
    "2024-01-01", "2024-01-15", "2024-02-19", "2024-03-29", "2024-05-27", "2024-06-19",
    "2024-07-04", "2024-09-02", "2024-11-28", "2024-12-25",
    "2025-01-01", "2025-01-09", "2025-01-20", "2025-02-17", "2025-04-18", "2025-05-26",
    "2025-06-19", "2025-07-04", "2025-09-01", "2025-11-27", "2025-12-25",
    "2026-01-01", "2026-01-19", "2026-02-16", "2026-04-03",
}
HOLIDAYS["London"] |= {
    "2022-01-03", "2022-04-15", "2022-04-18", "2022-05-02", "2022-06-02", "2022-06-03",
    "2022-08-29", "2022-09-19", "2022-12-26", "2022-12-27",
    "2023-01-02", "2023-04-07", "2023-04-10", "2023-05-01", "2023-05-08", "2023-05-29",
    "2023-08-28", "2023-12-25", "2023-12-26",
    "2024-01-01", "2024-03-29", "2024-04-01", "2024-05-06", "2024-05-27", "2024-08-26",
    "2024-12-25", "2024-12-26",
    "2025-01-01", "2025-04-18", "2025-04-21", "2025-05-05", "2025-05-26", "2025-08-25",
    "2025-12-25", "2025-12-26",
    "2026-01-01", "2026-04-03", "2026-04-06",
}

use_source(SOURCE)
SCEN_EXT_ALT = [0.272, 0.618, 1.0]   # umbrales alternativos (columnas scenario_1272 / _1618 / _20)
