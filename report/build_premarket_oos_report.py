"""Genera report/ICT_Premarket_Setup_OOS.pdf a partir de results/premarket_oos/summary.json.

Requiere haber ejecutado antes:  python3 backtest/premarket_oos.py
"""
import json
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.platypus import Image, KeepTogether, PageBreak, SimpleDocTemplate, Spacer

import build_ict_methodology as B  # estilos y utilidades comunes (fuentes, tablas)

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "results" / "premarket_oos"
OUT = ROOT / "report" / "ICT_Premarket_Setup_OOS.pdf"
P, table, bullets = B.P, B.table, B.bullets
H1, H2, BODY, NOTE, BOX, TITLE, SUB = B.H1, B.H2, B.BODY, B.NOTE, B.BOX, B.TITLE, B.SUB
W = A4[0] - 4 * cm
MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]


def f(x, d=2):
    return "—" if x is None or x != x else f"{x:.{d}f}".replace(".", ",").replace("-", "−")


def sg(x, d=2):
    if x is None or x != x:
        return "—"
    if round(x, d) == 0:
        return "0" if d == 0 else f"{0:.{d}f}".replace(".", ",")
    return f"{x:+.{d}f}".replace(".", ",").replace("-", "−")


def pct(x, d=1):
    return f"{f(x, d)} %"


def ci(a, d=2):
    return f"[{sg(a[0], d)}; {sg(a[1], d)}]"


def pci(t, d=1):
    return f"{f(t[0], d)} % [{f(t[1], d)}–{f(t[2], d)}]"


def img(name, h):
    return Image(str(RES / name), width=W, height=h)


def build():
    S = json.loads((RES / "summary.json").read_text())
    o, i, d = S["oos"], S["is"], S["data"]
    oa = S["oos_all_sessions"]
    mc, mci = o["mc_6m"], i["mc_6m"]
    sub, isub = o["subgroups"], i["subgroups"]
    be = o["break_even"]
    blocks = o["blocks"]
    nb = len(blocks)
    s = []

    # ------------------------------------------------------------------ portada
    s += [Spacer(1, 4 * cm), P("Barrido del premarket: prueba fuera de muestra", TITLE),
          P("El setup de ICT \"barrido de un extremo del premarket → extremo opuesto\", con las reglas "
            "congeladas, evaluado en datos del Nasdaq 100 nunca usados en su desarrollo", SUB),
          Spacer(1, 1 * cm),
          P(f"Fuera de muestra: {d['first']} a {d['last']} ({o['sessions']} sesiones válidas, {o['n']} "
            f"operaciones) · Desarrollo: 2023-10-02 a 2026-11-06 ({i['sessions']} sesiones) · "
            "velas de 1 minuto, hora de Nueva York", SUB),
          Spacer(1, 3 * cm),
          P("<b>Aviso.</b> Estudio estadístico con fines educativos; no es asesoramiento financiero ni una "
            "recomendación de inversión. Los resultados son simulados sobre un CFD del Nasdaq 100 como "
            "aproximación del futuro NQ, con costes aproximados. Rentabilidades pasadas, reales o "
            "simuladas, no garantizan resultados futuros.", BOX), PageBreak()]

    # ------------------------------------------------------------------ resumen
    verdict_ok = o["R_net_ci"][0] > 0 and S["oos"]["blocks_ci_below0"] == 0
    s += [P("Resumen y veredicto", H1),
          P("En el periodo de desarrollo (oct. 2023 – nov. 2026) este setup fue el único de los estudiados "
            f"con un resultado ligeramente positivo: {sg(i['R_net'])} R netos por operación, con un "
            f"intervalo de confianza que incluía el cero. Como esas cifras se vieron mientras se "
            "construían las reglas, no prueban nada. Aquí se aplican <b>las mismas reglas, sin tocar "
            "ningún parámetro</b>, a enero 2021 – septiembre 2023, un periodo que no se había mirado."),
          P(("<b>Veredicto: rentabilidad DEMOSTRADA.</b> " if verdict_ok else
             "<b>Veredicto: NO se demuestra que sea rentable.</b> ") +
            f"Fuera de muestra el setup pierde {f(abs(o['R_net']))} R netos por operación "
            f"(IC 95 % {ci(o['R_net_ci'])}; bruto {sg(o['R_gross'])} R). "
            f"La probabilidad bootstrap de que la esperanza neta real sea positiva es del "
            f"{pct(100 * o['p_net_gt0'], 0)} (p unilateral frente a 0: {f(o['p_boot_one_sided'], 2)}). "
            f"Solo {S['oos']['blocks_positive']} de {nb} bloques semestrales terminan en positivo y "
            f"{S['oos']['blocks_ci_below0']} son negativos con intervalo entero por debajo de cero. "
            "El resultado del desarrollo no se replica: era, con toda probabilidad, ruido.", BOX),
          table([["Indicador", "Fuera de muestra (2021–2023)", "Desarrollo (2023–2026)"],
                 ["Operaciones / sesiones", f"{o['n']} / {o['sessions']}", f"{i['n']} / {i['sessions']}"],
                 ["Acierto (IC 95 % Wilson)", pci(o["win_pct"]), pci(i["win_pct"])],
                 ["R bruto medio [IC 95 %]", f"{sg(o['R_gross'])} {ci(o['R_gross_ci'])}", f"{sg(i['R_gross'])} {ci(i['R_gross_ci'])}"],
                 ["<b>R neto medio [IC 95 %]</b>", f"<b>{sg(o['R_net'])}</b> {ci(o['R_net_ci'])}", f"<b>{sg(i['R_net'])}</b> {ci(i['R_net_ci'])}"],
                 ["P(esperanza neta &gt; 0)", pct(100 * o["p_net_gt0"], 0), pct(100 * i["p_net_gt0"], 0)],
                 ["Objetivo alcanzado (extremo opuesto)", pci(o["tp_pct"]), pci(i["tp_pct"])],
                 ["Factor de beneficio neto", f(o["pf_net"]), f(i["pf_net"])],
                 ["R neto total / máx. drawdown", f"{sg(o['total_R_net'], 1)} / {f(o['max_dd_net'], 1)}",
                  f"{sg(i['total_R_net'], 1)} / {f(i['max_dd_net'], 1)}"],
                 ["P(acabar en positivo tras 6 meses)", pct(100 * mc["mes"]["p_positive"], 0), pct(100 * mci["mes"]["p_positive"], 0)],
                 ["R:R planificado mediano · riesgo mediano", f"{f(o['planned_rr_median'])} · {f(o['risk_pts_median'], 1)} pts",
                  f"{f(i['planned_rr_median'])} · {f(i['risk_pts_median'], 1)} pts"]],
                [5.6 * cm, (W - 5.6 * cm) / 2, (W - 5.6 * cm) / 2]),
          Spacer(1, 6),
          P("Las cifras del desarrollo se han recalculado con el mismo código y coinciden con las del "
            "estudio original (658 operaciones, 32,1 % de acierto, +0,13 R netos). Los intervalos son "
            "bootstrap con 20 000 remuestreos; P(acabar en positivo) usa bootstrap por meses.", NOTE),
          PageBreak()]

    # ------------------------------------------------------------------ reglas y datos
    tz = S["tz_check"]
    tz_rows = [["Año · régimen", "Días", "Salto 09:30", "Salto 08:30", "Salto 10:30", "Minutos más agitados"]]
    short = {"invierno EE. UU. y UE": "invierno", "verano EE. UU. y UE": "verano", "semanas desfasadas": "desfasadas"}
    for k, v in tz.items():
        y, rg = k.split(" · ")
        tz_rows.append([f"{y} · {short.get(rg, rg)}", v["days"], f"×{f(v['open_x_09'], 1)}", f"×{f(v['open_x_08'], 1)}",
                        f"×{f(v['open_x_10'], 1)}", ", ".join(v["top3"])])
    s += [P("1. Reglas congeladas y datos", H1),
          P("Las reglas son exactamente las de <font face='DV'>pillar1()</font> en "
            "<font face='DV'>backtest/ict_pillars.py</font>, llamada sin modificaciones:"),
          *bullets([
              "Sesión: día con vela de 09:30 y de 16:14 (hora de Nueva York). Rango del premarket: máximo y "
              "mínimo de 07:00–08:59. Estado: eficiencia |cierre − apertura| / rango ≥ 0,5 = "
              "\"tendencia\"; si no, \"consolidación\".",
              "Desde las 09:30 y antes de las 12:00: cuando el precio supera un extremo del premarket "
              "(barrido) y una vela de 1 minuto <b>cierra de vuelta dentro</b>, se entra a ese cierre.",
              "Largo tras barrer el mínimo: stop = mínimo desde las 09:30 − 1 tick (0,25); objetivo = máximo "
              "del premarket. Corto, simétrico. Solo la primera señal y una operación al día; se descarta si "
              "el objetivo no queda más allá de la entrada.",
              "Salida en objetivo o stop (stop primero si ambos caen en la misma vela); si no, al cierre de "
              "las 15:59. R neto = R bruto − 1 punto / riesgo en puntos."]),
          P("Datos y control de calidad", H2),
          P("NSXUSD de histdata.com (CFD del Nasdaq 100, misma fuente que el desarrollo). Hay datos para "
            "todo el periodo pedido, pero <b>de finales de febrero a julio de 2023 el fichero de histdata "
            "tiene huecos masivos</b> (mediana de 240–300 de las 540 velas de 07:00–15:59). Antes de ver "
            "resultados se fijó un filtro de calidad de datos, no de reglas: sesión con ≥ 530 de 540 velas y "
            "mes con ≥ 10 sesiones así. Quedan "
            f"{d['sessions_kept']} de {d['sessions_raw']} sesiones; se excluyen los meses "
            f"{', '.join(d['months_dropped'])} y {d['sessions_incomplete']} sesiones sueltas incompletas. "
            "Sin el filtro (todas las sesiones que acepta el código congelado) el resultado es casi igual: "
            f"{oa['n']} operaciones, {sg(oa['R_net'])} R netos {ci(oa['R_net_ci'])}."),
          P("Verificación horaria", H2),
          P("histdata da las horas en UTC−5 más el horario de verano europeo; el cargador las convierte a "
            "Nueva York, pero solo se había validado para 2023-10 a 2025-06. Se comprobó para 2021–2023 "
            "midiendo la volatilidad media de cada minuto. Si el reloj estuviera desplazado una hora, la "
            "apertura de contado aparecería a las 08:30 o a las 10:30. \"Salto\" = |retorno| medio de "
            "hh:30–hh:34 dividido por el de hh:20–hh:29."),
          table(tz_rows, [3.4 * cm, 1.2 * cm, 1.9 * cm, 1.9 * cm, 1.9 * cm, W - 10.3 * cm]),
          Spacer(1, 4),
          P("El perfil completo minuto a minuto está en results/premarket_oos/tz_check.png. El salto de la apertura está a las 09:30 en todos los regímenes, también en las semanas de marzo "
            "y octubre-noviembre en que EE. UU. y Europa no coinciden (2021 y 2022); a las 10:30 no hay salto "
            "(×1,0). El pico de las 08:30 corresponde a los datos macro de EE. UU. <b>La alineación es "
            "correcta y no hizo falta corregir nada.</b> Las semanas desfasadas de 2023 caen en el tramo con "
            "huecos y quedan excluidas.", NOTE),
          PageBreak()]

    # ------------------------------------------------------------------ resultados OOS
    brow = [["Bloque", "n", "Acierto", "R bruto", "R neto [IC 95 %]", "PF neto", "R total", "Máx. DD"]]
    for b in blocks:
        brow.append([b["label"].replace("2023 (4 m)", "2023 (ene–feb, ago–sep)"), b["n"], pct(b["win_pct"][0]),
                     sg(b["R_gross"]), f"{sg(b['R_net'])} {ci(b['R_net_ci'])}", f(b["pf_net"]),
                     sg(b["total_R_net"], 1), f(b["max_dd_net"], 1)])
    for y, b in o["years"].items():
        brow.append([f"Año {y}", b["n"], pct(b["win_pct"][0]), sg(b["R_gross"]),
                     f"{sg(b['R_net'])} {ci(b['R_net_ci'])}", f(b["pf_net"]), sg(b["total_R_net"], 1),
                     f(b["max_dd_net"], 1)])
    brow.append(["<b>Total OOS</b>", o["n"], pct(o["win_pct"][0]), sg(o["R_gross"]),
                 f"<b>{sg(o['R_net'])}</b> {ci(o['R_net_ci'])}", f(o["pf_net"]), sg(o["total_R_net"], 1),
                 f(o["max_dd_net"], 1)])
    s += [P("2. Resultados fuera de muestra", H1),
          table(brow, [3.9 * cm, 1.0 * cm, 1.6 * cm, 1.6 * cm, 3.6 * cm, 1.5 * cm, 1.5 * cm, W - 14.7 * cm]),
          Spacer(1, 4),
          P(f"Salidas: {o['exits'].get('SL', 0)} en stop, {o['exits'].get('TP', 0)} en objetivo y "
            f"{o['exits'].get('EOD', 0)} al cierre. Racha perdedora más larga: {o['longest_losing']} "
            f"operaciones. Meses en positivo: {o['months_positive'][0]} de {o['months_positive'][1]}. "
            "Los bloques son semestres naturales consecutivos; 2023 solo tiene 4 meses con datos fiables y "
            "forma un único bloque.", NOTE),
          img("equity_oos.png", W * 3.2 / 7.6),
          P("Curva de capital en R (1 R = el riesgo de cada operación). Los saltos verticales son operaciones "
            "con stop muy corto y objetivo lejano (la mejor, el 2 de marzo de 2022, gana 34 R con un riesgo "
            "de 3,5 puntos).", NOTE)]
    # tabla mensual
    mrows = [["Año"] + MESES + ["Total"]]
    for y in sorted({k[:4] for k in o["monthly"]}):
        row, tot = [y], 0.0
        for mth in range(1, 13):
            key = f"{y}-{mth:02d}"
            if key in o["monthly"]:
                v = o["monthly"][key]
                tot += v
                row.append(sg(v, 0))
            else:
                row.append("·")
        row.append(f"<b>{sg(tot, 1)}</b>")
        mrows.append(row)
    s += [KeepTogether([P("R neto por mes", H2),
                        table(mrows, [1.3 * cm] + [(W - 2.8 * cm) / 12] * 12 + [1.5 * cm]),
                        P("«·» = mes sin datos fiables (excluido).", NOTE)]),
          PageBreak()]

    # ------------------------------------------------------------------ probabilidades
    tp, tpa, tps = o["tp_pct"], o["touched_target_any_pct"], o["tp_per_session_pct"]
    c = o["costs"]
    s += [P("3. Probabilidades: ¿se cumplen las afirmaciones?", H1),
          table([["Pregunta", "Fuera de muestra", "Lectura"],
                 ["Tras el barrido, ¿llega el precio al extremo opuesto antes que al stop? (operación ganada en objetivo)",
                  pci(tp), "Menos de 1 de cada 3 veces"],
                 ["¿Toca el extremo opuesto en algún momento antes de las 16:00, aunque antes salte el stop?",
                  pci(tpa), "La idea de ICT \"va al otro lado\" se cumple a menudo, pero tarde para el stop"],
                 ["Por sesión: ¿hay señal? / ¿hay señal y llega al objetivo?",
                  f"{pci(o['trade_freq_pct'])} / {pci(tps)}", "Una ganadora cada ~4 sesiones"],
                 ["P(esperanza neta real &gt; 0), bootstrap", pct(100 * o["p_net_gt0"], 1),
                  f"p unilateral = {f(o['p_boot_one_sided'], 2)}; t = {f(o['t_test'][0], 2)}"],
                 ["Acierto necesario para no perder (con el pago observado)",
                  f"{pct(be['R_net']['be_win_pct'])} neto · {pct(be['R_gross']['be_win_pct'])} bruto",
                  f"Real: {pct(be['R_net']['win_pct'])}. Ganancia media {f(be['R_net']['avg_win'])} R, pérdida media {f(be['R_net']['avg_loss'])} R"],
                 ["Sin las 3 mejores operaciones", f"{sg(o['outliers']['mean_excl_top3'])} R netos",
                  f"Mediana por operación {sg(o['outliers']['median_R_net'])} R; desarrollo sin top 3: {sg(i['outliers']['mean_excl_top3'])} R"]],
                [6.4 * cm, 3.6 * cm, W - 10.0 * cm]),
          P("Seis meses siguiendo el setup", H2),
          P("Se simuló 20 000 veces medio año de operativa con dos métodos: remuestreando operaciones "
            f"sueltas ({mc['iid']['trades_per_6m']} por semestre, la media observada) y remuestreando meses "
            "completos (conserva cuántas operaciones hubo y su agrupación)."),
          table([["Método", "P(total &gt; 0)", "Mediana", "Percentil 5", "Percentil 95", "P(DD peor que −10 R)", "P(DD peor que −20 R)"]] +
                [[nm, pct(100 * v["p_positive"], 0), sg(v["median"], 1), sg(v["p5"], 1), sg(v["p95"], 1),
                  pct(100 * v["p_dd_worse_10R"], 0), pct(100 * v["p_dd_worse_20R"], 0)]
                 for nm, v in [("OOS, por operaciones", mc["iid"]), ("OOS, por meses", mc["mes"]),
                               ("Desarrollo, por meses", mci["mes"])]],
                [3.6 * cm, 2.0 * cm, 1.8 * cm, 1.9 * cm, 1.9 * cm, (W - 11.2 * cm) / 2, (W - 11.2 * cm) / 2]),
          Spacer(1, 4),
          Image(str(RES / "mc_6m.png"), width=W * 0.85, height=W * 0.85 * 2.8 / 7.6),
          P("Incluso con los parámetros favorables del desarrollo, un drawdown de más de 10 R en seis meses es "
            "casi seguro: con ~105 operaciones de −1 R y un 30 % de acierto, las rachas de 8–13 pérdidas "
            "seguidas son normales.", NOTE),
          P("Costes y subgrupos", H2),
          table([["Coste ida y vuelta", "0 puntos", "0,5 puntos", "1 punto (base)", "2 puntos"],
                 ["R neto medio [IC 95 %]"] + [f"{sg(c[k]['R'])} {ci(c[k]['ci'])}" for k in ("0.0", "0.5", "1.0", "2.0")],
                 ["P(esperanza &gt; 0)"] + [pct(100 * c[k]["p_gt0"], 0) for k in ("0.0", "0.5", "1.0", "2.0")]],
                [3.6 * cm] + [(W - 3.6 * cm) / 4] * 4),
          Spacer(1, 6),
          table([["Subgrupo", "n OOS", "R neto OOS [IC 95 %]", "n IS", "R neto desarrollo (IS) [IC 95 %]", "¿Se replica?"]] +
                [[nm, sub[k]["n"], f"{sg(sub[k]['R_net'])} {ci(sub[k]['R_net_ci'])}", isub[k]["n"],
                  f"{sg(isub[k]['R_net'])} {ci(isub[k]['R_net_ci'])}", rep]
                 for nm, k, rep in [("Largos", "long", "Sí: siguen sin ventaja"),
                                    ("Cortos", "short", "No: la ventaja desaparece"),
                                    ("Premarket en tendencia", "tendencia", "No: la ventaja desaparece"),
                                    ("Premarket en consolidación", "consolidación", "Sí: siguen sin ventaja")]],
                [3.6 * cm, 1.3 * cm, 3.6 * cm, 1.2 * cm, 3.8 * cm, W - 13.5 * cm]),
          P(f"Diferencias OOS (permutación, bilateral): cortos frente a largos p = {f(sub['p_short_vs_long'], 2)}; "
            f"tendencia frente a consolidación p = {f(sub['p_trend_vs_consol'], 2)}. Son comparaciones "
            "descriptivas elegidas después de ver el desarrollo (comparaciones múltiples): con corrección de "
            "Bonferroni para 2 pruebas haría falta p &lt; 0,025. Ninguna es significativa. El patrón del "
            "desarrollo (cortos y \"tendencia\" mejores) se mantiene en el signo de la diferencia, pero ambos "
            "grupos pierden dinero fuera de muestra.", NOTE)]

    # ------------------------------------------------------------------ comparación
    def row(nm, a, b):
        return [nm, a, b]
    s += [P("4. Desarrollo frente a fuera de muestra", H1),
          Image(str(RES / "blocks.png"), width=W * 0.8, height=W * 0.8 * 3.0 / 7.6),
          P(f"R neto medio por semestre con IC 95 %. Fuera de muestra: {S['oos']['blocks_positive']} de {nb} "
            f"bloques positivos. En el desarrollo: {sum(b['R_net'] > 0 for b in i['blocks'])} de "
            f"{len(i['blocks'])}. Ningún semestre, en ninguno de los dos periodos, tiene el intervalo entero "
            "por encima de cero.", NOTE),
          Image(str(RES / "equity_oos_is.png"), width=W * 0.72, height=W * 0.72 * 2.8 / 7.6),
          table([["", "Fuera de muestra", "Desarrollo", "2021–2026 juntos"],
                 ["Operaciones", o["n"], i["n"], S["all_2021_2026"]["n"]],
                 ["R bruto", sg(o["R_gross"]), sg(i["R_gross"]), sg(S["all_2021_2026"]["R_gross"])],
                 ["R neto [IC 95 %]", f"{sg(o['R_net'])} {ci(o['R_net_ci'])}", f"{sg(i['R_net'])} {ci(i['R_net_ci'])}",
                  f"{sg(S['all_2021_2026']['R_net'])} {ci(S['all_2021_2026']['R_net_ci'])}"],
                 ["P(esperanza &gt; 0)", pct(100 * o["p_net_gt0"], 0), pct(100 * i["p_net_gt0"], 0),
                  pct(100 * S["all_2021_2026"]["p_net_gt0"], 0)],
                 ["Factor de beneficio neto", f(o["pf_net"]), f(i["pf_net"]), f(S["all_2021_2026"]["pf_net"])]],
                [4.2 * cm, (W - 4.2 * cm) / 3, (W - 4.2 * cm) / 3, (W - 4.2 * cm) / 3]),
          P("Con los cinco años y medio juntos, la esperanza neta es prácticamente cero: lo esperable de una "
            "regla sin ventaja con un coste pequeño. El buen resultado del desarrollo cae dentro de la "
            "variación normal entre periodos de tres años.", NOTE),
          PageBreak()]

    # ------------------------------------------------------------------ conclusiones
    v = S["oos"]["variants"]
    s += [P("5. Conclusiones", H1),
          *bullets([
              f"<b>No es rentable de forma demostrable.</b> Fuera de muestra pierde {f(abs(o['R_net']))} R netos por "
              f"operación (IC {ci(o['R_net_ci'])}), incluso en bruto es negativo, y falla los dos criterios "
              "fijados: el intervalo no excluye el cero (está casi entero por debajo) y los bloques no son "
              "consistentes.",
              f"<b>La afirmación de ICT, medida:</b> tras barrer un extremo del premarket, el precio llega al "
              f"extremo opuesto antes que al stop solo el {pct(tp[0], 0)} de las veces; en algún momento del día, "
              f"el {pct(tpa[0], 0)}. Con un R:R de ~2,4 hace falta un {pct(be['R_net']['be_win_pct'], 0)} de "
              "acierto para cubrir costes; el setup se queda por debajo.",
              f"<b>Probabilidades para quien lo siga:</b> P(esperanza &gt; 0) ≈ {pct(100 * o['p_net_gt0'], 0)}; "
              f"P(terminar en positivo tras 6 meses) ≈ {pct(100 * mc['mes']['p_positive'], 0)}; resultado "
              f"mediano a 6 meses {sg(mc['mes']['median'], 0)} R; drawdown de más de 10 R casi seguro.",
              "<b>Los subgrupos prometedores (cortos, premarket en tendencia) no se sostienen</b>: eran "
              "hallazgos del mismo periodo en que se buscaron.",
              "El resultado depende mucho de pocas operaciones con stop de muy pocos puntos y objetivos "
              "de 10–35 R; en ejecución real esas son precisamente las más sensibles al deslizamiento."]),
          P("Revisión del código congelado", H2),
          *bullets([
              "No se ha encontrado ningún error que cambie el resultado. Una re-simulación independiente de las "
              "salidas reproduce el simulador congelado operación por operación.",
              f"Velas ambiguas (stop y objetivo en la misma vela): {v['ambiguous_bars']} fuera de muestra; resolverlas "
              f"a favor del objetivo da {sg(v['target_first']['R_net'])} R. Stops con hueco (vela que abre más allá "
              f"del stop): {v['stop_gaps']}; ejecutarlos a la apertura da {sg(v['gap_fill']['R_net'])} R.",
              "Punto débil de datos: el código acepta sesiones con huecos (basta con 100 de 120 velas de premarket "
              "y 120 de 150 de mañana). Con los huecos de histdata de 2023 eso deja pasar días incompletos; por eso "
              "se añadió el filtro de calidad, que apenas cambia el resultado.",
              "Matiz de diseño (no es un error): el stop es el mínimo/máximo desde las 09:30, no el del barrido; si "
              "la sesión abre ya fuera del rango, el stop puede quedar lejos."]),
          P("Limitaciones", H2),
          *bullets([
              "CFD del Nasdaq 100 (histdata) como aproximación del futuro NQ: precios, horas sin negociación y "
              "velas pueden diferir ligeramente del futuro.",
              "Costes aproximados (1 punto ida y vuelta), sin modelo de deslizamiento en stops ni en entradas a "
              "mercado; los stops de pocos puntos son especialmente optimistas.",
              "Velas de 1 minuto: no se conoce el orden real de máximo y mínimo dentro de la vela (se asume stop "
              "primero), y la ejecución a cierre de vela supone liquidez inmediata.",
              "Fuera de muestra = 28 meses (2021, 2022 y 4 meses de 2023), un régimen distinto (mercado bajista de "
              "2022). Un solo periodo de prueba no descarta que la regla funcione en otro régimen, pero sí que "
              "su ventaja sea fiable.",
              "Reproducible: <font face='DV'>python3 backtest/premarket_oos.py</font> y "
              "<font face='DV'>python3 report/build_premarket_oos_report.py</font>."])]

    doc = SimpleDocTemplate(str(OUT), pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm,
                            topMargin=1.8 * cm, bottomMargin=1.8 * cm,
                            title="Barrido del premarket: prueba fuera de muestra", author="drjimenez")

    def footer(c, doc_):
        c.saveState(); c.setFont("DV", 7.5); c.setFillColor(B.colors.HexColor("#777777"))
        c.drawString(2 * cm, 1.2 * cm, "Barrido del premarket (ICT): prueba fuera de muestra")
        c.drawRightString(A4[0] - 2 * cm, 1.2 * cm, f"Página {doc_.page}"); c.restoreState()

    doc.build(s, onFirstPage=lambda c, d_: None, onLaterPages=footer)
    print("OK", OUT)


if __name__ == "__main__":
    build()
