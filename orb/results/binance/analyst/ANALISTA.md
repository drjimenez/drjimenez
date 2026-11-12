# Agente analista — binance (2026-05-01 → 2026-11-11)

Rupturas analizadas: 1081. Pruebas: 1639. Hallazgos estables: 3 (q < 0,05 tras Benjamini-Hochberg, |efecto| ≥ 5 pp, mismo signo en IS y OOS y en ≥ 75 % de los años).

## Probabilidad base de cada escenario (%)

| session   |   or_min |   Continúa sin volver |   Vuelve y continúa en la 1.ª dirección |   Vuelve, rompe el otro extremo y continúa |   Llega al otro extremo y es rechazado |   Vuelve y se queda en rango |
|:----------|---------:|----------------------:|----------------------------------------:|-------------------------------------------:|---------------------------------------:|-----------------------------:|
| London    |       15 |                   5.9 |                                    66.2 |                                       25.0 |                                    2.6 |                          0.4 |
| London    |       20 |                   7.4 |                                    67.3 |                                       20.2 |                                    3.3 |                          1.8 |
| NewYork   |       15 |                   8.1 |                                    65.9 |                                       17.4 |                                    3.7 |                          4.8 |
| NewYork   |       20 |                   7.9 |                                    66.3 |                                       13.5 |                                    7.5 |                          4.9 |

## Hallazgos estables (ordenados por significación)

| session   |   or_min | evento_txt                            | condicion   | valor   |   n |   p_cond |   p_base |   lift_pp |   lift_IS |   lift_OOS | anios_mismo_signo   |   q_value |
|:----------|---------:|:--------------------------------------|:------------|:--------|----:|---------:|---------:|----------:|----------:|-----------:|:--------------------|----------:|
| London    |       20 | Toca el extremo opuesto               | tam_rango   | pequeño |  76 |     71.1 |     51.5 |      19.6 |      14.3 |       36.2 | 1/1                 |       0.0 |
| London    |       20 | Cierra más allá del extremo opuesto   | tam_rango   | pequeño |  76 |     69.7 |     50.4 |      19.4 |      13.7 |       37.1 | 1/1                 |       0.0 |
| NewYork   |       15 | Escenario: Vuelve y se queda en rango | tam_rango   | grande  |  76 |     13.2 |      4.8 |       8.3 |       6.9 |        9.1 | 1/1                 |       0.0 |

## Repetición: P(mismo escenario hoy que ayer) frente a la base

| session   |   or_min | hoy                                      |   n_ayer |    p |   p_base |   lift_pp |
|:----------|---------:|:-----------------------------------------|---------:|-----:|---------:|----------:|
| London    |       15 | Vuelve, rompe el otro extremo y continúa |       68 | 30.9 |     24.8 |       6.1 |
| London    |       15 | Vuelve y continúa en la 1.ª dirección    |      178 | 67.4 |     66.3 |       1.1 |
| NewYork   |       20 | Vuelve y continúa en la 1.ª dirección    |      175 | 66.9 |     66.0 |       0.8 |
| London    |       20 | Vuelve y continúa en la 1.ª dirección    |      181 | 66.3 |     67.0 |      -0.7 |
| NewYork   |       15 | Vuelve y continúa en la 1.ª dirección    |      177 | 63.8 |     65.7 |      -1.8 |

## Escenarios según `contexto_previo` (%)

| session   |   or_min | contexto_previo   |   Continúa sin volver |   Vuelve y continúa en la 1.ª dirección |   Vuelve, rompe el otro extremo y continúa |   Llega al otro extremo y es rechazado |   Vuelve y se queda en rango |   n |
|:----------|---------:|:------------------|----------------------:|----------------------------------------:|-------------------------------------------:|---------------------------------------:|-----------------------------:|----:|
| London    |       15 | alza              |                   5.9 |                                    67.6 |                                       22.5 |                                    2.9 |                          1.0 | 102 |
| London    |       15 | baja              |                   7.8 |                                    65.6 |                                       25.0 |                                    1.6 |                          0.0 |  64 |
| London    |       15 | rango             |                   4.7 |                                    65.1 |                                       27.4 |                                    2.8 |                          0.0 | 106 |
| London    |       20 | alza              |                   8.8 |                                    69.6 |                                       15.7 |                                    2.9 |                          2.9 | 102 |
| London    |       20 | baja              |                   6.2 |                                    60.9 |                                       26.6 |                                    3.1 |                          3.1 |  64 |
| London    |       20 | rango             |                   6.6 |                                    68.9 |                                       20.8 |                                    3.8 |                          0.0 | 106 |
| NewYork   |       15 | alza              |                  10.3 |                                    62.8 |                                       14.1 |                                    5.1 |                          7.7 |  78 |
| NewYork   |       15 | baja              |                   4.8 |                                    68.3 |                                       19.0 |                                    1.6 |                          6.3 |  63 |
| NewYork   |       15 | rango             |                   8.5 |                                    66.7 |                                       18.6 |                                    3.9 |                          2.3 | 129 |
| NewYork   |       20 | alza              |                  10.4 |                                    62.3 |                                        7.8 |                                   11.7 |                          7.8 |  77 |
| NewYork   |       20 | baja              |                   6.5 |                                    71.0 |                                       14.5 |                                    3.2 |                          4.8 |  62 |
| NewYork   |       20 | rango             |                   7.0 |                                    66.4 |                                       16.4 |                                    7.0 |                          3.1 | 128 |

## Escenarios según `ruptura_vs_previo` (%)

| session   |   or_min | ruptura_vs_previo   |   Continúa sin volver |   Vuelve y continúa en la 1.ª dirección |   Vuelve, rompe el otro extremo y continúa |   Llega al otro extremo y es rechazado |   Vuelve y se queda en rango |   n |
|:----------|---------:|:--------------------|----------------------:|----------------------------------------:|-------------------------------------------:|---------------------------------------:|-----------------------------:|----:|
| London    |       15 | a favor             |                   8.3 |                                    67.9 |                                       21.4 |                                    2.4 |                          0.0 |  84 |
| London    |       15 | en contra           |                   4.9 |                                    65.9 |                                       25.6 |                                    2.4 |                          1.2 |  82 |
| London    |       15 | sin tendencia       |                   4.7 |                                    65.1 |                                       27.4 |                                    2.8 |                          0.0 | 106 |
| London    |       20 | a favor             |                   7.1 |                                    69.4 |                                       17.6 |                                    3.5 |                          2.4 |  85 |
| London    |       20 | en contra           |                   8.6 |                                    63.0 |                                       22.2 |                                    2.5 |                          3.7 |  81 |
| London    |       20 | sin tendencia       |                   6.6 |                                    68.9 |                                       20.8 |                                    3.8 |                          0.0 | 106 |
| NewYork   |       15 | a favor             |                  10.4 |                                    63.6 |                                       19.5 |                                    2.6 |                          3.9 |  77 |
| NewYork   |       15 | en contra           |                   4.7 |                                    67.2 |                                       12.5 |                                    4.7 |                         10.9 |  64 |
| NewYork   |       15 | sin tendencia       |                   8.5 |                                    66.7 |                                       18.6 |                                    3.9 |                          2.3 | 129 |
| NewYork   |       20 | a favor             |                   6.9 |                                    69.4 |                                       12.5 |                                    8.3 |                          2.8 |  72 |
| NewYork   |       20 | en contra           |                  10.4 |                                    62.7 |                                        9.0 |                                    7.5 |                         10.4 |  67 |
| NewYork   |       20 | sin tendencia       |                   7.0 |                                    66.4 |                                       16.4 |                                    7.0 |                          3.1 | 128 |

## Escenarios según `tendencia_diaria` (%)

| session   |   or_min | tendencia_diaria   |   Continúa sin volver |   Vuelve y continúa en la 1.ª dirección |   Vuelve, rompe el otro extremo y continúa |   Llega al otro extremo y es rechazado |   Vuelve y se queda en rango |   n |
|:----------|---------:|:-------------------|----------------------:|----------------------------------------:|-------------------------------------------:|---------------------------------------:|-----------------------------:|----:|
| London    |       15 | alcista            |                   5.5 |                                    65.8 |                                       23.3 |                                    5.5 |                          0.0 |  73 |
| London    |       15 | bajista            |                   1.4 |                                    75.7 |                                       20.0 |                                    1.4 |                          1.4 |  70 |
| London    |       15 | lateral            |                   8.2 |                                    60.0 |                                       29.4 |                                    2.4 |                          0.0 |  85 |
| London    |       15 | n/d                |                   9.1 |                                    63.6 |                                       27.3 |                                    0.0 |                          0.0 |  44 |
| London    |       20 | alcista            |                   8.2 |                                    58.9 |                                       26.0 |                                    4.1 |                          2.7 |  73 |
| London    |       20 | bajista            |                   2.9 |                                    75.7 |                                       17.1 |                                    2.9 |                          1.4 |  70 |
| London    |       20 | lateral            |                   9.4 |                                    65.9 |                                       18.8 |                                    4.7 |                          1.2 |  85 |
| London    |       20 | n/d                |                   9.1 |                                    70.5 |                                       18.2 |                                    0.0 |                          2.3 |  44 |
| NewYork   |       15 | alcista            |                   4.1 |                                    67.1 |                                       17.8 |                                    2.7 |                          8.2 |  73 |
| NewYork   |       15 | bajista            |                  15.7 |                                    61.4 |                                       15.7 |                                    1.4 |                          5.7 |  70 |
| NewYork   |       15 | lateral            |                   6.9 |                                    65.5 |                                       18.4 |                                    5.7 |                          3.4 |  87 |
| NewYork   |       15 | n/d                |                   5.0 |                                    72.5 |                                       17.5 |                                    5.0 |                          0.0 |  40 |
| NewYork   |       20 | alcista            |                   4.2 |                                    66.2 |                                       16.9 |                                    7.0 |                          5.6 |  71 |
| NewYork   |       20 | bajista            |                  11.4 |                                    60.0 |                                        7.1 |                                   12.9 |                          8.6 |  70 |
| NewYork   |       20 | lateral            |                  11.6 |                                    62.8 |                                       16.3 |                                    5.8 |                          3.5 |  86 |
| NewYork   |       20 | n/d                |                   0.0 |                                    85.0 |                                       12.5 |                                    2.5 |                          0.0 |  40 |

## Escenarios según `ruptura_vs_diaria` (%)

| session   |   or_min | ruptura_vs_diaria   |   Continúa sin volver |   Vuelve y continúa en la 1.ª dirección |   Vuelve, rompe el otro extremo y continúa |   Llega al otro extremo y es rechazado |   Vuelve y se queda en rango |   n |
|:----------|---------:|:--------------------|----------------------:|----------------------------------------:|-------------------------------------------:|---------------------------------------:|-----------------------------:|----:|
| London    |       15 | a favor             |                   2.7 |                                    71.2 |                                       21.9 |                                    2.7 |                          1.4 |  73 |
| London    |       15 | en contra           |                   4.3 |                                    70.0 |                                       21.4 |                                    4.3 |                          0.0 |  70 |
| London    |       15 | sin tendencia       |                   8.5 |                                    61.2 |                                       28.7 |                                    1.6 |                          0.0 | 129 |
| London    |       20 | a favor             |                   4.2 |                                    67.6 |                                       23.9 |                                    2.8 |                          1.4 |  71 |
| London    |       20 | en contra           |                   6.9 |                                    66.7 |                                       19.4 |                                    4.2 |                          2.8 |  72 |
| London    |       20 | sin tendencia       |                   9.3 |                                    67.4 |                                       18.6 |                                    3.1 |                          1.6 | 129 |
| NewYork   |       15 | a favor             |                   5.2 |                                    67.2 |                                       20.7 |                                    1.7 |                          5.2 |  58 |
| NewYork   |       15 | en contra           |                  12.9 |                                    62.4 |                                       14.1 |                                    2.4 |                          8.2 |  85 |
| NewYork   |       15 | sin tendencia       |                   6.3 |                                    67.7 |                                       18.1 |                                    5.5 |                          2.4 | 127 |
| NewYork   |       20 | a favor             |                   5.5 |                                    61.8 |                                       18.2 |                                    9.1 |                          5.5 |  55 |
| NewYork   |       20 | en contra           |                   9.3 |                                    64.0 |                                        8.1 |                                   10.5 |                          8.1 |  86 |
| NewYork   |       20 | sin tendencia       |                   7.9 |                                    69.8 |                                       15.1 |                                    4.8 |                          2.4 | 126 |

## Escenarios según `ruptura_vs_gap` (%)

| session   |   or_min | ruptura_vs_gap          |   Continúa sin volver |   Vuelve y continúa en la 1.ª dirección |   Vuelve, rompe el otro extremo y continúa |   Llega al otro extremo y es rechazado |   Vuelve y se queda en rango |   n |
|:----------|---------:|:------------------------|----------------------:|----------------------------------------:|-------------------------------------------:|---------------------------------------:|-----------------------------:|----:|
| NewYork   |       15 | a favor del gap         |                   7.6 |                                    68.6 |                                       17.1 |                                    4.8 |                          1.9 | 105 |
| NewYork   |       15 | gap plano               |                  12.3 |                                    61.5 |                                       23.1 |                                    3.1 |                          0.0 |  65 |
| NewYork   |       15 | hacia el cierre del gap |                   6.1 |                                    65.3 |                                       14.3 |                                    3.1 |                         11.2 |  98 |
| NewYork   |       20 | a favor del gap         |                   6.8 |                                    65.0 |                                       13.6 |                                   11.7 |                          2.9 | 103 |
| NewYork   |       20 | gap plano               |                   7.7 |                                    75.4 |                                       15.4 |                                    1.5 |                          0.0 |  65 |
| NewYork   |       20 | hacia el cierre del gap |                   9.3 |                                    60.8 |                                       12.4 |                                    7.2 |                         10.3 |  97 |

## Escenarios según `vs_londres` (%)

| session   |   or_min | vs_londres          |   Continúa sin volver |   Vuelve y continúa en la 1.ª dirección |   Vuelve, rompe el otro extremo y continúa |   Llega al otro extremo y es rechazado |   Vuelve y se queda en rango |   n |
|:----------|---------:|:--------------------|----------------------:|----------------------------------------:|-------------------------------------------:|---------------------------------------:|-----------------------------:|----:|
| NewYork   |       15 | contraria a Londres |                  11.5 |                                    63.4 |                                       17.6 |                                    3.8 |                          3.8 | 131 |
| NewYork   |       15 | igual que Londres   |                   5.2 |                                    67.4 |                                       17.8 |                                    3.7 |                          5.9 | 135 |
| NewYork   |       20 | contraria a Londres |                  10.2 |                                    61.7 |                                       16.4 |                                    8.6 |                          3.1 | 128 |
| NewYork   |       20 | igual que Londres   |                   5.9 |                                    70.4 |                                       11.1 |                                    5.9 |                          6.7 | 135 |
