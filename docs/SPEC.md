# Especificación común — Modelo Fractal estilo TTrades (TTFM)

Documento de referencia compartido por los tres agentes. La lógica del indicador Pine,
la estrategia Pine y el motor de backtesting en Python DEBEN implementar exactamente estas reglas.

## Concepto
El "fractal model" difundido por TTrades parte de que cada vela de temporalidad alta (HTF)
se construye con la misma estructura en temporalidad baja (LTF). Se opera la formación de la
vela HTF "C2/C3":
1. **C1** = vela HTF previa (cerrada). Define el rango objetivo (high/low).
2. **C2** = vela HTF que barre (sweep) un extremo de C1 y cierra de vuelta dentro de su rango
   → sesgo (bias) en dirección opuesta al barrido. Ej.: C2.low < C1.low y C2.close > C1.low → alcista.
3. **C3** = vela HTF en curso, en la que se busca la entrada en LTF tras el barrido.
4. **CISD** (Change In State of Delivery) en LTF: en sesgo alcista, la serie de velas LTF bajistas
   consecutivas más reciente define el nivel CISD = apertura de la primera vela de esa serie.
   Un cierre LTF por encima de ese nivel confirma el CISD → entrada long al cierre de esa vela.
   (Simétrico para bajista: serie de velas alcistas, nivel = apertura de la primera, cierre por debajo.)
5. Opcional (filtro): la sesión de entrada debe ocurrir dentro de las primeras N velas LTF de C3
   (`maxEntryBars`) y antes de que el precio alcance el objetivo.

## Pares de temporalidades (HTF → LTF)
| Perfil | HTF | LTF |
|---|---|---|
| Intradía (por defecto) | 4H | 15m |
| Swing | 1D | 1H |

## Reglas de trading (versión backtestable)
- **Setup alcista**: vela HTF anterior (C2) con `low < low(C1)` y `close > low(C1)` (y `close < high(C1)`
  opcional no requerido). Durante la vela HTF actual (C3) buscar CISD alcista en LTF.
- **Stop loss**: mínimo de C2 (el extremo del barrido) − buffer (`slBufferATR` × ATR14 LTF, defecto 0.1).
- **Take profit**: high de C2 (extremo opuesto de la vela de barrido)   [TP1 = 50% en el punto medio de C2 opcional].
  Si el R:R resultante < `minRR` (defecto 1.0) se omite el trade.
- **Simétrico para bajista** (`high > high(C1)` y `close < high(C1)`; SL = high C2 + buffer; TP = low C2).
- **Invalidación**: si antes del CISD el precio rompe el extremo de C2 (nuevo low para long), el setup se cancela.
- **Gestión de tiempo**: si al cerrar la vela C3 la operación sigue abierta, se mantiene hasta SL/TP
  (no hay cierre forzado) salvo `timeExitBars` > 0.
- Un solo trade por setup HTF. Una posición a la vez por activo.
- **Costes**: comisión 0.04% por lado + slippage 1 tick (Python: 0.02% por lado adicional).
- **Riesgo**: 1% del capital por trade (sizing por distancia al SL). Capital inicial 10 000 USD.
- Orden de ejecución dentro de una vela LTF cuando toca SL y TP a la vez: se asume SL primero (conservador).

## Universo y datos (backtest Python)
Fuente: archivo público de Binance (data.binance.vision), klines 15m/1h, ya que los hosts de
Yahoo/otros están bloqueados en el entorno. Período: 2026-04-01 → 2026-11-10 (≥ 7 meses).
| Clase | Símbolos (proxy) |
|---|---|
| Forex | EURUSDT (spot, proxy de EURUSD) |
| Cripto | BTCUSDT, ETHUSDT, SOLUSDT (spot) |
| Índices | SPYUSDT (S&P 500), QQQUSDT (Nasdaq 100) — perpetuos USDⓈ-M TradFi |
| Commodities | XAUUSDT (oro), XAGUSDT (plata), CLUSDT (petróleo WTI) — perpetuos USDⓈ-M |

## Estructura del repositorio
```
pine/ttfm_indicator.pine      # Agente 1: indicador (infraestructura visual)
pine/ttfm_strategy.pine       # Agente 2: estrategia Pine (strategy()) para el Strategy Tester
backtest/data_loader.py       # Agente 2: descarga y caché de datos
backtest/ttfm_engine.py       # Agente 2: motor de señales + simulación
backtest/run_backtest.py      # Agente 2: corre todo el universo, guarda results/
results/                      # CSV/JSON/PNG de resultados
report/build_report.py        # Agente 3: genera report/TTFM_Report.pdf
README.md                     # Agente 3
```
