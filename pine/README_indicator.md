# TTFM — Indicador Fractal Model (estilo TTrades)

Archivo: `pine/ttfm_indicator.pine` (Pine Script v6). Implementa las reglas de `docs/SPEC.md`.

## Cómo añadirlo en TradingView
1. Abre un gráfico (p. ej. BTCUSDT en 15m) y el **Pine Editor** (panel inferior).
2. Crea un script nuevo, borra el contenido y pega todo `ttfm_indicator.pine`.
3. Pulsa **Guardar** y después **Añadir al gráfico**.
4. En la configuración (⚙) elige la temporalidad HTF (por defecto `240` = 4H; `Auto` mapea
   1m→15m, 5m→1H, 15m/30m→4H, 1H→D, 4H→W) y ajusta reglas/colores.
5. Alertas: menú **Alertas → Crear alerta → Condición: TTFM** y elige
   `TTFM Sweep alcista`, `TTFM Sweep bajista`, `TTFM CISD long` o `TTFM CISD short`.

La HTF debe ser mayor que la temporalidad del gráfico (si no, la tabla muestra ⚠).

## Qué muestra
| Elemento | Significado |
|---|---|
| Velas a la derecha del precio | Últimas N velas HTF (cuerpo = caja, mechas = líneas). La de la derecha (más transparente) es la vela en formación **C3**; a su izquierda **C2** y **C1**. Debajo, la hora de apertura (o fecha si HTF ≥ 1D). |
| Líneas azules continuas | High/low de **C1** (rango que debe ser barrido), proyectadas durante C3. |
| Líneas naranjas discontinuas | High/low de **C2** (vela del barrido): el extremo barrido es la base del SL y el opuesto el TP. |
| Etiqueta `Sweep ▲ / ▼` | Al abrir C3: C2 barrió el low (high) de C1 y cerró dentro → sesgo alcista (bajista). |
| Fondo verde/rojo suave | Sesgo activo durante C3 mientras se busca entrada o hay señal. |
| Línea punteada `CISD pendiente` | Nivel CISD vigente = apertura de la 1ª vela de la serie opuesta más reciente. |
| Línea magenta + `CISD ▲ / ▼` | Confirmación: una vela LTF cerró a través del nivel → entrada al cierre. |
| Líneas Entrada / SL / TP | Entrada = cierre de la vela CISD; SL = extremo de C2 ± `slBufATR`×ATR14; TP = extremo opuesto de C2 (con R:R). |
| `✕ Invalidado` | El precio rompió el extremo de C2 antes del CISD: setup cancelado. |
| Tabla | HTF, sesgo, estado (Esperando / Sweep / CISD / Invalidado / Expirado / Objetivo alcanzado), R:R (estimado o de la señal) y velas transcurridas de C3 frente a `maxEntryBars`. |

## Reglas clave implementadas
- Velas HTF construidas manualmente con `timeframe.change()` (sin `request.security`, sin repintado);
  la primera vela HTF parcial del histórico se descarta.
- Si C2 barre **ambos** extremos de C1 → sin sesgo (caso ambiguo).
- Cada serie de velas solo puede confirmar un CISD una vez (el nivel se consume al cerrarse a través de él).
- Orden por vela LTF: invalidación → expiración (`maxEntryBars`) → objetivo alcanzado (opcional) → CISD.
- Si R:R < `minRR` la señal se omite y el setup sigue buscando otro CISD. Una sola señal por setup HTF.
- Por defecto el CISD solo se confirma con la vela LTF cerrada.

## Versión visual sin alertas (`ttfm_indicator_visual.pine`)

Variante del mismo indicador analizado en el backtest, con idéntica lógica de detección
(velas HTF C1/C2/C3, sweep, sesgo, CISD, invalidación y expiración), pero:

- **Sin `alertcondition`**: no crea alertas de sweep ni de entrada/salida.
- **Sin proyección de Entrada / SL / TP** ni fila de R:R en la tabla.

Úsala como herramienta de lectura del modelo fractal. Se añade igual: Pine Editor →
pegar el código → *Add to chart* (recomendado: gráfico 15m con HTF 240, o 1H con HTF D).
