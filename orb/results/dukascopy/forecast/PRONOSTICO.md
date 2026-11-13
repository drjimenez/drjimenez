# Agente de pronóstico (walk-forward) — dukascopy

Aperturas con ruptura: 9515. Calibración sin los primeros 120 días.

Brier: error cuadrático medio de la probabilidad (menor es mejor). `mejora_pct` compara el modelo condicionado con la frecuencia base acumulada sin condiciones.

| evento   | evento_txt                            |    n |   brier_modelo |   brier_base |   mejora_pct |   frecuencia_real |
|:---------|:--------------------------------------|-----:|---------------:|-------------:|-------------:|------------------:|
| alcista  | Primera ruptura alcista               | 8855 |         0.2511 |       0.2502 |        -0.33 |              52.6 |
| vuelve   | Vuelve al nivel roto                  | 8855 |         0.049  |       0.049  |         0.02 |              94.9 |
| toca50   | Toca el 50 % del rango                | 8855 |         0.2067 |       0.2086 |         0.88 |              70.4 |
| opuesto  | Toca el extremo opuesto               | 8855 |         0.2443 |       0.2498 |         2.23 |              50.9 |
| ext1618  | Llega a la extensión 1.618            | 8855 |         0.1876 |       0.1925 |         2.58 |              74   |
| continua | Vuelve y continúa en la 1.ª dirección | 8855 |         0.2058 |       0.2059 |         0.05 |              71.2 |
| giro     | Rompe el otro extremo y continúa      | 8855 |         0.1536 |       0.1537 |         0.07 |              18.9 |
