"""Genera report/ICT_Tres_Pilares_Medicion.pdf a partir de results/ict_pillars/summary.json."""
import json
from pathlib import Path

import pandas as pd
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.platypus import Image, PageBreak, SimpleDocTemplate, Spacer

import build_ict_methodology as B  # estilos y utilidades comunes (fuentes, tablas)

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "results" / "ict_pillars"
OUT = ROOT / "report" / "ICT_Tres_Pilares_Medicion.pdf"
P, table, bullets = B.P, B.table, B.bullets
H1, H2, BODY, NOTE, BOX, TITLE, SUB = B.H1, B.H2, B.BODY, B.NOTE, B.BOX, B.TITLE, B.SUB


def pct(x, d=1):
    return f"{x:.{d}f} %".replace(".", ",")


def num(x, d=2):
    return f"{x:+.{d}f}".replace(".", ",") if x == x else "—"


def ci(a, d=2):
    return f"[{a[0]:.{d}f}; {a[1]:.{d}f}]".replace(".", ",")


def pci(t, d=0):
    return f"{t[0]:.{d}f} % [{t[1]:.{d}f}–{t[2]:.{d}f}]".replace(".", ",")


def pv(p):
    return "—" if p != p else (f"{p:.3f}".replace(".", ",") if p >= 0.001 else "< 0,001")


def build():
    S = json.loads((RES / "summary.json").read_text())
    d, p1, p2, p3 = S["data"], S["pillar1"], S["pillar2"], S["pillar3"]
    fc = S["fvg_classes"]
    X = json.loads((RES / "extra_summary.json").read_text())
    lm, th, pre, pr = X["lunch_macro"], X["thursday"], X["pre830"], X["premarket_rule"]
    W = A4[0] - 4 * cm
    t1 = pd.read_csv(RES / "pillar1_trades.csv")
    t1["y"] = t1["date"].str[:4]
    s = []

    # Portada
    s += [Spacer(1, 4 * cm), P("Los tres pilares de ICT, medidos", TITLE),
          P("Premarket, 50 % del hueco de apertura y Silver Bullet de las 10:00, "
            f"comprobados en {d['sessions']} sesiones del Nasdaq 100 (1 minuto)", SUB),
          Spacer(1, 1 * cm),
          P(f"Datos: {d['first']} a {d['last']} · CFD del Nasdaq 100 como proxy del futuro NQ · "
            "hora de Nueva York", SUB),
          Spacer(1, 3 * cm),
          P("<b>Aviso.</b> Estudio estadístico con fines educativos; no es asesoramiento financiero. Las "
            "reglas son una traducción mecánica de lo que ICT describe en <i>How New Students Should "
            "Start</i> (partes 4 y 5); él usa además criterio discrecional que aquí no se puede "
            "reproducir.", BOX), PageBreak()]

    # Resumen
    sb = p3["10:00 (Silver Bullet)"]["stats"]
    st = p1["setup_sweep_opposite"]
    s += [P("Resumen", H1),
          P("Se midieron las afirmaciones concretas de las partes 1–5 de la serie y de tres vídeos más de ICT con reglas fijadas de antemano y, "
            "siempre que fue posible, frente a un <b>control</b>: el mismo cálculo en un nivel u hora "
            "donde ICT no espera nada especial. Si la idea de ICT es correcta, su nivel u hora debería "
            "salir claramente mejor que el control."),
          table([
              ["Afirmación de ICT", "Resultado", "Veredicto"],
              ["\"La mitad del hueco se rellena antes de las 10:00 el 70 % de las veces\"",
               f"{pct(p2['all']['ce_by_10'][0])} de los días. Un nivel a la misma distancia en el lado "
               f"<b>contrario</b> se alcanza el {pct(p2['all']['mirror_by_10'][0])} (p = {pv(p2['all']['p_paired'])}).",
               "No se confirma: es volatilidad, no imán"],
              ["Las proyecciones −1 del hueco \"marcan al tick\" el máximo o el mínimo de la mañana",
               f"El {pct(p2['projections']['near_1.0_pct'])} de los extremos cae a ±0,1 huecos del nivel; "
               f"niveles de control cercanos: {pct(p2['projections']['controls_mean_pct'])} de media.",
               "No se confirma"],
              ["El estado del premarket (07–09) anticipa la mañana (tendencia → consolidación)",
               f"Tras premarket en tendencia, la mañana consolida el {pct(p1['p_am_consol_given_pm_trend'][0])}; "
               f"tras consolidación, el {pct(p1['p_am_consol_given_pm_consol'][0])}. "
               f"Correlación {str(p1['corr_pm_er_am_er']).replace('.', ',')}.",
               "Relación muy débil y en sentido contrario"],
              ["Si el premarket consolida, a las 09:30 llega un gran movimiento en una dirección "
               "(<i>PreMarket Session Rules Revisited</i>)",
               f"Ese movimiento ocurre el {pct(pr['v2_pos']['big30']['consol'][0])} de los días tras "
               f"consolidación y el {pct(pr['v2_pos']['big30']['trend'][0])} tras tendencia; igual con tres "
               "definiciones de consolidación.", "No se confirma"],
              ["Los máximos/mínimos \"relativamente iguales\" atraen al precio",
               "Se toman con la misma frecuencia que los swings simples a igual distancia.",
               "No se confirma"],
              ["Setup: barrido de un extremo del premarket → extremo opuesto",
               f"{st['n']} operaciones, {num(st['R_net'])} R netos por operación "
               f"(IC 95 % {ci(st['R_net_ci'])}).", "Positivo pero no concluyente"],
              ["Silver Bullet: primer FVG de las 10:00",
               f"{sb['n']} operaciones, {num(sb['R_net'])} R netos (IC {ci(sb['R_net_ci'])}). Igual que "
               "la misma regla en otras horas.", "Sin ventaja; la hora no aporta"],
              ["El FVG \"con desplazamiento\" y el \"reflection\" mandan más que un FVG cualquiera",
               f"FPD {num(fc['groups']['FP con desplazamiento (FPD)']['R_net'])} R, FPR "
               f"{num(fc['groups']['First presented reflection (FPR)']['R_net'])} R, resto de FVG "
               f"{num(fc['groups']['Resto de FVG (control)']['R_net'])} R (netos).",
               "No se confirma"],
              ["Lunch macro: en días alcistas busca la sell side formada después de las 10:00",
               "Entre 11:30 y 13:00 se alcanza igual o menos que la liquidez a favor del sesgo, a igual distancia.",
               "No se confirma"],
              ["En semanas alcistas, el máximo se forma el jueves o el viernes lo rompe",
               f"{pct(th['thu_or_fri_high'][0])} de las semanas alcistas, frente a "
               f"{pct(th['thu_or_fri_high_perm_pct'])} con los días barajados al azar.",
               "Cierto, pero es aritmética, no un patrón"],
              ["Barrido del rango 07:00–08:29 tras la noticia de las 08:30 → extremo opuesto",
               f"{pre['all']['n']} operaciones, {num(pre['all']['R_net'])} R netos "
               f"(IC {ci(pre['all']['R_net_ci'])}).", "Sin ventaja"],
          ], [5.0 * cm, 8.0 * cm, W - 13.0 * cm]),
          Spacer(1, 6),
          P("<b>Conclusión.</b> Ninguno de los fenómenos concretos que ICT presenta como "
            "\"algorítmicos\" se distingue de lo que produce la volatilidad normal del Nasdaq. Lo único "
            "con un resultado positivo es el setup de barrido del premarket, y su intervalo de confianza "
            "todavía incluye el cero. Es el candidato a seguir estudiando, no algo para operar.", BOX)]

    # Datos y método
    s += [PageBreak(), P("1. Datos y método", H1),
          table([
              ["Elemento", "Detalle"],
              ["Fuente", "NSXUSD de histdata.com (1 minuto). Es la misma serie que USATECHIDXUSD de "
               "Dukascopy: <b>317.669 de 317.670 velas idénticas</b> en los meses comparados."],
              ["Horario", "Las horas de histdata son UTC−5 con el horario de verano <i>europeo</i> (no el de "
               "EE. UU., aunque su web diga EST). Se corrigió y validó contra Dukascopy, incluidas las "
               "semanas de marzo y octubre en que ambos cambios de hora no coinciden."],
              ["Sesiones", f"{d['sessions']} sesiones con vela a las 09:30 y a las 16:14 (se excluyen "
               "festivos y medias jornadas). Hueco = cierre de las 16:14 de la sesión anterior → "
               "apertura de las 09:30."],
              ["Validación", "Huecos del 31/08/2026 (−47 puntos) y del 01/09/2026 (−397) coinciden con "
               "los que cita ICT en las partes 1 y 2 (\"47 handles\", \"400 o más\")."],
              ["Costes", f"{str(d['cost_pts_round_trip']).replace('.', ',')} punto por operación de ida y "
               "vuelta (comisión + deslizamiento aproximados del NQ). Stop antes que objetivo si los "
               "dos caen en la misma vela."],
              ["Estadística", "Proporciones con IC 95 % de Wilson; medias en R con IC 95 % por bootstrap; "
               "comparaciones en los mismos días con test de McNemar."],
              ["Limitación principal", "Es un CFD, no el futuro: el nivel difiere unas decenas de puntos "
               "(base), pero los movimientos y huecos son los mismos. No hay volumen real."],
          ], [3.2 * cm, W - 3.2 * cm])]

    # Pilar 1
    eq = p1["equal_vs_single"]
    s += [P("2. Pilar 1: la sesión premarket (07:00–09:00)", H1),
          P("<b>Reglas.</b> Estado del tramo = eficiencia direccional (movimiento neto / rango): "
            f"≥ {str(d['er_trend']).replace('.', ',')} es tendencia; si no, consolidación. Lo mismo para la "
            "mañana (09:30–12:00). Swings = fractales de 2 velas; \"iguales\" si distan ≤ 0,01 % del precio."),
          Image(str(RES / "p1_states.png"), width=W, height=W * 2.6 / 7.5),
          *bullets([f"La relación entre premarket y mañana es casi nula (correlación "
                    f"{str(p1['corr_pm_er_am_er']).replace('.', ',')}). Si acaso, la consolidación tiende a "
                    f"repetirse (p = {pv(p1['p_value_diff'])}), al revés que en el ejemplo de ICT.",
                    f"Tras un premarket en tendencia, la mañana es algo más amplia (rango "
                    f"{num(p1['am_range_rel_after_pm_trend'][0] - 1)} frente a su mediana de 20 días, contra "
                    f"{num(p1['am_range_rel_after_pm_consol'][0] - 1)} tras consolidación).",
                    f"Entre las 09:30 y las 12:00 se toma el máximo del premarket el "
                    f"{pct(p1['pm_high_taken_pct'][0])} de los días y el mínimo el "
                    f"{pct(p1['pm_low_taken_pct'][0])}; ambos el "
                    f"{pct(100 * p1['pm_extremes_taken_9_30_12']['ambos'] / p1['days'])}. La mediana hasta "
                    f"la primera toma es de {p1['median_min_to_first_take']:.0f} minutos: el rango del "
                    "premarket suele estar muy cerca de la apertura."]),
          P("¿Atraen más los máximos y mínimos \"iguales\"?", H2),
          table([["Distancia a la apertura", "Iguales (n)", "Tomados", "Simples (n)", "Tomados", "p"]] +
                [[r["dist_pct"].replace("(", "").replace("]", "").replace(", ", "–").replace(".", ",") + " %",
                  r["n_equal"], pct(r["taken_equal_pct"]), r["n_single"], pct(r["taken_single_pct"]), pv(r["p"])]
                 for r in eq],
                [4.0 * cm, 2.3 * cm, 2.3 * cm, 2.3 * cm, 2.3 * cm, W - 13.2 * cm]),
          P("No hay diferencia en las distancias cortas y medias. En las lejanas, los iguales se toman "
            "<i>menos</i>.", NOTE),
          P("Regla revisada: consolidación en el premarket → movimiento grande a las 09:30", H2),
          P("En <i>Monday Review On NQ &amp; PreMarket Session Rules Revisited</i> (24/08/2026) Michael "
            "concreta: si de 07:00 a 09:00 el precio \"no puede extenderse\" y gira alrededor de la mitad "
            "del rango (un empujón inicial que solo barre liquidez no cuenta como tendencia), a las 09:30 "
            "llega \"un gran movimiento en una sola dirección\". Ese día se cumplió: premarket con "
            "eficiencia 0,18 y cierre a mitad de rango, y caída de 291 puntos en la primera media hora."),
          P("<b>Medición.</b> Tres definiciones de consolidación: V1 eficiencia &lt; 0,5; V2 cierre de las "
            "08:59 en la mitad central del rango (25–75 %); V3 estricta, ambas cosas (eficiencia &lt; 0,35), "
            "frente a tendencia estricta. Resultado en la apertura: rango (frente a su mediana de 20 días), "
            "eficiencia direccional y \"movimiento grande\" (eficiencia ≥ 0,6 y rango por encima de lo "
            "normal en 09:30–09:59)."),
          table([["Definición", "n (cons./tend.)", "Rango 09:30–10:00 (cons. / tend.)",
                  "Eficiencia (cons. / tend.)", "Movimiento grande (cons. / tend.)", "p"]] +
                [[name, f"{v['n_consol']} / {v['n_trend']}",
                  f"{num(v['or30_range_rel']['consol'] - 1)} / {num(v['or30_range_rel']['trend'] - 1)}",
                  f"{str(v['or30_er']['consol']).replace('.', ',')} / {str(v['or30_er']['trend']).replace('.', ',')}",
                  f"{pct(v['big30']['consol'][0])} / {pct(v['big30']['trend'][0])}", pv(v["big30"]["p"])]
                 for name, v in [("V1 eficiencia", pr["v1_er"]), ("V2 posición", pr["v2_pos"]),
                                 ("V3 estricta", pr["v3_strict"])]],
                [2.6 * cm, 2.4 * cm, 3.4 * cm, 2.8 * cm, 3.4 * cm, W - 14.6 * cm]),
          P(f"El \"movimiento grande\" ocurre en el {pct(pr['big30_base_pct'])} de todas las aperturas, haya "
            "consolidado o no el premarket. Lo que sí anticipa una apertura amplia es un premarket amplio "
            f"(correlación {str(pr['corr_pm_range_rel_or30_range_rel']).replace('.', ',')} entre ambos rangos "
            "relativos): la volatilidad se agrupa, sin relación con la forma del premarket. El 24/08/2026 fue "
            "un buen ejemplo, no una regla.", NOTE),
          P("Setup \"de pan con mantequilla\"", H2),
          P("Entre 09:30 y 12:00: si el precio rompe un extremo del premarket y una vela cierra de nuevo "
            "dentro, se entra al cierre; stop un tick más allá del extremo del barrido; objetivo en el "
            "extremo opuesto del premarket; salida a las 16:00 si no toca ninguno. Una operación por día."),
          table([["Grupo", "n", "Acierto", "R bruto", "R neto", "IC 95 % (neto)", "R:R mediano"]] +
                [[name, v["n"], pct(v["win_pct"]), num(v["R_gross"]), num(v["R_net"]), ci(v["R_net_ci"]),
                  str(v["planned_rr_median"]).replace(".", ",")]
                 for name, v in [("Todas", st), ("Premarket en tendencia", p1["setup_by_pm_state"]["tendencia"]),
                                 ("Premarket en consolidación", p1["setup_by_pm_state"]["consolidación"])]],
                [4.6 * cm, 1.4 * cm, 1.9 * cm, 1.9 * cm, 1.9 * cm, 3.0 * cm, W - 14.7 * cm]),
          Spacer(1, 4),
          table([["Año", "n", "R neto medio"]] +
                [[y, len(g), num(g.R_net.mean())] for y, g in t1.groupby("y")] +
                [["Largos", int((t1.side == "long").sum()), num(t1[t1.side == "long"].R_net.mean())],
                 ["Cortos", int((t1.side == "short").sum()), num(t1[t1.side == "short"].R_net.mean())]],
                [4.6 * cm, 2.0 * cm, 3.0 * cm]),
          P("Es el único resultado positivo del estudio y es estable desde 2024, pero el intervalo de "
            "confianza incluye el cero, el resultado depende de los cortos y se probaron varias "
            "variantes (riesgo de encontrar algo por azar). Merece validarse con datos del futuro NQ "
            "y fuera de muestra antes de darle valor.", NOTE)]

    # Pilar 2
    a = p2["all"]
    s += [PageBreak(), P("3. Pilar 2: el 50 % del hueco de apertura", H1),
          P(f"Hueco mediano: {pct(p2['gap_pct_median'], 2)} del precio (~{p2['gap_pts_median']:.0f} puntos). "
            "<b>Control:</b> un nivel a la misma distancia de la apertura pero en el lado contrario al hueco "
            "(\"espejo\"). Si el 50 % del hueco fuera un imán, debería alcanzarse más que el espejo."),
          Image(str(RES / "p2_ce_vs_mirror.png"), width=W, height=W * 3.3 / 7.5),
          table([["Tamaño del hueco", "n", "CE antes de 10:00", "Espejo antes de 10:00", "p",
                  "Cierre completo antes de 10:00", "CE en el día"]] +
                [[k, v["n"], pct(v["ce_by_10"][0]), pct(v["mirror_by_10"][0]), pv(v["p_paired"]),
                  pct(v["fill_by_10"][0]), pct(v["ce_by_16"][0])] for k, v in p2["by_size"].items()] +
                [["Todos", a["n"], pct(a["ce_by_10"][0]), pct(a["mirror_by_10"][0]), pv(a["p_paired"]),
                  pct(a["fill_by_10"][0]), pct(a["ce_by_16"][0])]],
                [2.8 * cm, 1.2 * cm, 2.6 * cm, 2.9 * cm, 1.4 * cm, 3.4 * cm, W - 14.3 * cm]),
          Spacer(1, 4),
          *bullets([f"El 70 % de ICT solo se cumple en huecos pequeños (< 0,25 %), y ahí el nivel espejo se "
                    "alcanza igual de a menudo: con un hueco pequeño, cualquier nivel cercano se toca.",
                    f"En el conjunto, el CE se alcanza antes de las 10:00 el {pct(a['ce_by_10'][0])} de los "
                    f"días ({pct(p2['by_type']['descuento']['ce_by_10'][0])} en huecos en descuento y "
                    f"{pct(p2['by_type']['premium']['ce_by_10'][0])} en premium). En el día completo, el "
                    f"{pct(a['ce_by_16'][0])}.",
                    "Conclusión: el CE es un objetivo razonable para huecos pequeños, pero no por una "
                    "atracción especial del hueco, sino porque está cerca."]),
          P("Proyecciones de \"desviación estándar\" (−1 del hueco)", H2),
          Image(str(RES / "p2_projections.png"), width=W, height=W * 3.0 / 7.5),
          P(f"Para {p2['projections']['n_gaps']} huecos ≥ 0,10 %, se midió dónde cae el máximo y el mínimo de "
            "la mañana en múltiplos del hueco. El nivel de ICT es 1,0. Si fuera especial, habría un pico "
            f"en 1,0; no lo hay: {pct(p2['projections']['near_1.0_pct'])} de los extremos a ±0,1 frente a "
            f"{pct(p2['projections']['controls_mean_pct'])} en niveles de control (0,6–1,4). A menos de "
            f"1 punto (\"al tick\"): {pct(p2['projections']['within_1pt_of_level_pct'], 2)}. El pico en 0 "
            "son los días en que la apertura fue el extremo de la mañana.", NOTE)]

    # Pilar 3
    s += [PageBreak(), P("4. Pilar 3: Silver Bullet (primer FVG de las 10:00)", H1),
          P("<b>Reglas.</b> Primer FVG de 1 minuto (≥ 1 tick) cuya vela central está entre las 10:00 y las "
            "10:58. Entrada con orden límite en su 50 % (CE) si el precio vuelve antes de las 11:00; stop un "
            "tick más allá de las dos primeras velas del patrón; objetivo en el extremo de corto plazo "
            "alcanzado entre la formación y el retorno (la liquidez que ICT señala); salida a las 16:00. "
            "<b>Control:</b> la misma regla en las horas de las 11, 12 y 13 (y las 14, el Silver Bullet de "
            "la tarde)."),
          Image(str(RES / "p3_by_window.png"), width=W, height=W * 3.2 / 7.5),
          table([["Ventana", "Días con FVG", "N.º op.", "Acierto", "R bruto", "R neto", "IC 95 %",
                  "Riesgo med. (pts)"]] +
                [[k, v["days_with_fvg"], v["returned_and_traded"], pct(v["stats"]["win_pct"]),
                  num(v["stats"]["R_gross"]), num(v["stats"]["R_net"]), ci(v["stats"]["R_net_ci"]),
                  str(v["stats"]["risk_pts_median"]).replace(".", ",")] for k, v in p3.items()],
                [3.6 * cm, 1.8 * cm, 1.9 * cm, 1.6 * cm, 1.6 * cm, 1.6 * cm, 2.6 * cm, W - 14.7 * cm]),
          Spacer(1, 4),
          *bullets([f"Casi todos los días aparece un FVG en la hora de las 10:00 y el precio vuelve a él en "
                    f"una mediana de {p3['10:00 (Silver Bullet)']['median_min_to_return']:.0f} minutos.",
                    "La operación está en torno a cero en todas las horas. Las 10:00 no se distinguen de "
                    "las 11:00 o las 13:00; solo las 12:00 (almuerzo) son claramente peores.",
                    "Esta es la versión mecánica. ICT filtra con contexto (lunch macro, FVG con "
                    "desplazamiento, draw on liquidity), pero en la parte 5 reconoce que esos filtros se "
                    "deciden caso a caso, así que no se pueden probar sin reglas escritas."])]

    # FVG clasificados
    G = fc["groups"]
    s += [PageBreak(), P("5. First presented, con desplazamiento y reflection", H1),
          P("En el vídeo <i>NQ Futures Review &amp; 1st Presented Reflection FVG</i> (8 de septiembre de 2026) "
            "Michael precisa tres PD arrays y afirma que un FVG con desplazamiento \"tiene mucha más "
            "importancia en el precio futuro\". Se midieron con sus definiciones:"),
          *bullets(["<b>First presented FVG (FP)</b>: el primer FVG de 1 minuto después de las 09:30.",
                    "<b>FP con desplazamiento (FPD)</b>: el primero cuyo tramo rompe un máximo (alcista) o "
                    "mínimo (bajista) previo; aquí, el último swing fractal desde las 07:00. Variante "
                    "estricta: romper el extremo de los 30 minutos anteriores.",
                    "<b>First presented reflection (FPR)</b>: el primer FVG de sentido contrario al FP. Según "
                    "él, es más fuerte si se forma en una macro (xx:50–xx:10).",
                    "<b>Control</b>: todos los demás FVG del día (09:30–15:00), con y sin desplazamiento. "
                    "Misma operación en todos: entrada en el CE si el precio vuelve en ≤ 60 minutos, stop "
                    "tras las dos primeras velas, objetivo en el extremo de corto plazo."]),
          Image(str(RES / "fvg_classes.png"), width=W, height=W * 3.4 / 7.5),
          table([["Grupo", "n", "Acierto", "R bruto", "R neto", "IC 95 % (neto)"]] +
                [[k, v["n"], pct(v["win_pct"]), num(v["R_gross"]), num(v["R_net"]), ci(v["R_net_ci"])]
                 for k, v in G.items()],
                [6.2 * cm, 1.6 * cm, 1.8 * cm, 1.8 * cm, 1.8 * cm, W - 13.2 * cm]),
          Spacer(1, 4),
          *bullets([f"En 1 minuto hay una mediana de {fc['fvgs_per_day_median']:.0f} FVG por sesión, y el "
                    f"{pct(fc['pct_with_displacement'])} cumple la condición de desplazamiento. Por eso el "
                    "FPD coincide con el FP la mayoría de los días (85 %) y se forma hacia las "
                    f"{fc['fpd_median_time'][:5]}; el FPR, hacia las {fc['fpr_median_time'][:5]}.",
                    "Ninguno de los tres se distingue del resto de FVG: todos rondan cero en bruto y quedan "
                    "negativos tras costes. La variante estricta del FPD da lo mismo (−0,10 R netos).",
                    "Entre los FVG de control, los que tienen desplazamiento aciertan algo <i>menos</i> que "
                    f"los que no (p = {pv(fc['p_disp_vs_nodisp_win'])}), al contrario de lo que afirma.",
                    "El FPR formado en una macro sale ligeramente mejor, pero con pocos casos y un intervalo "
                    "que incluye de sobra el cero.",
                    "No se midió su uso en días posteriores (p. ej., el FPR del viernes como resistencia el "
                    "martes): no hay una regla que diga cuándo deja de ser válido."]),
          P("Conclusión: con sus propias definiciones, ni el desplazamiento ni el \"reflection\" aportan "
            "información útil para operar el FVG. Encaja con lo visto en el Silver Bullet: el FVG de 1 "
            "minuto es un patrón muy frecuente y, por sí solo, no da ventaja.", BOX)]

    # Otras reglas
    s += [PageBreak(), P("6. Otras reglas: <i>Trading Premarket and Regular Session Liquidity</i> (18/09/2025)", H1),
          P("Tres reglas concretas de este vídeo, medidas en las mismas sesiones."),
          P("Lunch macro", H2),
          P("<b>Regla de ICT:</b> \"cuando el mercado es alcista, la lunch macro buscará la sell side… la "
            "primera liquidez destacada formada después de las 10:00\", a partir de las 11:30. "
            "<b>Medición:</b> día alcista = precio a las 11:29 por encima de la apertura de las 09:30. "
            "Liquidez = primer mínimo (máximo) fractal de 5 velas formado entre las 10:00 y las 11:29 y "
            "aún no tomado. ¿Se alcanza entre las 11:30 y las 13:00? <b>Control:</b> la liquidez del lado "
            "a favor del sesgo, a igual distancia (en días bajistas, lo simétrico)."),
          table([["Distancia al precio", "Contra el sesgo (n)", "Alcanzada", "A favor (n)", "Alcanzada", "p"]] +
                [[r["dist_pct"].replace("(", "").replace("]", "").replace(", ", "–").replace(".", ",") + " %",
                  r["n_counter"], pct(r["hit_counter"][0]), r["n_with"], pct(r["hit_with"][0]), pv(r["p"])]
                 for r in lm["counter_vs_with_by_distance"]],
                [3.6 * cm, 3.0 * cm, 2.2 * cm, 2.4 * cm, 2.2 * cm, W - 13.4 * cm]),
          P(f"En días alcistas, esa sell side se alcanza el {pct(lm['bull_days_ssl_hit'][0])} de las veces "
            f"(distancia mediana {pct(lm['bull_days_ssl_dist_median'], 2)}). Contra el sesgo se alcanza "
            "<i>menos</i> que a favor, no más.", NOTE),
          P("El jueves de las semanas alcistas", H2),
          P("<b>Regla:</b> en una semana alcista \"el máximo de la semana se forma el jueves, o es un máximo "
            "falso y el viernes lo rompe\". <b>Control:</b> las mismas semanas con el orden de sus cinco "
            f"días barajado 200 veces (mismos movimientos, otro orden). {th['up_weeks']} semanas alcistas "
            f"completas de {th['weeks']}."),
          table([["Día del máximo semanal", "Lun", "Mar", "Mié", "Jue", "Vie"],
                 ["Real"] + [pct(v, 0) for v in th["up_week_high_day_pct"].values()],
                 ["Días barajados"] + [pct(v, 0) for v in th["perm_high_day_pct"].values()]],
                [4.4 * cm] + [2.0 * cm] * 5),
          P(f"Si el jueves marca el máximo hasta ese momento, el viernes lo rompe el "
            f"{pct(th['fri_breaks_thu_given_thu_high'][0])} de las veces frente al "
            f"{pct(th['fri_breaks_thu_given_thu_high_perm_pct'])} con los días barajados. En una semana que "
            "termina al alza, el máximo cae casi siempre al final por pura aritmética.", NOTE),
          P("Barrido del premarket alrededor de las 08:30", H2),
          P("<b>Regla</b> (su operación de ese día): el precio rompe un extremo del rango 07:00–08:29 entre "
            "las 08:30 y las 09:29 y vuelve dentro; se entra al cierre de la vela, stop más allá del barrido, "
            "objetivo en el extremo opuesto, salida a las 12:00."),
          table([["Grupo", "n", "Acierto", "R bruto", "R neto", "IC 95 % (neto)", "R:R mediano"]] +
                [[k, v["n"], pct(v["win_pct"]), num(v["R_gross"]), num(v["R_net"]), ci(v["R_net_ci"]),
                  str(v["planned_rr_median"]).replace(".", ",")]
                 for k, v in [("Todas", pre["all"]), ("Largos", pre["long"]), ("Cortos", pre["short"])]],
                [3.0 * cm, 1.4 * cm, 1.9 * cm, 1.9 * cm, 1.9 * cm, 3.0 * cm, W - 13.1 * cm]),
          P("Rango pequeño, stop corto y objetivo lejano (R:R mediano de 6): casi siempre salta el stop. A "
            "diferencia del barrido del rango 07:00–09:00 tras la apertura (sección 2), aquí no hay "
            "resultado positivo.", NOTE)]

    # Conclusiones
    s += [P("7. Conclusiones y siguientes pasos", H1),
          *bullets(["<b>Las afirmaciones cuantitativas no se sostienen.</b> El 70 % del hueco, las "
                    "proyecciones \"al tick\", el poder de los niveles iguales, la ventaja horaria del "
                    "Silver Bullet, la importancia del FVG con desplazamiento o \"reflection\", la lunch macro, "
                    "el jueves de las semanas alcistas y la regla \"premarket en consolidación → gran "
                    "movimiento a las 09:30\" desaparecen al compararlos con un control. Encajan con lo que se "
                    "esperaría de la volatilidad normal y del sesgo retrospectivo (sección 11 del informe "
                    "de metodología).",
                    "<b>Lo que sí es útil:</b> los tres pilares son una forma ordenada de mirar el mercado "
                    "cada día, y las frecuencias de este estudio sirven como referencia realista (por "
                    "ejemplo, cuánto se suele alcanzar el CE según el tamaño del hueco).",
                    "<b>Candidato a investigar:</b> el barrido del premarket hacia el extremo opuesto "
                    f"({num(st['R_net'])} R netos). Siguiente paso: datos del futuro NQ, división "
                    "entrenamiento/prueba por fechas y no ajustar más parámetros sobre estos mismos datos.",
                    "Reproducible: <font face='DV'>python3 backtest/ict_pillars.py</font> regenera todos los "
                    "resultados en results/ict_pillars/ (descarga los datos de histdata.com la primera "
                    "vez)."])]

    doc = SimpleDocTemplate(str(OUT), pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm,
                            topMargin=1.8 * cm, bottomMargin=1.8 * cm, title="Los tres pilares de ICT, medidos",
                            author="drjimenez")

    def footer(c, doc_):
        c.saveState(); c.setFont("DV", 7.5); c.setFillColor(B.colors.HexColor("#777777"))
        c.drawString(2 * cm, 1.2 * cm, "Los tres pilares de ICT, medidos")
        c.drawRightString(A4[0] - 2 * cm, 1.2 * cm, f"Página {doc_.page}"); c.restoreState()

    doc.build(s, onFirstPage=lambda c, d_: None, onLaterPages=footer)
    print("OK", OUT)


if __name__ == "__main__":
    build()
