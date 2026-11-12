# Agente analista — dukascopy (2022-01-03 → 2026-11-06)

Rupturas analizadas: 9515. Pruebas: 1815. Hallazgos estables: 51 (q < 0,05 tras Benjamini-Hochberg, |efecto| ≥ 5 pp, mismo signo en IS y OOS y en ≥ 75 % de los años).

## Probabilidad base de cada escenario (%)

| session   |   or_min |   Continúa sin volver |   Vuelve y continúa en la 1.ª dirección |   Vuelve, rompe el otro extremo y continúa |   Llega al otro extremo y es rechazado |   Vuelve y se queda en rango |
|:----------|---------:|----------------------:|----------------------------------------:|-------------------------------------------:|---------------------------------------:|-----------------------------:|
| London    |       15 |                   4.6 |                                    71.3 |                                       20.3 |                                    2.5 |                          1.2 |
| London    |       20 |                   5.5 |                                    69.7 |                                       18.8 |                                    3.0 |                          3.0 |
| NewYork   |       15 |                   5.2 |                                    71.7 |                                       19.3 |                                    2.8 |                          1.1 |
| NewYork   |       20 |                   5.4 |                                    72.3 |                                       17.0 |                                    3.2 |                          2.1 |

## Hallazgos estables (ordenados por significación)

| session   |   or_min | evento_txt                                       | condicion              | valor                                    |   n |   p_cond |   p_base |   lift_pp |   lift_IS |   lift_OOS | anios_mismo_signo   |   q_value |
|:----------|---------:|:-------------------------------------------------|:-----------------------|:-----------------------------------------|----:|---------:|---------:|----------:|----------:|-----------:|:--------------------|----------:|
| London    |       20 | Escenario: Vuelve y se queda en rango            | tam_rango              | grande                                   | 702 |      8.1 |      3.0 |       5.1 |       5.4 |        4.7 | 5/5                 |       0.0 |
| London    |       20 | Toca el extremo opuesto                          | tam_rango              | pequeño                                  | 703 |     61.5 |     48.3 |      13.1 |      12.7 |       13.3 | 5/5                 |       0.0 |
| NewYork   |       20 | Toca el extremo opuesto                          | tam_rango              | pequeño                                  | 717 |     60.4 |     47.8 |      12.6 |      11.6 |       14.1 | 5/5                 |       0.0 |
| London    |       15 | Llega a la extensión 1.618                       | tam_rango              | grande                                   | 702 |     63.8 |     74.8 |     -11.0 |     -13.2 |       -8.6 | 5/5                 |       0.0 |
| London    |       20 | Llega a la extensión 1.618                       | tam_rango              | grande                                   | 702 |     59.3 |     70.7 |     -11.4 |     -14.8 |       -7.4 | 5/5                 |       0.0 |
| London    |       20 | Cierra más allá del extremo opuesto              | tam_rango              | pequeño                                  | 703 |     57.6 |     45.3 |      12.3 |      10.8 |       13.8 | 5/5                 |       0.0 |
| London    |       20 | Llega a la extensión 1.618                       | tam_rango              | pequeño                                  | 703 |     81.8 |     70.7 |      11.1 |      11.5 |       10.0 | 5/5                 |       0.0 |
| NewYork   |       20 | Cierra más allá del extremo opuesto              | tam_rango              | pequeño                                  | 717 |     57.2 |     45.6 |      11.6 |      11.1 |       12.4 | 5/5                 |       0.0 |
| London    |       15 | Toca el extremo opuesto                          | tam_rango              | pequeño                                  | 704 |     66.1 |     54.3 |      11.7 |      10.6 |       13.1 | 5/5                 |       0.0 |
| London    |       15 | Cierra más allá del extremo opuesto              | tam_rango              | pequeño                                  | 704 |     61.9 |     51.5 |      10.5 |       8.6 |       13.0 | 5/5                 |       0.0 |
| NewYork   |       20 | Toca el extremo opuesto                          | tam_rango              | grande                                   | 715 |     37.6 |     47.8 |     -10.1 |      -9.2 |      -10.1 | 5/5                 |       0.0 |
| NewYork   |       20 | Cierra más allá del extremo opuesto              | tam_rango              | grande                                   | 715 |     35.7 |     45.6 |      -9.9 |      -8.8 |      -10.1 | 5/5                 |       0.0 |
| NewYork   |       15 | Llega a la extensión 1.618                       | tam_rango              | grande                                   | 717 |     68.8 |     77.0 |      -8.2 |      -7.7 |       -8.8 | 5/5                 |       0.0 |
| NewYork   |       15 | Toca el extremo opuesto                          | tam_rango              | pequeño                                  | 718 |     63.4 |     53.9 |       9.5 |       7.4 |       12.8 | 5/5                 |       0.0 |
| London    |       15 | Llega a la extensión 1.618                       | tam_rango              | pequeño                                  | 704 |     83.2 |     74.8 |       8.4 |       9.7 |        6.3 | 5/5                 |       0.0 |
| London    |       20 | Toca el extremo opuesto                          | tam_rango              | grande                                   | 702 |     38.6 |     48.3 |      -9.7 |      -7.8 |      -12.6 | 5/5                 |       0.0 |
| NewYork   |       15 | Toca el extremo opuesto                          | tam_rango              | grande                                   | 717 |     44.5 |     53.9 |      -9.4 |     -10.1 |       -7.6 | 5/5                 |       0.0 |
| NewYork   |       15 | Cierra más allá del extremo opuesto              | tam_rango              | grande                                   | 717 |     42.4 |     51.6 |      -9.2 |     -10.0 |       -7.5 | 5/5                 |       0.0 |
| NewYork   |       20 | Retrocede al 50 % del rango                      | tam_rango              | pequeño                                  | 717 |     75.9 |     67.3 |       8.6 |       9.3 |        7.3 | 5/5                 |       0.0 |
| London    |       20 | Cierra más allá del extremo opuesto              | tam_rango              | grande                                   | 702 |     36.0 |     45.3 |      -9.3 |      -6.6 |      -13.1 | 5/5                 |       0.0 |
| London    |       15 | Toca el extremo opuesto                          | tam_rango              | grande                                   | 702 |     45.2 |     54.3 |      -9.2 |      -7.8 |      -11.0 | 5/5                 |       0.0 |
| NewYork   |       20 | Llega a la extensión 1.618                       | tam_rango              | grande                                   | 715 |     65.0 |     73.0 |      -8.0 |      -9.3 |       -6.5 | 5/5                 |       0.0 |
| NewYork   |       15 | Cierra más allá del extremo opuesto              | tam_rango              | pequeño                                  | 718 |     59.9 |     51.6 |       8.3 |       5.8 |       12.2 | 5/5                 |       0.0 |
| NewYork   |       15 | Llega a la extensión 1.618                       | tam_rango              | pequeño                                  | 718 |     84.0 |     77.0 |       7.0 |       8.8 |        4.4 | 5/5                 |       0.0 |
| NewYork   |       20 | Llega a la extensión 1.618                       | tam_rango              | pequeño                                  | 717 |     80.1 |     73.0 |       7.1 |       7.2 |        6.8 | 5/5                 |       0.0 |
| NewYork   |       20 | Retrocede al 50 % del rango                      | tam_rango              | grande                                   | 715 |     59.9 |     67.3 |      -7.4 |      -9.4 |       -5.2 | 5/5                 |       0.0 |
| London    |       15 | Cierra más allá del extremo opuesto              | tam_rango              | grande                                   | 702 |     43.4 |     51.5 |      -8.0 |      -6.2 |      -10.5 | 5/5                 |       0.0 |
| London    |       15 | Retrocede al 50 % del rango                      | tam_rango              | pequeño                                  | 704 |     80.4 |     73.4 |       7.0 |       6.4 |        7.8 | 5/5                 |       0.0 |
| London    |       20 | Retrocede al 50 % del rango                      | tam_rango              | pequeño                                  | 703 |     76.2 |     69.2 |       7.0 |       7.4 |        6.2 | 5/5                 |       0.0 |
| London    |       20 | Escenario: Llega al otro extremo y es rechazado  | escenario_ayer         | Vuelve y se queda en rango               |  73 |     12.3 |      3.0 |       9.3 |       8.0 |       11.6 | 4/4                 |       0.0 |
| London    |       20 | Escenario: Vuelve y se queda en rango            | escenario_ayer         | Vuelve y se queda en rango               |  73 |     12.3 |      3.0 |       9.3 |      14.3 |        0.8 | 4/4                 |       0.0 |
| NewYork   |       15 | Retrocede al 50 % del rango                      | tam_rango              | pequeño                                  | 718 |     78.1 |     71.8 |       6.4 |       6.7 |        5.9 | 5/5                 |       0.0 |
| London    |       20 | Retrocede al 50 % del rango                      | tam_rango              | grande                                   | 702 |     63.1 |     69.2 |      -6.1 |      -5.0 |       -7.9 | 5/5                 |       0.0 |
| NewYork   |       15 | Retrocede al 50 % del rango                      | dia_semana             | Wed                                      | 473 |     79.1 |     71.8 |       7.3 |       8.6 |        5.5 | 5/5                 |       0.0 |
| London    |       20 | Escenario: Vuelve y continúa en la 1.ª dirección | escenario_ayer         | Vuelve y se queda en rango               |  73 |     49.3 |     69.7 |     -20.4 |     -19.2 |      -22.4 | 4/4                 |       0.0 |
| NewYork   |       15 | Retrocede al 50 % del rango                      | tam_rango              | grande                                   | 717 |     66.4 |     71.8 |      -5.4 |      -9.1 |       -1.3 | 4/5                 |       0.0 |
| NewYork   |       20 | Cierra más allá del extremo opuesto              | dia_semana             | Wed                                      | 471 |     53.3 |     45.6 |       7.7 |      10.0 |        4.5 | 4/5                 |       0.0 |
| London    |       15 | Retrocede al 50 % del rango                      | tam_rango              | grande                                   | 702 |     68.1 |     73.4 |      -5.3 |      -3.8 |       -7.3 | 5/5                 |       0.0 |
| NewYork   |       20 | Toca el extremo opuesto                          | dia_semana             | Wed                                      | 471 |     55.4 |     47.8 |       7.7 |      10.9 |        3.0 | 4/5                 |       0.0 |
| London    |       15 | Llega a la extensión 1.618                       | escenario_ayer         | Vuelve, rompe el otro extremo y continúa | 496 |     81.0 |     74.8 |       6.2 |       7.2 |        4.7 | 5/5                 |       0.0 |
| NewYork   |       20 | Escenario: Vuelve y continúa en la 1.ª dirección | ruptura_vs_diaria      | sin tendencia                            | 627 |     66.8 |     72.3 |      -5.5 |      -5.7 |       -4.9 | 5/5                 |       0.0 |
| NewYork   |       15 | Toca el extremo opuesto                          | dia_semana             | Wed                                      | 473 |     61.1 |     53.9 |       7.2 |       9.3 |        4.3 | 5/5                 |       0.0 |
| NewYork   |       20 | Retrocede al 50 % del rango                      | dia_semana             | Wed                                      | 471 |     74.1 |     67.3 |       6.8 |       8.5 |        4.3 | 5/5                 |       0.0 |
| London    |       15 | 1.618 antes de retroceder al 50 %                | escenario_ayer         | Vuelve, rompe el otro extremo y continúa | 496 |     59.9 |     53.1 |       6.8 |       7.7 |        4.9 | 4/5                 |       0.0 |
| NewYork   |       20 | Retrocede al 50 % del rango                      | dia_semana             | Tue                                      | 486 |     60.9 |     67.3 |      -6.4 |      -7.4 |       -4.9 | 5/5                 |       0.0 |
| NewYork   |       15 | Cierra más allá del extremo opuesto              | dia_semana             | Wed                                      | 473 |     58.4 |     51.6 |       6.8 |       8.0 |        5.1 | 5/5                 |       0.0 |
| London    |       20 | Llega a la extensión 1.618                       | dia_semana             | Mon                                      | 452 |     64.4 |     70.7 |      -6.3 |      -8.4 |       -3.1 | 4/5                 |       0.0 |
| NewYork   |       15 | Retrocede al 50 % del rango                      | dia_semana             | Tue                                      | 486 |     65.8 |     71.8 |      -5.9 |      -8.6 |       -1.8 | 4/5                 |       0.0 |
| London    |       15 | 1.618 antes de retroceder al 50 %                | tam_rango              | grande                                   | 702 |     48.0 |     53.1 |      -5.1 |      -7.1 |       -2.3 | 5/5                 |       0.0 |
| NewYork   |       20 | 1.618 antes de retroceder al 50 %                | contexto_previo        | baja                                     | 615 |     58.0 |     52.8 |       5.2 |       5.8 |        4.1 | 4/5                 |       0.0 |
| NewYork   |       20 | Escenario: Vuelve y continúa en la 1.ª dirección | apertura_vs_dia_previo | bajo mínimo previo                       | 372 |     78.8 |     72.3 |       6.5 |       6.9 |        5.9 | 5/5                 |       0.0 |

## Repetición: P(mismo escenario hoy que ayer) frente a la base

| session   |   or_min | hoy                                      |   n_ayer |    p |   p_base |   lift_pp |
|:----------|---------:|:-----------------------------------------|---------:|-----:|---------:|----------:|
| London    |       20 | Vuelve y se queda en rango               |       73 | 12.3 |      3.0 |       9.3 |
| NewYork   |       15 | Llega al otro extremo y es rechazado     |       64 |  4.7 |      2.8 |       1.9 |
| London    |       15 | Llega al otro extremo y es rechazado     |       62 |  3.2 |      2.5 |       0.7 |
| London    |       20 | Vuelve y continúa en la 1.ª dirección    |     1696 | 69.9 |     69.7 |       0.2 |
| NewYork   |       15 | Vuelve, rompe el otro extremo y continúa |      448 | 19.2 |     19.3 |      -0.1 |
| London    |       20 | Llega al otro extremo y es rechazado     |       73 |  2.7 |      3.0 |      -0.3 |
| NewYork   |       20 | Vuelve y continúa en la 1.ª dirección    |     1676 | 71.9 |     72.4 |      -0.5 |
| NewYork   |       15 | Vuelve y continúa en la 1.ª dirección    |     1664 | 71.2 |     71.7 |      -0.5 |
| London    |       15 | Vuelve y continúa en la 1.ª dirección    |     1736 | 70.8 |     71.3 |      -0.5 |
| NewYork   |       20 | Continúa sin volver                      |      125 |  4.8 |      5.4 |      -0.6 |
| NewYork   |       20 | Vuelve, rompe el otro extremo y continúa |      394 | 16.2 |     17.0 |      -0.8 |
| London    |       15 | Continúa sin volver                      |      113 |  3.5 |      4.6 |      -1.1 |
| NewYork   |       20 | Llega al otro extremo y es rechazado     |       73 |  1.4 |      3.1 |      -1.7 |
| London    |       20 | Continúa sin volver                      |      133 |  3.0 |      5.5 |      -2.5 |
| London    |       20 | Vuelve, rompe el otro extremo y continúa |      459 | 16.1 |     18.9 |      -2.7 |
| London    |       15 | Vuelve, rompe el otro extremo y continúa |      496 | 16.9 |     20.3 |      -3.4 |
| NewYork   |       15 | Continúa sin volver                      |      120 |  1.7 |      5.2 |      -3.5 |

## Escenarios según `contexto_previo` (%)

| session   |   or_min | contexto_previo   |   Continúa sin volver |   Vuelve y continúa en la 1.ª dirección |   Vuelve, rompe el otro extremo y continúa |   Llega al otro extremo y es rechazado |   Vuelve y se queda en rango |    n |
|:----------|---------:|:------------------|----------------------:|----------------------------------------:|-------------------------------------------:|---------------------------------------:|-----------------------------:|-----:|
| London    |       15 | alza              |                   5.3 |                                    72.1 |                                       18.8 |                                    3.0 |                          0.9 |  741 |
| London    |       15 | baja              |                   5.0 |                                    71.5 |                                       19.7 |                                    2.0 |                          1.8 |  603 |
| London    |       15 | rango             |                   4.0 |                                    70.7 |                                       21.8 |                                    2.6 |                          1.0 | 1094 |
| London    |       20 | alza              |                   5.5 |                                    69.1 |                                       19.8 |                                    2.4 |                          3.1 |  741 |
| London    |       20 | baja              |                   5.6 |                                    68.6 |                                       18.8 |                                    2.8 |                          4.2 |  602 |
| London    |       20 | rango             |                   5.3 |                                    70.7 |                                       18.2 |                                    3.5 |                          2.3 | 1093 |
| NewYork   |       15 | alza              |                   5.8 |                                    67.4 |                                       22.6 |                                    2.2 |                          2.1 |  674 |
| NewYork   |       15 | baja              |                   3.7 |                                    76.3 |                                       16.9 |                                    2.4 |                          0.6 |  617 |
| NewYork   |       15 | rango             |                   5.6 |                                    71.7 |                                       18.6 |                                    3.4 |                          0.7 | 1032 |
| NewYork   |       20 | alza              |                   5.6 |                                    70.6 |                                       18.3 |                                    2.5 |                          3.0 |  673 |
| NewYork   |       20 | baja              |                   5.4 |                                    74.8 |                                       14.5 |                                    3.7 |                          1.6 |  615 |
| NewYork   |       20 | rango             |                   5.2 |                                    71.9 |                                       17.7 |                                    3.3 |                          1.8 | 1030 |

## Escenarios según `ruptura_vs_previo` (%)

| session   |   or_min | ruptura_vs_previo   |   Continúa sin volver |   Vuelve y continúa en la 1.ª dirección |   Vuelve, rompe el otro extremo y continúa |   Llega al otro extremo y es rechazado |   Vuelve y se queda en rango |    n |
|:----------|---------:|:--------------------|----------------------:|----------------------------------------:|-------------------------------------------:|---------------------------------------:|-----------------------------:|-----:|
| London    |       15 | a favor             |                   6.0 |                                    69.6 |                                       19.6 |                                    2.8 |                          2.0 |  652 |
| London    |       15 | en contra           |                   4.3 |                                    73.8 |                                       18.8 |                                    2.3 |                          0.7 |  692 |
| London    |       15 | sin tendencia       |                   4.0 |                                    70.7 |                                       21.8 |                                    2.6 |                          1.0 | 1094 |
| London    |       20 | a favor             |                   5.7 |                                    67.9 |                                       19.4 |                                    3.1 |                          3.9 |  644 |
| London    |       20 | en contra           |                   5.4 |                                    69.8 |                                       19.3 |                                    2.1 |                          3.3 |  699 |
| London    |       20 | sin tendencia       |                   5.3 |                                    70.7 |                                       18.2 |                                    3.5 |                          2.3 | 1093 |
| NewYork   |       15 | a favor             |                   5.8 |                                    70.7 |                                       20.1 |                                    2.5 |                          0.9 |  642 |
| NewYork   |       15 | en contra           |                   3.9 |                                    72.6 |                                       19.6 |                                    2.2 |                          1.8 |  649 |
| NewYork   |       15 | sin tendencia       |                   5.6 |                                    71.7 |                                       18.6 |                                    3.4 |                          0.7 | 1032 |
| NewYork   |       20 | a favor             |                   6.2 |                                    71.2 |                                       17.2 |                                    3.3 |                          2.1 |  632 |
| NewYork   |       20 | en contra           |                   4.9 |                                    73.9 |                                       15.7 |                                    2.9 |                          2.6 |  656 |
| NewYork   |       20 | sin tendencia       |                   5.2 |                                    71.9 |                                       17.7 |                                    3.3 |                          1.8 | 1030 |

## Escenarios según `tendencia_diaria` (%)

| session   |   or_min | tendencia_diaria   |   Continúa sin volver |   Vuelve y continúa en la 1.ª dirección |   Vuelve, rompe el otro extremo y continúa |   Llega al otro extremo y es rechazado |   Vuelve y se queda en rango |    n |
|:----------|---------:|:-------------------|----------------------:|----------------------------------------:|-------------------------------------------:|---------------------------------------:|-----------------------------:|-----:|
| London    |       15 | alcista            |                   4.8 |                                    71.3 |                                       19.7 |                                    3.1 |                          1.0 | 1119 |
| London    |       15 | bajista            |                   4.7 |                                    69.2 |                                       22.8 |                                    2.0 |                          1.3 |  549 |
| London    |       15 | lateral            |                   4.8 |                                    69.3 |                                       22.0 |                                    2.5 |                          1.4 |  440 |
| London    |       15 | n/d                |                   3.6 |                                    77.3 |                                       16.1 |                                    1.5 |                          1.5 |  330 |
| London    |       20 | alcista            |                   5.5 |                                    69.0 |                                       19.5 |                                    3.1 |                          2.9 | 1119 |
| London    |       20 | bajista            |                   6.2 |                                    68.9 |                                       19.7 |                                    2.6 |                          2.7 |  549 |
| London    |       20 | lateral            |                   4.3 |                                    69.5 |                                       18.5 |                                    3.9 |                          3.9 |  439 |
| London    |       20 | n/d                |                   5.8 |                                    73.9 |                                       15.8 |                                    2.1 |                          2.4 |  329 |
| NewYork   |       15 | alcista            |                   4.3 |                                    73.0 |                                       19.5 |                                    2.1 |                          1.1 | 1137 |
| NewYork   |       15 | bajista            |                   5.9 |                                    71.0 |                                       19.0 |                                    3.2 |                          0.9 |  559 |
| NewYork   |       15 | lateral            |                   5.3 |                                    70.6 |                                       19.5 |                                    3.3 |                          1.3 |  456 |
| NewYork   |       15 | n/d                |                   8.2 |                                    67.8 |                                       18.1 |                                    4.7 |                          1.2 |  171 |
| NewYork   |       20 | alcista            |                   4.0 |                                    74.5 |                                       16.9 |                                    2.9 |                          1.7 | 1134 |
| NewYork   |       20 | bajista            |                   5.6 |                                    74.0 |                                       14.5 |                                    3.6 |                          2.3 |  557 |
| NewYork   |       20 | lateral            |                   6.8 |                                    68.6 |                                       19.1 |                                    3.3 |                          2.2 |  456 |
| NewYork   |       20 | n/d                |                  10.5 |                                    62.0 |                                       19.9 |                                    3.5 |                          4.1 |  171 |

## Escenarios según `ruptura_vs_diaria` (%)

| session   |   or_min | ruptura_vs_diaria   |   Continúa sin volver |   Vuelve y continúa en la 1.ª dirección |   Vuelve, rompe el otro extremo y continúa |   Llega al otro extremo y es rechazado |   Vuelve y se queda en rango |   n |
|:----------|---------:|:--------------------|----------------------:|----------------------------------------:|-------------------------------------------:|---------------------------------------:|-----------------------------:|----:|
| London    |       15 | a favor             |                   3.7 |                                    71.0 |                                       21.8 |                                    2.7 |                          0.8 | 845 |
| London    |       15 | en contra           |                   6.0 |                                    70.2 |                                       19.7 |                                    2.8 |                          1.3 | 823 |
| London    |       15 | sin tendencia       |                   4.3 |                                    72.7 |                                       19.5 |                                    2.1 |                          1.4 | 770 |
| London    |       20 | a favor             |                   4.0 |                                    69.2 |                                       21.5 |                                    2.8 |                          2.6 | 859 |
| London    |       20 | en contra           |                   7.5 |                                    68.7 |                                       17.4 |                                    3.1 |                          3.2 | 809 |
| London    |       20 | sin tendencia       |                   4.9 |                                    71.4 |                                       17.3 |                                    3.1 |                          3.3 | 768 |
| NewYork   |       15 | a favor             |                   4.8 |                                    71.2 |                                       20.5 |                                    2.7 |                          0.8 | 840 |
| NewYork   |       15 | en contra           |                   4.9 |                                    73.5 |                                       18.2 |                                    2.2 |                          1.2 | 856 |
| NewYork   |       15 | sin tendencia       |                   6.1 |                                    69.9 |                                       19.1 |                                    3.7 |                          1.3 | 627 |
| NewYork   |       20 | a favor             |                   4.4 |                                    74.2 |                                       16.8 |                                    3.0 |                          1.6 | 838 |
| NewYork   |       20 | en contra           |                   4.6 |                                    74.4 |                                       15.5 |                                    3.3 |                          2.2 | 853 |
| NewYork   |       20 | sin tendencia       |                   7.8 |                                    66.8 |                                       19.3 |                                    3.3 |                          2.7 | 627 |

## Escenarios según `ruptura_vs_gap` (%)

| session   |   or_min | ruptura_vs_gap          |   Continúa sin volver |   Vuelve y continúa en la 1.ª dirección |   Vuelve, rompe el otro extremo y continúa |   Llega al otro extremo y es rechazado |   Vuelve y se queda en rango |   n |
|:----------|---------:|:------------------------|----------------------:|----------------------------------------:|-------------------------------------------:|---------------------------------------:|-----------------------------:|----:|
| NewYork   |       15 | a favor del gap         |                   5.6 |                                    70.0 |                                       21.0 |                                    2.3 |                          1.1 | 899 |
| NewYork   |       15 | gap plano               |                   5.3 |                                    71.7 |                                       19.4 |                                    3.1 |                          0.5 | 417 |
| NewYork   |       15 | hacia el cierre del gap |                   4.1 |                                    74.1 |                                       17.7 |                                    2.7 |                          1.3 | 874 |
| NewYork   |       20 | a favor del gap         |                   5.7 |                                    71.9 |                                       17.4 |                                    2.8 |                          2.2 | 862 |
| NewYork   |       20 | gap plano               |                   5.0 |                                    73.1 |                                       17.5 |                                    3.6 |                          0.7 | 416 |
| NewYork   |       20 | hacia el cierre del gap |                   4.3 |                                    74.0 |                                       16.2 |                                    3.2 |                          2.3 | 907 |

## Escenarios según `vs_londres` (%)

| session   |   or_min | vs_londres          |   Continúa sin volver |   Vuelve y continúa en la 1.ª dirección |   Vuelve, rompe el otro extremo y continúa |   Llega al otro extremo y es rechazado |   Vuelve y se queda en rango |    n |
|:----------|---------:|:--------------------|----------------------:|----------------------------------------:|-------------------------------------------:|---------------------------------------:|-----------------------------:|-----:|
| NewYork   |       15 | contraria a Londres |                   4.4 |                                    72.1 |                                       19.5 |                                    2.8 |                          1.2 | 1127 |
| NewYork   |       15 | igual que Londres   |                   5.9 |                                    70.9 |                                       19.6 |                                    2.5 |                          1.1 | 1142 |
| NewYork   |       20 | contraria a Londres |                   5.4 |                                    71.8 |                                       17.7 |                                    2.9 |                          2.2 | 1079 |
| NewYork   |       20 | igual que Londres   |                   5.5 |                                    72.9 |                                       16.6 |                                    3.0 |                          2.0 | 1184 |
