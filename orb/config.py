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
