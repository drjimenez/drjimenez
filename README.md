# TTFM: modelo fractal estilo TTrades para TradingView

Indicador y estrategia en **Pine Script v6** que mecanizan el *fractal model* divulgado por TTrades,
junto con un **backtest independiente en Python** sobre Forex, Cripto, Índices y Commodities y un
**informe en PDF** con los resultados.

> **Aviso:** proyecto de investigación. No constituye asesoramiento financiero ni recomendación de
> inversión. Los resultados son simulados, se han obtenido con *proxies* de datos y no garantizan
> resultados futuros.

## El modelo en una línea

Una vela de temporalidad alta (**C2**) barre el high o el low de la vela anterior (**C1**) y cierra de
vuelta dentro de su rango. Durante la vela siguiente (**C3**) se busca en temporalidad baja un
**CISD** (*Change In State of Delivery*) a favor del giro. El stop va en el extremo barrido de C2 y
el objetivo en su extremo opuesto.

| Concepto | Regla |
|---|---|
| Sweep alcista | `low(C2) < low(C1)` y `close(C2) > low(C1)` → sesgo alcista para C3 (bajista: simétrico). Si C2 barre ambos lados, se descarta. |
| CISD alcista | Nivel = apertura de la 1ª vela de la serie de velas LTF bajistas más reciente. Un cierre LTF por encima confirma la entrada (cada nivel solo confirma una vez). |
| Orden por vela LTF de C3 | invalidación (rompe el extremo de C2) → expiración (`maxEntryBars` = 12) → objetivo alcanzado antes del CISD → CISD |
| Entrada | Al cierre de la vela que confirma el CISD |
| Stop / objetivo | SL = extremo barrido de C2 ∓ 0,1 × ATR14 (LTF); TP = extremo opuesto de C2 |
| Filtro | R:R ≥ `minRR` (1,0). Si no se cumple, se omite esa señal y el setup sigue activo |
| Gestión | 1 trade por setup, 1 posición por activo, hasta SL o TP; riesgo 1 % del equity |
| Costes | Comisión 0,04 % por lado + slippage (Python 0,02 % por lado; Pine 1 tick) |

La especificación completa está en [`docs/SPEC.md`](docs/SPEC.md).

## Estructura

```
docs/SPEC.md                 Especificación común (reglas, universo, estructura)
pine/ttfm_indicator.pine     Indicador Pine v6: velas HTF C1/C2/C3, sweep, CISD, SL/TP, tabla y alertas
pine/README_indicator.md     Guía detallada del indicador
pine/ttfm_strategy.pine      Estrategia Pine v6 para el Strategy Tester (misma lógica que el indicador)
backtest/data_loader.py      Descarga y caché de velas del archivo público de Binance
backtest/ttfm_engine.py      Motor de señales y simulador barra a barra (con asserts anti look-ahead)
backtest/run_backtest.py     Ejecuta ambos perfiles, costes, sensibilidad y gráficos → results/
results/                     Trades, métricas (CSV), summary.json y gráficos PNG
report/build_report.py       Genera report/TTFM_Report.pdf a partir de results/
report/TTFM_Report.pdf       Informe completo (14 páginas)
```

## Uso en TradingView

1. Abre el gráfico del instrumento:
   - **Intradía:** gráfico de **15 minutos** con HTF **240** (4H), que es el valor por defecto.
   - **Swing:** gráfico de **1 hora** con HTF **D**.
2. Abre el **Pine Editor** (panel inferior), crea un script nuevo, borra el contenido y pega
   `pine/ttfm_indicator.pine`. Pulsa **Guardar** y **Añadir al gráfico**.
3. Repite el paso anterior en otro script con `pine/ttfm_strategy.pine` para ver las operaciones en
   el **Strategy Tester**.
4. En los ajustes (⚙) puedes cambiar la temporalidad HTF (`Auto` la deduce del gráfico), `minRR`,
   el buffer del SL en ATR, `maxEntryBars`, el riesgo por operación y el filtro de fechas.
   La HTF tiene que ser mayor que la temporalidad del gráfico.
5. Alertas del indicador: *TTFM Sweep alcista / bajista* y *TTFM CISD long / short*
   (Alertas → Crear alerta → Condición: TTFM).

Las velas HTF se construyen a partir de las velas del gráfico con `timeframe.change()`, sin
`request.security`, así que no hay repintado. En la estrategia, el CISD se evalúa siempre con la vela
cerrada. En el indicador, también por defecto.

> El código Pine se ha revisado a fondo, pero **no se ha podido compilar en TradingView desde este
> entorno**. Si el editor marca algún aviso, revisa la línea que indique.

## Reproducir el backtest

```bash
pip install -r requirements.txt          # pandas, numpy, matplotlib (+ reportlab para el PDF)
python3 backtest/run_backtest.py         # descarga datos a data/ (no versionado) y escribe results/
python3 report/build_report.py           # genera report/TTFM_Report.pdf
```

La primera ejecución descarga unas 9 series de 15 minutos de `data.binance.vision`. Después, una
ejecución completa (2 perfiles, versión sin costes y rejilla de sensibilidad) tarda unos 15 segundos.

**Datos y proxies** (2026-04-01 → 2026-11-10, velas de 15 minutos; 1H, 4H y 1D se obtienen por
agregación en UTC):

| Clase | Símbolos | Notas |
|---|---|---|
| Forex | EURUSDT (spot) | Proxy de EUR/USD |
| Cripto | BTCUSDT, ETHUSDT, SOLUSDT (spot) | |
| Índices | SPYUSDT, QQQUSDT | Perpetuos TradFi de Binance como proxy de S&P 500 y Nasdaq 100 |
| Commodities | XAUUSDT, XAGUSDT, CLUSDT | Perpetuos de oro, plata y WTI |

Capital de 10 000 USD por activo. La cartera es la media equiponderada de las curvas de cada activo.

## Resultados (netos de costes)

| Perfil | Trades | Win % | PF | Expectativa | Retorno cartera | Máx. DD | Sin costes |
|---|---:|---:|---:|---:|---:|---:|---:|
| Intradía 4H → 15m | 325 | 36,0 % | 0,35 | −0,65 R | **−20,52 %** | −20,61 % | −0,74 % |
| Swing 1D → 1H | 86 | 43,0 % | 0,87 | −0,09 R | **−0,85 %** | −2,07 % | +1,24 % |

Buy & hold medio del universo en el período: −3,04 %.

Conclusiones:

- **Intradía: no es rentable.** Sin costes la señal queda prácticamente en cero (−0,02 R por trade).
  Con costes pierde con claridad, porque los stops son muy cortos: la distancia mediana es del 0,32 %
  del precio y en EURUSDT del 0,07 %, frente a un coste de ida y vuelta del 0,12 %. Ninguna de las 9
  combinaciones de `minRR` (1 / 1,5 / 2) y buffer del SL (0 / 0,1 / 0,25 ATR) termina en positivo.
- **Swing: casi plano.** La ventaja bruta es pequeña (+0,13 R por trade) y los costes la anulan.
- **Commodities en swing: lo mejor.** Ganan +2,55 % con PF 1,45. XAU sube un +5,51 % y XAG un +5,14 %,
  mientras su buy & hold cae un −13,8 % y un −31,0 %. Hay pocas operaciones por activo (7-12), así que
  no es concluyente.

Hay más detalle en `results/summary.json`, en los CSV de `results/` y en
[`report/TTFM_Report.pdf`](report/TTFM_Report.pdf). El informe incluye métricas por clase y por activo,
retornos mensuales, sensibilidad, análisis bruto frente a neto, limitaciones y recomendaciones.

## Advertencias y limitaciones

- **Proxies:** EURUSDT de Binance no es el EUR/USD interbancario. Los perpetuos de índices y
  commodities cotizan 24/7 y no reproducen las sesiones, los gaps ni las velas por sesión de los
  mercados reales. En TradingView, con datos del subyacente, los resultados serán distintos.
- **Período corto** (algo más de 7 meses) y **muestras pequeñas**, sobre todo en swing.
- **Modelo mecanizado:** se opera cualquier sweep que cumpla la regla, sin el contexto discrecional
  (sesiones, SMT, FVG, niveles HTF) que usa el modelo original.
- **Diferencias de ejecución:** el Strategy Tester ordena SL y TP dentro de una vela con su propia
  heurística y aplica el slippage en ticks. Python asume SL primero y un slippage porcentual. Las cifras
  no coincidirán exactamente.
- **Alineación HTF:** las velas HTF se alinean a 00:00 UTC. En instrumentos con sesión, TradingView
  las alinea según la sesión del símbolo.

## Posibles mejoras (hipótesis a validar)

- Filtrar las entradas por sesiones (*killzones* de Londres y Nueva York).
- Priorizar HTF diaria con LTF de 1 hora, donde los stops son más amplios.
- Subir el R:R mínimo y fijar un stop mínimo en múltiplos del coste.
- Centrarse en commodities.
- Añadir confirmaciones con SMT o FVG.
- Validar con datos reales del subyacente, 2-3 años de histórico y *walk-forward*.
