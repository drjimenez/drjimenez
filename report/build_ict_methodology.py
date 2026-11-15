"""Genera report/ICT_Metodologia_Michael_Huddleston.pdf.

Informe de lectura sobre cómo analiza un gráfico Michael J. Huddleston (ICT)
según el material público de su canal de YouTube. Incluye un esquema
ilustrativo (velas sintéticas) del modelo de entrada.
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (Image, KeepTogether, PageBreak, Paragraph,
                                SimpleDocTemplate, Spacer, Table, TableStyle)

HERE = Path(__file__).resolve().parent
FIGS = HERE / "figs"
OUT = HERE / "ICT_Metodologia_Michael_Huddleston.pdf"

FONT_DIR = Path("/usr/share/fonts/truetype/dejavu")
pdfmetrics.registerFont(TTFont("DV", str(FONT_DIR / "DejaVuSans.ttf")))
pdfmetrics.registerFont(TTFont("DV-B", str(FONT_DIR / "DejaVuSans-Bold.ttf")))
_obl = FONT_DIR / "DejaVuSans-Oblique.ttf"
pdfmetrics.registerFont(TTFont("DV-I", str(_obl if _obl.exists() else FONT_DIR / "DejaVuSans.ttf")))
pdfmetrics.registerFontFamily("DV", normal="DV", bold="DV-B", italic="DV-I", boldItalic="DV-B")

ACCENT = colors.HexColor("#1f4e79")
SOFT = colors.HexColor("#eef3f8")
GRID = colors.HexColor("#b8c7d6")

ss = getSampleStyleSheet()
H1 = ParagraphStyle("H1", parent=ss["Heading1"], fontName="DV-B", fontSize=16, textColor=ACCENT,
                    spaceBefore=10, spaceAfter=8)
H2 = ParagraphStyle("H2", parent=ss["Heading2"], fontName="DV-B", fontSize=12.5, textColor=ACCENT,
                    spaceBefore=8, spaceAfter=5)
BODY = ParagraphStyle("B", parent=ss["BodyText"], fontName="DV", fontSize=9.6, leading=13.6,
                      spaceAfter=5)
BUL = ParagraphStyle("BUL", parent=BODY, leftIndent=14, bulletIndent=4, spaceAfter=2.5)
CELL = ParagraphStyle("C", parent=BODY, fontSize=8.4, leading=11, spaceAfter=0)
CELLB = ParagraphStyle("CB", parent=CELL, fontName="DV-B")
NOTE = ParagraphStyle("N", parent=BODY, fontSize=8.6, leading=12, textColor=colors.HexColor("#444444"))
BOX = ParagraphStyle("BOX", parent=BODY, backColor=SOFT, borderColor=GRID, borderWidth=0.6,
                     borderPadding=7, spaceBefore=6, spaceAfter=10)
TITLE = ParagraphStyle("T", parent=H1, fontSize=24, leading=30, alignment=TA_CENTER, spaceAfter=10)
SUB = ParagraphStyle("S", parent=BODY, fontSize=12, alignment=TA_CENTER, textColor=colors.HexColor("#333333"))


def P(t, s=BODY):
    return Paragraph(t, s)


def bullets(items):
    return [Paragraph(i, BUL, bulletText="•") for i in items]


def table(rows, widths, header=True):
    data = [[Paragraph(str(c), CELLB if (header and r == 0) or c_i == 0 else CELL)
             for c_i, c in enumerate(row)] for r, row in enumerate(rows)]
    t = Table(data, colWidths=widths, repeatRows=1 if header else 0)
    st = [("GRID", (0, 0), (-1, -1), 0.4, GRID),
          ("VALIGN", (0, 0), (-1, -1), "TOP"),
          ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4),
          ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]
    if header:
        st += [("BACKGROUND", (0, 0), (-1, 0), SOFT)]
    t.setStyle(TableStyle(st))
    return t


# --------------------------------------------------------------------------
# Figuras
# --------------------------------------------------------------------------
def candles(ax, ohlc, x0=0, w=0.6):
    for i, (o, h, l, c) in enumerate(ohlc):
        x = x0 + i
        col = "#2e7d32" if c >= o else "#c62828"
        ax.plot([x, x], [l, h], color="#333333", lw=0.9, zorder=2)
        ax.add_patch(Rectangle((x - w / 2, min(o, c)), w, max(abs(c - o), 0.04),
                               facecolor=col, edgecolor="#333333", lw=0.6, zorder=3))


def fig_model():
    # Escenario largo: rango asiático, Judas swing bajo SSL, desplazamiento + MSS con FVG,
    # retroceso al FVG (entrada), expansión hacia BSL.
    o = [
        (10.0, 10.4, 9.8, 10.2), (10.2, 10.5, 10.0, 10.1), (10.1, 10.3, 9.7, 9.9),
        (9.9, 10.2, 9.7, 10.1), (10.1, 10.6, 10.0, 10.4), (10.4, 10.5, 9.9, 10.0),  # rango
        (10.0, 10.1, 9.4, 9.5), (9.5, 9.6, 9.1, 9.25),                             # barrido SSL
        (9.25, 9.9, 9.2, 9.85), (9.85, 10.9, 9.8, 10.8), (10.8, 11.1, 10.35, 10.95),  # desplazamiento
        (10.95, 11.0, 10.5, 10.6), (10.6, 10.7, 10.15, 10.3),                        # retroceso al FVG
        (10.3, 10.9, 10.25, 10.85), (10.85, 11.4, 10.8, 11.3), (11.3, 11.9, 11.2, 11.8),
        (11.8, 12.1, 11.6, 11.7),
    ]
    fig, ax = plt.subplots(figsize=(9.2, 4.6), dpi=170)
    candles(ax, o)
    # SSL / BSL
    ax.hlines(9.7, -0.5, 7.5, colors="#c62828", linestyles="--", lw=1)
    ax.text(-0.4, 9.58, "SSL: mínimos iguales del rango", fontsize=7.5, color="#c62828")
    ax.hlines(10.6, -0.5, 16.5, colors="#2e7d32", linestyles="--", lw=1)
    ax.hlines(12.0, 9.5, 16.5, colors="#2e7d32", linestyles=":", lw=1)
    ax.text(9.6, 12.07, "Objetivo: BSL externo / draw on liquidity", fontsize=7.5, color="#2e7d32")
    ax.text(-0.4, 10.65, "Máximo del rango (BSL interno)", fontsize=7.5, color="#2e7d32")
    # FVG: entre high vela 8 (9.9) y low vela 10 (10.35)
    ax.add_patch(Rectangle((8.5, 9.9), 8.0, 0.45, facecolor="#1f77b4", alpha=0.15, zorder=1))
    ax.text(13.6, 10.0, "FVG (BISI)", fontsize=7.5, color="#1f4e79")
    # MSS: rompe el swing high 10.6 (vela 4)
    ax.annotate("MSS con desplazamiento", xy=(9, 10.62), xytext=(5.0, 11.4), fontsize=7.5,
                arrowprops=dict(arrowstyle="->", lw=0.8))
    ax.annotate("Judas swing:\nbarrido de SSL", xy=(7, 9.1), xytext=(3.3, 8.85), fontsize=7.5,
                arrowprops=dict(arrowstyle="->", lw=0.8))
    ax.annotate("Entrada en el FVG", xy=(12, 10.2), xytext=(13.2, 9.45), fontsize=7.5,
                arrowprops=dict(arrowstyle="->", lw=0.8))
    ax.hlines(9.05, 6.5, 13.5, colors="#555555", linestyles="-.", lw=0.9)
    ax.text(8.6, 8.88, "Stop bajo el mínimo del barrido", fontsize=7.5, color="#555555")
    for x0, x1, lab in [(-0.5, 5.5, "Acumulación"), (5.5, 7.5, "Manipulación"), (7.5, 16.5, "Distribución")]:
        ax.axvspan(x0, x1, ymin=0.965, ymax=1.0, color="#dde6ef")
        ax.text((x0 + x1) / 2, 12.33, lab, ha="center", fontsize=7.5, color="#1f4e79")
    ax.set_xlim(-0.6, 16.6)
    ax.set_ylim(8.7, 12.45)
    ax.set_xticks([]); ax.set_yticks([])
    for s in ax.spines.values():
        s.set_color("#bbbbbb")
    ax.set_title("Esquema ilustrativo del modelo de entrada de ICT (escenario largo)", fontsize=10)
    fig.tight_layout()
    p = FIGS / "ict_entry_model.png"
    fig.savefig(p); plt.close(fig)
    return p


def fig_pd():
    fig, ax = plt.subplots(figsize=(9.2, 3.0), dpi=170)
    lo, hi = 0, 100
    ax.axhspan(50, 100, color="#c62828", alpha=0.08)
    ax.axhspan(0, 50, color="#2e7d32", alpha=0.08)
    ax.axhspan(62, 79, xmin=0.55, xmax=0.95, color="#1f77b4", alpha=0.18)
    for lvl, lab in [(100, "Máximo del rango (BSL)"), (50, "Equilibrio 50 %"), (0, "Mínimo del rango (SSL)")]:
        ax.axhline(lvl, color="#333333", lw=0.9, ls="--" if lvl == 50 else "-")
        ax.text(1, lvl + 2, lab, fontsize=8)
    ax.text(1, 75, "PREMIUM: zona de ventas", fontsize=9, color="#c62828")
    ax.text(1, 22, "DESCUENTO: zona de compras", fontsize=9, color="#2e7d32")
    ax.text(57, 70, "OTE para cortos: 62–79 % (70,5 %)", fontsize=8, color="#1f4e79")
    ax.set_xlim(0, 100); ax.set_ylim(lo - 5, hi + 8)
    ax.set_xticks([]); ax.set_yticks([])
    for s in ax.spines.values():
        s.set_color("#bbbbbb")
    ax.set_title("Dealing range: premium, descuento y OTE", fontsize=10)
    fig.tight_layout()
    p = FIGS / "ict_premium_discount.png"
    fig.savefig(p); plt.close(fig)
    return p


# --------------------------------------------------------------------------
# Documento
# --------------------------------------------------------------------------
def on_page(c, doc):
    c.saveState()
    c.setFont("DV", 7.5)
    c.setFillColor(colors.HexColor("#777777"))
    c.drawString(2 * cm, 1.2 * cm, "Metodología ICT: cómo analiza un gráfico Michael J. Huddleston")
    c.drawRightString(A4[0] - 2 * cm, 1.2 * cm, f"Página {doc.page}")
    c.restoreState()


def build():
    FIGS.mkdir(exist_ok=True)
    f_model, f_pd = fig_model(), fig_pd()
    W = A4[0] - 4 * cm
    s = []

    # Portada
    s += [Spacer(1, 4.5 * cm), P("Metodología ICT", TITLE),
          P("Cómo analiza un gráfico Michael J. Huddleston (The Inner Circle Trader): "
            "qué señales busca, qué patrón sigue y qué tiene en cuenta antes de operar", SUB),
          Spacer(1, 1.2 * cm),
          P("Informe de lectura basado en el contenido público del canal de YouTube "
            "@innercircletrader (mentoría 2022, series de lecciones y directos) y en resúmenes "
            "de terceros.", SUB),
          Spacer(1, 0.5 * cm), P("15 de noviembre de 2026", SUB),
          Spacer(1, 3 * cm),
          P("<b>Aviso.</b> Documento educativo. No es asesoramiento financiero. Los horarios, "
            "porcentajes y reglas son los que ICT enseña habitualmente; él mismo los matiza y cambia "
            "entre series, así que conviene contrastarlos con los vídeos originales. No hay un "
            "historial auditado que demuestre que el método sea rentable.", BOX),
          PageBreak()]

    # 0. Resumen
    s += [P("Resumen", H1),
          P("ICT parte de una idea central: el precio no se mueve al azar. Según él, lo reparte un "
            "algoritmo (lo llama <b>IPDA</b>, <i>Interbank Price Delivery Algorithm</i>) que hace dos "
            "cosas: <b>buscar liquidez</b> (las órdenes de stop por encima de máximos y por debajo de "
            "mínimos) y <b>rebalancear ineficiencias</b> (huecos de precio que dejan los movimientos "
            "rápidos). Todo su análisis consiste en responder, de arriba abajo, a tres preguntas:"),
          *bullets(["<b>¿Hacia dónde va el precio?</b> El <i>draw on liquidity</i>: el pool de "
                    "liquidez o la ineficiencia que actúa de imán en temporalidad alta.",
                    "<b>¿Desde dónde?</b> Una zona de precio en premium o en descuento, con un "
                    "<i>PD array</i> (FVG, order block, breaker…) en la que entrar.",
                    "<b>¿Cuándo?</b> Dentro de una <i>killzone</i> o ventana horaria (hora de Nueva "
                    "York), tras un barrido de liquidez y un cambio de estructura con desplazamiento."]),
          P("El patrón que repite en casi todos sus ejemplos es el mismo, a cualquier escala: "
            "<b>barrido de liquidez → desplazamiento con cambio de estructura (MSS) que deja un "
            "fair value gap → retroceso al FVG → expansión hacia la liquidez opuesta</b>. Es la "
            "secuencia de su <i>2022 Mentorship Model</i> y la versión intradía de su "
            "<i>Power of Three</i> (acumulación, manipulación, distribución)."),
          P("En su lección en directo del 31 de agosto de 2026 (sección 7) deja clara su prioridad: "
            "<b>primero mapear el draw on liquidity sin entradas</b> (calendario económico, niveles "
            "mensuales y diarios, FVG diarios en octavos, huecos de apertura) y después leer cómo "
            "responde el precio en las macros horarias, gestionando cada operación con parciales y "
            "stop \"financiado\". En la parte 2 (sección 8), con un hueco enorme y una mañana de "
            "consolidación, busca un objetivo donde coinciden dos niveles y confirma cada paso con "
            "cierres sobre el 50 % de las mechas."),
          P("Es la misma lógica que mecaniza el modelo TTFM de este repositorio (sweep de C1 por C2 y "
            "CISD en temporalidad baja). Pero ICT añade capas de contexto (sesgo HTF, nivel de "
            "liquidez concreto, premium/descuento, hora, SMT) que el backtest no incluía. Eso explica "
            "en parte por qué el patrón aislado no mostró ventaja.", BOX)]

    # 1. Filosofía
    s += [P("1. Principios de fondo", H1),
          table([
              ["Principio", "Qué significa en la práctica"],
              ["Liquidez", "Por encima de cada máximo relevante hay órdenes de compra (stops de cortos y "
               "entradas en ruptura): <b>buy-side liquidity (BSL)</b>. Por debajo de cada mínimo, "
               "<b>sell-side liquidity (SSL)</b>. Los máximos y mínimos iguales "
               "(<i>equal highs/lows</i>, \"relative equal\") son los objetivos más evidentes."],
              ["Ineficiencias", "Un movimiento rápido deja zonas por las que el precio solo pasó en "
               "una dirección (FVG, volume imbalance, liquidity void). El precio tiende a volver a "
               "ellas para \"rebalancear\"."],
              ["Tiempo y precio", "\"Tiempo antes que precio\". Las mismas zonas funcionan o no según "
               "la hora: busca setups solo en ventanas concretas (killzones, Silver Bullet, macros)."],
              ["Fractalidad", "El mismo comportamiento se repite en mensual, semanal, diario e "
               "intradía. La HTF da la narrativa y la LTF solo afina la ejecución."],
              ["Liquidez interna ↔ externa", "El precio alterna entre tomar liquidez externa (máximos "
               "y mínimos del rango) y rebalancear liquidez interna (FVG dentro del rango). Si acaba "
               "de tomar una, lo esperable es que busque la otra."],
          ], [3.4 * cm, W - 3.4 * cm])]

    # 2. Proceso top-down
    s += [P("2. Cómo recorre un gráfico: de arriba abajo", H1),
          P("En sus revisiones de mercado (análisis de fin de semana y directos) sigue casi siempre "
            "este orden. Trabaja sobre todo con futuros de índices (ES, NQ) y también con EUR/USD, "
            "el índice del dólar (DXY), bonos y oro."),
          table([
              ["Temporalidad", "Qué busca", "Para qué"],
              ["Mensual / Semanal", "Máximos y mínimos antiguos, FVG y order blocks grandes, "
               "rangos de 20, 40 y 60 días (<i>IPDA data ranges</i>), cambios trimestrales.",
               "Definir el <b>draw on liquidity</b> de fondo y el sesgo semanal."],
              ["Diario", "Último swing tomado, PDH/PDL (máximo y mínimo del día anterior), FVG "
               "diarios sin rellenar, dealing range actual y su 50 %.",
               "Fijar el <b>sesgo diario</b>: ¿hoy es más probable que alcance un máximo o un "
               "mínimo antiguo?"],
              ["4H / 1H", "Estructura intermedia, PD arrays en premium o descuento respecto al "
               "rango, máximos y mínimos de sesiones anteriores.",
               "Localizar la <b>zona</b> donde esperar la reacción."],
              ["15m / 5m", "Barrido de liquidez de sesión y cambio de estructura con desplazamiento.",
               "<b>Confirmar</b> que el precio ha girado a favor del sesgo."],
              ["1m–3m", "FVG, order block o breaker que deja el desplazamiento.",
               "<b>Entrar</b> con un stop ajustado."],
          ], [2.6 * cm, 7.6 * cm, W - 10.2 * cm]),
          Spacer(1, 6),
          P("Insiste en que la temporalidad baja nunca contradice a la alta: si la narrativa diaria es "
            "alcista, en 5 minutos solo busca compras en descuento. Si no tiene claro el draw on "
            "liquidity, no opera."),
          P("Referencias de apertura", H2),
          *bullets(["<b>Midnight open</b> (00:00 de Nueva York), el \"verdadero\" inicio del día: si el "
                    "precio está por encima, para comprar busca descuento por debajo de ese nivel; si "
                    "está por debajo, para vender busca premium por encima.",
                    "<b>Apertura de las 08:30 y de las 09:30</b> en índices. Muchas manipulaciones "
                    "empiezan con las noticias de las 08:30.",
                    "<b>NWOG / NDOG</b> (<i>New Week / New Day Opening Gap</i>): el hueco entre el "
                    "cierre del viernes y la apertura del domingo, o entre el cierre y la reapertura "
                    "diaria. Los trata como niveles de referencia e imán."])]

    # 3. Conceptos / señales
    s += [PageBreak(), P("3. Las señales que busca: el vocabulario de ICT", H1),
          P("Llama <b>PD arrays</b> (<i>premium/discount arrays</i>) a las zonas de precio que usa para "
            "entrar o como objetivo. Estas son las que más repite:"),
          table([
              ["Señal", "Definición", "Uso"],
              ["Fair Value Gap (FVG)", "Patrón de 3 velas en el que las mechas de la 1ª y la 3ª no se "
               "solapan. Alcista = <b>BISI</b> (buy-side imbalance, sell-side inefficiency); "
               "bajista = <b>SIBI</b>.",
               "Su zona de entrada favorita tras un desplazamiento. El 50 % del FVG se llama "
               "<b>consequent encroachment (CE)</b>."],
              ["Inversion FVG", "FVG que el precio atraviesa con cierre en contra; cambia de papel.",
               "Soporte o resistencia tras un cambio de estructura."],
              ["Order Block (OB)", "Última vela de sentido contrario antes de un movimiento con "
               "desplazamiento (p. ej., última bajista antes de una subida fuerte).",
               "Zona de entrada. Lo más sensible es su apertura y su 50 % (<i>mean threshold</i>)."],
              ["Breaker block", "Order block que falla: el precio barre un swing y luego rompe la "
               "estructura en contra; el OB fallido se convierte en zona opuesta.",
               "Entrada tras un barrido + MSS. Breaker + FVG solapados = <b>Unicorn</b>."],
              ["Mitigation / Rejection block", "Variantes del OB sin barrido previo o basadas en las "
               "mechas de rechazo.", "Entradas secundarias."],
              ["Volume imbalance / Liquidity void", "Hueco entre cuerpos de velas consecutivas "
               "o tramo largo de velas en una sola dirección.", "Objetivos de rebalanceo e imanes."],
              ["Market Structure Shift (MSS)", "Ruptura de un swing de corto plazo con "
               "<b>desplazamiento</b> (velas grandes y decididas que dejan FVG). Solo vale si antes "
               "se tomó liquidez del lado contrario.", "Confirmación de giro."],
              ["Change in State of Delivery (CISD)", "Cierre más allá de la apertura de la serie de "
               "velas que produjo el barrido.", "Confirmación temprana (la que usa TTFM)."],
              ["SMT divergence", "Divergencia entre activos correlacionados (ES vs NQ, EUR/USD vs "
               "GBP/USD, o inversa con DXY): uno marca un máximo o mínimo nuevo y el otro no.",
               "Refuerza que el barrido es una trampa."],
              ["Premium / Descuento", "Dentro de un dealing range (de un mínimo a un máximo), por "
               "encima del 50 % es premium y por debajo es descuento.",
               "Compra solo en descuento y vende solo en premium."],
              ["OTE", "<i>Optimal Trade Entry</i>: retroceso de Fibonacci del 62–79 % del tramo que "
               "hizo el MSS; el nivel clave es el 70,5 %.", "Refina la entrada dentro del PD array."],
              ["Turtle Soup", "Barrido falso de un máximo o mínimo antiguo que se revierte.",
               "Entrada contra la ruptura."],
          ], [3.3 * cm, 7.5 * cm, W - 10.8 * cm]),
          Spacer(1, 8),
          Image(str(f_pd), width=W, height=W * 3.0 / 9.2)]

    # 4. Tiempo
    s += [PageBreak(), P("4. El factor tiempo", H1),
          P("Para ICT el cuándo pesa tanto como el dónde. Todas las horas están en <b>hora de Nueva "
            "York</b> (en invierno, CET − 6 h; en verano europeo, CEST − 6 h, salvo las semanas de "
            "desfase de cambio de hora)."),
          table([
              ["Ventana", "Horario (NY)", "Qué espera ver"],
              ["Asian killzone", "20:00 – 00:00", "Rango de consolidación (acumulación); sus extremos "
               "serán liquidez para Londres."],
              ["London open killzone", "02:00 – 05:00", "Judas swing: barrido de un extremo de Asia y "
               "giro. Suele fijar el máximo o mínimo del día en FX."],
              ["New York AM killzone", "07:00 – 10:00 (índices 08:30 – 11:00)", "Continuación o "
               "reversión de Londres; noticias de las 08:30, apertura de las 09:30."],
              ["London close", "10:00 – 12:00", "Retrocesos y toma de beneficios."],
              ["New York PM", "13:30 – 16:00", "Segunda oportunidad en índices."],
              ["Silver Bullet", "03–04, 10–11 y 14–15", "Primer FVG que aparece en la ventana, "
               "a favor del draw on liquidity."],
              ["Macros", "Cada hora, de xx:50 a xx:10 (08:50–09:10, 09:50–10:10…)", "Los últimos 10 "
               "minutos de una hora y los 10 primeros de la siguiente. No indican dirección: marcan "
               "cuándo el precio debería \"arrancar\" hacia lo que ya esperabas (ver sección 7)."],
          ], [3.6 * cm, 4.2 * cm, W - 7.8 * cm]),
          Spacer(1, 6),
          P("Power of Three (AMD)", H2),
          P("Cada vela, sea diaria, semanal o de sesión, tiene tres fases: <b>acumulación</b> cerca de "
            "la apertura, <b>manipulación</b> (un movimiento falso contra la dirección real que toma "
            "liquidez, el <i>Judas swing</i>) y <b>distribución</b> (la expansión real, que es la que "
            "quiere operar). En un día alcista espera que el precio baje primero por debajo de la "
            "apertura (formando la mecha inferior de la vela diaria) y luego cierre cerca del máximo."),
          P("Perfiles semanales", H2),
          P("Aplica la misma idea a la semana: en una semana alcista, el mínimo suele formarse entre "
            "lunes y miércoles (con frecuencia el martes), y el jueves y el viernes suelen traer la "
            "expansión o un giro. Evita operar el día de noticias de alto impacto como FOMC antes de "
            "que salgan y el viernes por la tarde.")]

    # 5. Patrón paso a paso
    s += [PageBreak(), P("5. El patrón que sigue: modelo de entrada paso a paso", H1),
          Image(str(f_model), width=W, height=W * 4.6 / 9.2),
          Spacer(1, 6),
          P("Esta es la secuencia de su <b>2022 Mentorship Model</b>, la que más enseña en abierto. "
            "El Silver Bullet, el Unicorn y el OTE son variaciones del mismo esqueleto:"),
          table([
              ["Paso", "Qué hace", "Detalle"],
              ["1. Sesgo y objetivo", "Determina el <b>draw on liquidity</b> en diario / 4H.",
               "¿Máximo o mínimo antiguo? ¿FVG HTF sin rellenar? Si no hay respuesta clara, no hay "
               "trade."],
              ["2. Dealing range", "Marca el rango vigente y su 50 %.",
               "Compras solo desde descuento y ventas solo desde premium."],
              ["3. Liquidez a vigilar", "Marca BSL y SSL cercanas: PDH/PDL, máximos y mínimos de "
               "Asia y Londres, equal highs/lows, NDOG/NWOG.",
               "Son a la vez la trampa que espera ver barrida y los objetivos."],
              ["4. Esperar la hora", "Solo mira el gráfico de ejecución dentro de una killzone o del "
               "Silver Bullet.", "Fuera de ventana, aunque haya patrón, lo descarta."],
              ["5. Barrido (manipulación)", "El precio toma la liquidez del lado <i>contrario</i> al "
               "sesgo.", "Mejor si hay <b>SMT</b> con el activo correlacionado."],
              ["6. Desplazamiento + MSS", "Movimiento enérgico que rompe el último swing de corto "
               "plazo y deja un <b>FVG</b>.",
               "Sin desplazamiento (velas pequeñas y solapadas) no lo considera válido."],
              ["7. Entrada", "Orden límite en el retroceso al FVG (o al OB, breaker u OTE).",
               "Variantes: borde del FVG, su 50 % (CE) o la zona OTE del tramo."],
              ["8. Stop", "Más allá del extremo del barrido o del swing que originó el MSS.",
               "Un stop más ajustado (sobre el FVG) solo cuando la entrada es muy precisa."],
              ["9. Objetivos", "Liquidez interna primero (siguiente FVG o swing), luego la externa "
               "(draw on liquidity).",
               "Cierres parciales; mueve el stop cuando el precio deja un nuevo FVG a favor."],
              ["10. Gestión", "Un setup bueno por sesión. Si sale bien, para.",
               "Lo resume con la idea de \"<i>one shot, one kill</i>\"."],
          ], [3.3 * cm, 5.6 * cm, W - 8.9 * cm])]

    # 6. Modelos con nombre
    s += [KeepTogether([P("6. Modelos con nombre propio", H1),
          table([
              ["Modelo", "Esencia"],
              ["2022 Mentorship Model", "Barrido de liquidez → MSS con desplazamiento → entrada en "
               "FVG → objetivo en la liquidez opuesta. Explicado con NQ/ES en 1–5 minutos."],
              ["Silver Bullet", "Primer FVG que se forma en las ventanas 03–04, 10–11 o 14–15 (NY), "
               "operado hacia el pool de liquidez más cercano. Buscar al menos unos puntos "
               "de recorrido (ICT suele pedir ≥ 5 pts en NQ/ES y ≥ 15 pips en FX)."],
              ["OTE", "Tras un MSS, entrada en el retroceso del 62–79 % (70,5 %), idealmente "
               "coincidiendo con un FVG u OB."],
              ["Unicorn", "Breaker block solapado con un FVG en la misma dirección."],
              ["Power of Three / Judas swing", "Movimiento falso inicial de la sesión contra el "
               "sesgo y luego la expansión real."],
              ["Market Maker Buy / Sell Model (MMXM)", "Estructura en \"escalera\": fase original de "
               "consolidación, tramo contra la tendencia futura con varios rangos, "
               "<i>smart money reversal</i> en un PD array HTF y vuelta simétrica. Es el marco "
               "para modelos de varios días o semanas."],
              ["Turtle Soup", "Barrido falso de un máximo o mínimo antiguo que se revierte."],
          ], [4.4 * cm, W - 4.4 * cm])]),
          ]

    # 7. Transcripción
    QUOTE = ParagraphStyle("Q", parent=BODY, fontName="DV-I", fontSize=8.8, leading=12.4,
                           leftIndent=14, rightIndent=10, textColor=colors.HexColor("#333333"),
                           borderColor=ACCENT, borderWidth=0, spaceBefore=2, spaceAfter=6)

    def Q(en, es):
        return [Paragraph(f"«{en}»", QUOTE),
                Paragraph(f"→ {es}", ParagraphStyle("Qes", parent=NOTE, leftIndent=14, spaceAfter=8))]

    s += [PageBreak(), P("7. En sus propias palabras: <i>How New Students Should Start, Part 1</i> (31/08/2026)", H1),
          P("Esta sección analiza la transcripción de una lección en directo sobre futuros del Nasdaq "
            "(NQ, contrato de septiembre de 2026): "
            "<i>How New Students Should Start, Part 1</i>. Michael se la explica a dos alumnos que "
            "empiezan, preparando la semana y luego leyendo el precio en tiempo real hasta pasada la "
            "apertura de las 09:30. Es muy útil porque muestra su proceso <b>antes</b> de que se "
            "conozca el resultado, no en una revisión a posteriori."),
          P("7.1 Preparación de la semana (sábado o domingo)", H2),
          *bullets(["<b>Calendario económico</b> (Forex Factory, filtrado por USD). Solo le importan "
                    "las noticias de impacto alto (rojo) y medio (naranja), y anota <b>a qué hora y qué "
                    "día</b> caen: son \"las grandes olas que interfieren con el reparto normal del "
                    "precio\".",
                    "<b>Semana de nóminas no agrícolas (NFP)</b>: el lunes es el día en que hay que "
                    "estar sentado buscando setup; el miércoles es seguro hasta las 11:00; un alumno "
                    "nuevo <b>no opera jueves ni viernes</b>, solo estudia. Desmiente que diga \"nunca "
                    "operes los lunes\": los demás lunes son \"a suerte\" según la experiencia.",
                    "<b>Noticia a las 10:00</b>: espera los primeros 30 minutos, deja salir el dato y "
                    "opera lo que queda \"en la estela\".",
                    "<b>Estacionalidad</b>: de septiembre a fin de año el precio se reparte \"mucho "
                    "más limpio\" por los motores económicos de las fiestas."]),
          *Q("Monday is pure price action… Every Monday of non-farm payroll is a day that you should be "
             "drilled in and trying to find a setup.",
             "El lunes es acción del precio pura. Cada lunes de la semana de NFP tienes que estar "
             "concentrado buscando un setup."),
          P("7.2 Cómo prepara el gráfico, paso a paso", H2),
          table([
              ["Paso", "Qué hace en la lección"],
              ["1. Mensual", "Marca máximo, mínimo y cierre del mes anterior (julio y agosto), con "
               "etiqueta en negro y negrita, a la derecha, <b>visibles en todas las temporalidades</b>. "
               "La apertura mensual no le importa: \"queda absorbida\" en el hueco de apertura semanal "
               "(NWOG)."],
              ["2. Diario: dónde estamos", "\"Primer asunto: dónde estamos respecto al rango más "
               "reciente\". Mide el equilibrio (50 %): en la mitad superior del rango de julio y "
               "ligeramente en descuento en el de agosto."],
              ["3. Liquidez", "El máximo mensual ya es buy-side liquidity, sin más etiquetas. Marca un "
               "mínimo aislado como \"sell-side liquidity\" en rojo."],
              ["4. Ineficiencias diarias", "Sombrea en gris un BISI diario (FVG alcista) y lo divide en "
               "<b>octavos</b> (0,125 = 29.451; 50 % = 29.211,25). Un SIBI con volume imbalance arriba y "
               "abajo lo llama <b>suspension block</b>: lo sombrea en rojo (premium) con líneas más "
               "gruesas por ser diario."],
              ["5. 1H → 15m → 5m → 1m", "Comprueba que todo se ve en cada temporalidad. Marca "
               "máximos iguales relativos barridos (viernes, 10:00), el <i>first presented FVG</i> del "
               "21 de agosto y liquidez menor con líneas cortas: azul = buy side, rojo = sell side, "
               "siempre los mismos colores."],
              ["6. Hueco de apertura (RTH)", "Línea morada en el cierre del viernes (\"settlement\"). "
               "A las 09:30 la renombra como máximo o mínimo del <b>opening range gap</b> según abra "
               "por debajo (hueco en descuento) o por encima (hueco en premium)."],
              ["7. Orden", "Usa varios <i>layouts</i>: uno de trabajo, otro solo con huecos NWOG/NDOG, "
               "otro con opening range gaps y otro con first presented FVGs, para no saturar el gráfico."],
          ], [3.4 * cm, W - 3.4 * cm]),
          Spacer(1, 6),
          *Q("What I'm fleshing out is how to arrive at draw on liquidity. Step by step… No entries "
             "required. This is the first part of what you're supposed to learn.",
             "Lo que estoy desarrollando es cómo llegar al draw on liquidity, paso a paso. No hacen "
             "falta entradas. Esto es lo primero que tienes que aprender."),
          P("7.3 Herramientas de lectura que usa en tiempo real", H2),
          table([
              ["Herramienta", "Cómo la usa"],
              ["Mechas al 50 % (consequent encroachment)", "\"Las mechas son marcadores de "
               "continuidad\". Divide cada mecha grande en dos: si va corto, quiere que los "
               "<b>cuerpos</b> cierren por debajo de la mitad. Un cierre por encima es motivo de "
               "preocupación (no de salida automática)."],
              ["Octantes y cuadrantes", "Los niveles en octavos de un FVG diario funcionan como "
               "objetivos y soportes intradía (el precio \"usa el octante superior\")."],
              ["Inversion FVG", "Un FVG bajista que el precio supera y luego respeta como soporte "
               "indica un posible mínimo de medio plazo. Si sigue actuando como resistencia, la "
               "tesis bajista sigue viva."],
              ["PD arrays anidados", "Un FVG encima del 50 % de una mecha: \"dos PD arrays juntos te "
               "dan información inmediata\"."],
              ["Immediate rebalance", "Vela que rellena el hueco en la siguiente sin dejar FVG. Lo "
               "llama <b>\"uno de mis PD arrays más fuertes… no hay nada mejor\"</b>."],
              ["Macros (xx:50–xx:10)", "No dan dirección; marcan cuándo debe \"animarse\" el precio. "
               "Si consolida dentro de la macro, espera el movimiento justo al terminar (algo que dice "
               "observar en los últimos años)."],
              ["Hueco de apertura", "<b>\"La mitad del hueco se rellena antes de las 10:00 el 70 % de "
               "las veces\"</b>. El cierre del hueco es \"valor justo en su sentido más puro\" y actúa "
               "de imán cerca de las 09:30."],
              ["Estructura", "Distingue máximos y mínimos de corto, medio y largo plazo. Los "
               "movimientos importantes nacen en mínimos o máximos de medio plazo dentro de una macro."],
          ], [4.0 * cm, W - 4.0 * cm]),
          P("7.4 La sesión, tal como la narró", H2),
          table([
              ["Hora (NY)", "Lo que dijo y lo que pasó"],
              ["Antes de las 08:30", "El precio rechaza el máximo del BISI diario y barre buy side "
               "menor. Hipótesis: corto desde un volume imbalance hacia el octante inferior del FVG "
               "diario (29.371) y luego hacia la sell side menor."],
              ["08:30–08:50", "Caída de 55–60 puntos. Toma un parcial en el <b>event horizon</b> "
               "(la mitad entre el nuevo mínimo y el nivel objetivo) y baja el stop justo encima del "
               "último máximo (29.412), asegurando unos 30 puntos."],
              ["08:50–09:10 (macro)", "El precio consolida en vez de bajar: \"eso es problemático\". "
               "Tras las 09:10 se anima al alza y salta el stop hipotético, con beneficio."],
              ["09:10–09:30", "Apertura en descuento: el cierre del viernes queda unos 47 puntos "
               "más arriba. Predice que la apertura buscará el cierre del hueco."],
              ["09:30", "\"Mirad cuánta energía… Boom. Hecho.\" El precio cierra el hueco en "
               "segundos y lo supera."],
              ["09:30–10:00", "Anticipa que bajarán a por los stops de los largos bajo el mínimo "
               "reciente; ocurre. Señala un corto en un inversion FVG con immediate rebalance, con "
               "stop un tick por encima del 50 % (mean threshold) de la vela alcista y objetivo en la "
               "sell side."],
          ], [3.0 * cm, W - 3.0 * cm]),
          P("7.5 Gestión de la operación según la lección", H2),
          *bullets(["<b>Parciales siempre</b>: con tres micros, saca uno en el event horizon; en "
                    "otros casos, el 50–65 % bajo el primer mínimo. \"Hay gente que dice que tomar "
                    "parciales es estúpido. Mira eso. ¿Es estúpido ahora?\"",
                    "<b>Financiar la operación</b>: tras el parcial, el stop baja sobre el último "
                    "máximo de corto plazo. Si salta, \"¿a quién le importa?\": ya cobraste. Así "
                    "\"no dependes de tener razón\".",
                    "<b>Tamaño</b>: si el stop correcto es demasiado grande, usa micros. Querer solo "
                    "contratos grandes es \"mentalidad de jugador\".",
                    "<b>Defensa</b>: si el precio hace lo que \"no debería\", no sale de golpe; "
                    "reduce o ajusta. Cuanto más se aleja el precio de la entrada, más se \"construye "
                    "la narrativa a favor\"."]),
          P("7.6 Cómo dice que hay que aprender", H2),
          *bullets(["Primero <b>tape reading</b> sin operar: mapear liquidez y draws, sin entradas.",
                    "Solo demo o papel; dice que no está autorizado para enseñar a operar con dinero "
                    "real. Las pruebas de cuentas fondeadas para principiantes son \"apostar\".",
                    "Grabar la pantalla con el gráfico de 1 minuto todo el día y revisar de 09:30 a "
                    "10:30 parando el vídeo: \"creo que va a hacer esto\", y comprobarlo.",
                    "En cada punto de inflexión de la lección, hacer captura, anotar qué se esperaba "
                    "y llevarlo al diario.",
                    "Paciencia y disciplina desde el principio: \"lo que empiezas haciendo al "
                    "principio tiende a quedarse contigo\"."]),
          P("7.7 Qué añade o corrige respecto a las secciones anteriores", H2),
          table([
              ["Tema", "Antes (fuentes secundarias)", "Según la lección"],
              ["Prioridad", "Modelo de entrada.", "Primero mapear el draw on liquidity; las entradas "
               "vienen después."],
              ["Stop", "Más allá del barrido.", "En la entrada por immediate rebalance: un tick por "
               "encima del 50 % de la vela; luego se baja tras el parcial."],
              ["Objetivos", "Liquidez interna y externa.", "Además: octantes del FVG diario, event "
               "horizon y cierre del hueco de apertura (70 % de medio hueco antes de las 10:00)."],
              ["Calendario", "Evitar noticias de alto impacto.", "Reglas por día de la semana de NFP; "
               "esperar 30 minutos tras la noticia de las 10:00."],
              ["Macros", "Ejemplos sueltos.", "Cada hora, xx:50–xx:10. Marcan el momento, no la "
               "dirección."],
              ["R:R", "Al menos 2:1.", "No lo menciona; prioriza parciales y stop financiado."],
          ], [2.6 * cm, 5.0 * cm, W - 7.6 * cm]),
          Spacer(1, 4),
          P("Nota: las citas son traducciones de la transcripción automática de YouTube, que contiene "
            "errores (por ejemplo, \"cibby\" = SIBI o BISI, \"germanine\" = germane). En un momento "
            "dice \"non-farm payroll Friday\" cuando por el contexto se refiere al lunes de la semana "
            "de NFP.", NOTE)]

    # 8. Parte 2
    s += [PageBreak(), P("8. <i>How New Students Should Start, Part 2</i> (01/09/2026): día de hueco "
                         "grande y consolidación", H1),
          P("Al día siguiente de la parte 1, Michael narra en directo la sesión de la mañana en NQ. El "
            "contexto es muy distinto: durante la noche el precio cayó unos <b>500 puntos</b> y la "
            "apertura de las 09:30 deja un <b>hueco en descuento de más de 400 puntos</b> respecto al "
            "cierre de la sesión regular anterior (29.511,5). Es martes de semana de NFP, con un dato "
            "ISM (impacto medio) a las 10:00. Como dice que hará con un alumno nuevo, todas las "
            "operaciones son <b>hipotéticas</b> (tape reading, sin demo), con contratos mini."),
          P("8.1 Su lectura antes y durante la apertura", H2),
          table([
              ["Idea", "Lo que dice"],
              ["Perfil de la sesión", "Tras una noche en tendencia fuerte, \"es razonable anticipar "
               "que la sesión de la mañana sea de <b>consolidación</b>\". Por eso busca un objetivo "
               "\"fácil de alcanzar\" (<i>low hanging fruit</i>) y no un gran recorrido."],
              ["Sesgo por el hueco", "Con un hueco tan grande prefiere los <b>largos</b>: es más "
               "probable que una compra dé \"una victoria sorpresa\" hacia el hueco que un corto "
               "buscando precios más bajos. \"Siempre hay que darle al menos un intento\" a entrar "
               "en el hueco; si te para el stop, \"suele anunciar un setup más fácil después\"."],
              ["Objetivo por confluencia", "<b>29.212</b>: coinciden el cuadrante inferior del FVG "
               "diario (la caja gris de la parte 1) y un nivel del hueco de apertura dividido con "
               "Fibonacci. \"Dos niveles alineados… es casi obvio que el precio irá ahí\". Por eso "
               "lo prefiere al 50 % del hueco en un día así."],
              ["First presented FVG", "El primer FVG que aparece tras las 09:30 de cada día. Usa el "
               "de hoy y los del lunes 24, el martes 25 y el miércoles 26 de agosto como zonas de "
               "entrada y como objetivos. En largos: \"ningún cuerpo en la mitad inferior\"; las "
               "mechas sí pueden entrar."],
              ["Confirmación por mecha", "Para seguir largo exige que un cuerpo cierre <b>por encima "
               "del 50 % de la mecha</b> (\"la línea discontinua\"), y que la mecha quede superada "
               "\"en esta vela o en la siguiente; si es en esta, es muy fuerte\"."],
              ["10:30", "\"En cuanto llegamos a las 10:30 ya hay un rango de 1 hora formado\" y "
               "\"los algoritmos empiezan a dispararse\": espera más velocidad. Si a esa hora el "
               "hueco sigue abierto, es más probable que siga así un tiempo."],
              ["Sesión regular vs. nocturna", "Un nivel tocado por la noche (Globex) gana "
               "importancia cuando la sesión regular (RTH) vuelve a él. \"Lo que vemos en ETH debería "
               "confirmarse también en RTH; si no, es solo algo que pasó por la noche\"."],
              ["Solo velas", "No usa order flow ni análisis \"dentro de la vela\": \"la vela te lo "
               "dice todo… apertura, máximo, mínimo, cierre y el tiempo en que se forma\"."],
          ], [3.6 * cm, W - 3.6 * cm]),
          P("8.2 Las operaciones que narró (hipotéticas)", H2),
          table([
              ["#", "Operación", "Resultado según él"],
              ["1", "Largo tras barrer el mínimo inicial, hacia la buy side y el hueco. Stop bajo el "
               "mínimo, subido enseguida para cubrir costes. Parcial en la buy side.",
               "Parcial y luego stop en 29.100. Cuenta unos 49 + 32,5 puntos."],
              ["2", "Nuevo largo en el FPFVG del lunes 24 antes del ISM de las 10:00.",
               "La mecha rechaza; stop subido. Sale cubriendo costes."],
              ["3", "Corto con cuatro minis, contra su sesgo largo.",
               "\"Me equivoco. Cierro.\" Pérdida de unos 20 puntos: \"parece que soy humano\"."],
              ["4", "Largo en el BISI con volume imbalance de un tick que queda abierto (\"institutional "
               "order flow entry drill\"), con dos minis más añadidos. Stop bajo el mínimo (~20 puntos).",
               "Parciales en 29.153,5 (+20), sobre los máximos iguales y en 29.212. El último contrato "
               "llega al octante del FPFVG del miércoles 26."],
              ["", "<b>Total declarado</b>", "Unos 125–130 puntos netos con una sola operación "
               "perdedora (cifras suyas, no verificadas; él mismo pierde la cuenta)."],
          ], [0.7 * cm, 9.0 * cm, W - 9.7 * cm]),
          P("8.3 Detalles técnicos nuevos", H2),
          *bullets(["<b>Order block</b> con su propia definición: una vela cuya apertura coincide con el "
                    "mínimo (29.116 exacto). \"Es un order block, no una zona de demanda\".",
                    "<b>Volume imbalance de un tick</b> (cierre 29.133,25 y apertura 29.133,50): si "
                    "el flujo sigue alcista, ese tramo debería quedar sin rellenar. Es lo que explica "
                    "la reacción del precio.",
                    "<b>Stop por retroceso proyectado</b> (lo llama tema avanzado): mide el último "
                    "retroceso. Si el precio vuelve a recorrer esa distancia hacia arriba, sube el stop "
                    "bajo el último mínimo, porque después suele venir un retroceso mayor.",
                    "<b>Entrega diferida</b>: el 50 % del hueco no se alcanzó antes de las 10:00 (la "
                    "regla del 70 %), y lo trata como algo que puede llegar más tarde o no llegar.",
                    "<b>Tamaño para aprender</b>: micro NQ = 2 $ por punto (0,50 $ por tick, 4 ticks "
                    "por punto); mini = 20 $ por punto. Recomienda llevar el registro primero en "
                    "micros."]),
          P("8.4 Actitud y aprendizaje", H2),
          *bullets(["En consolidación \"hay que ser muy ágil y muy indulgente con uno mismo\" si el "
                    "precio te zarandea. Un alumno nuevo debe vivir esa sensación mirando, para "
                    "reconocer el peligro de perseguir movimientos.",
                    "\"Ver no es suficiente\": hay que tener una libreta y anotar cada número que "
                    "dice (entradas, stops, parciales).",
                    "Ser parado al <i>break-even</i> después de cobrar un parcial \"no debe molestar\": "
                    "estar molesto entonces \"es tonto\".",
                    "Dice que intenta imitar los dos primeros meses de un alumno nuevo, pero que \"no "
                    "puede olvidar su experiencia\" (33 años)."]),
          P("8.5 Qué aporta respecto a la parte 1", H2),
          table([
              ["Tema", "Parte 1 (31/08)", "Parte 2 (01/09)"],
              ["Tipo de día", "Mapear niveles y leer una mañana tranquila.", "Hueco enorme tras una "
               "noche en tendencia; espera consolidación."],
              ["Objetivo", "Cierre del hueco y sell side.", "Confluencia de niveles (FVG diario + hueco) "
               "en lugar del 50 % del hueco."],
              ["Gatillo", "Inversion FVG, immediate rebalance.", "FPFVG de varios días, cierres sobre el "
               "50 % de la mecha, volume imbalance de un tick."],
              ["Gestión", "Parcial en el event horizon.", "Stop a costes enseguida, varios parciales, "
               "añadir posición y stop por retroceso proyectado."],
              ["Errores", "La primera hipótesis no se cumple.", "Una operación perdedora (el corto contra "
               "el sesgo) y varias salidas a costes."],
          ], [2.4 * cm, 5.6 * cm, W - 8.0 * cm]),
          Spacer(1, 4),
          P("Observación crítica: en una sola mañana entra cuatro veces, en las dos direcciones, con "
            "ajustes continuos del stop. Lo hace con 33 años de experiencia y narrando en directo; para "
            "un alumno nuevo es muy difícil de replicar. El resultado lo calcula él mismo sobre la marcha "
            "y no es verificable. Lo útil de la lección es el razonamiento (perfil de sesión, confluencia "
            "de niveles, confirmación por mecha), no la cifra de puntos.", BOX)]

    # 9. Checklist
    s += [PageBreak(), P("9. Lista de comprobación antes de operar", H1),
          P("Esta lista recoge los puntos que ICT verifica de forma explícita o implícita en sus "
            "revisiones. Si alguno falla, lo habitual es que no opere:"),
          table([
              ["#", "Pregunta", "Sí / No"],
              ["1", "¿Sé cuál es el draw on liquidity de hoy (y de la semana)?", ""],
              ["2", "¿El sesgo diario coincide con el semanal, o tengo una razón clara para operar "
               "un retroceso?", ""],
              ["3", "¿El precio está en descuento (para comprar) o en premium (para vender) del rango "
               "relevante?", ""],
              ["4", "¿Estoy dentro de una killzone, una ventana del Silver Bullet o una macro?", ""],
              ["5", "¿Se ha barrido liquidez del lado contrario (PDH/PDL, Asia, Londres, equal "
               "highs/lows)?", ""],
              ["6", "¿Hay SMT con el activo correlacionado?", ""],
              ["7", "¿El cambio de estructura se produjo con desplazamiento y dejó un FVG?", ""],
              ["8", "¿La entrada está en un PD array claro (FVG / OB / breaker / OTE)?", ""],
              ["9", "¿El stop está protegido detrás del barrido y el objetivo en liquidez visible, "
               "con R:R ≥ 2?", ""],
              ["10", "¿Revisé el calendario (rojo/naranja)? ¿Es jueves o viernes de semana de NFP? ¿Pasaron 30 min desde la noticia de las 10:00?", ""],
              ["11", "¿Tengo un plan de parciales (event horizon) y de cuándo bajar el stop?", ""],
              ["12", "¿Qué perfil espero hoy (tendencia o consolidación) tras la sesión nocturna?", ""],
              ["13", "¿Mi objetivo coincide con dos niveles a la vez (p. ej., FVG diario + nivel del hueco)?", ""],
              ["14", "¿Ya hice mi trade del día o alcancé mi objetivo semanal?", ""],
          ], [0.8 * cm, W - 2.8 * cm, 2.0 * cm]),
          Spacer(1, 8),
          P("10. Gestión del riesgo y psicología", H1),
          *bullets(["Arriesga poco por operación (habla de 1 % o menos y de reducirlo tras pérdidas).",
                    "Pocas operaciones: prefiere un setup de alta probabilidad a muchas entradas.",
                    "Cierres parciales en liquidez interna y protección del stop.",
                    "Diario de operaciones y práctica en demo antes de usar dinero real.",
                    "Paciencia: el \"no trade\" es una posición. Si el día no ofrece el modelo, no se "
                    "fuerza.",
                    "Advierte que su contenido en YouTube es gratuito y que no pide dinero ni gestiona "
                    "fondos de nadie: quien se presente como ICT pidiendo dinero es falso."])]

    # 11. Valoración
    s += [P("11. Valoración crítica", H1),
          P("Puntos fuertes", H2),
          *bullets(["Da un <b>marco coherente</b>: contexto HTF, zona, hora y gatillo, cada uno con un "
                    "papel claro. Obliga a pensar en dónde están los stops de los demás.",
                    "Pone el foco en la <b>gestión del riesgo</b> y en operar poco.",
                    "Varias piezas (barridos de máximos y mínimos de sesión, huecos que se rellenan, "
                    "estacionalidad intradía de la volatilidad) se pueden formalizar y probar."]),
          P("Puntos débiles", H2),
          *bullets(["<b>Mucha discreción</b>: qué swing cuenta, qué FVG es \"el bueno\", qué es "
                    "desplazamiento. Dos analistas pueden leer el mismo gráfico al revés.",
                    "<b>Revisiones a posteriori</b>: buena parte de los ejemplos se explica con el "
                    "gráfico ya completado, lo que favorece el sesgo retrospectivo. La lección del "
                    "31 de agosto es una excepción valiosa: anticipa el cierre del hueco y la caza de "
                    "stops antes de que ocurran, aunque su primera hipótesis (bajar al octante "
                    "inferior) no se cumplió y la gestionó con parcial y stop financiado.",
                    "<b>Estadísticas sin fuente</b>: el \"70 % de medio hueco antes de las 10:00\" "
                    "es comprobable y convendría medirlo con datos propios.",
                    "<b>Narrativa difícil de falsar</b>: la idea de un algoritmo interbancario no se "
                    "puede comprobar, y casi cualquier movimiento admite una explicación a "
                    "posteriori.",
                    "<b>Sin historial auditado</b> público de rentabilidad sostenida del método.",
                    "El backtest TTFM de este repositorio, que mecaniza el núcleo barrido + CISD, "
                    "no encontró ventaja neta: −0,65 R en intradía y −0,09 R en swing, con una "
                    "ventaja bruta de solo +0,13 R en swing. Los filtros de contexto de ICT "
                    "(draw on liquidity, premium/descuento, SMT, hora) son justo lo que faltaba "
                    "y lo siguiente que habría que probar."]),
          P("Cómo usar esto en la práctica", H2),
          P("Lo más útil es convertir cada punto de la lista de comprobación en una regla que se pueda "
            "probar: sesgo = cierre diario respecto al 50 % del rango de 20 días; liquidez = PDH/PDL "
            "y extremos de Asia y Londres; ventana = killzone en hora de Nueva York; entrada = FVG "
            "tras un MSS. Después, medir cada filtro por separado con datos reales del subyacente y "
            "un análisis <i>walk-forward</i>. Así se separa lo que aporta ventaja de lo que solo es "
            "narrativa.", BOX)]

    # Fuentes
    s += [P("Fuentes y método", H1),
          P("No se han podido ver los vídeos directamente. La parte general del informe combina el contenido público del "
            "canal tal como lo recogen notas y resúmenes, y búsquedas web del 15 de noviembre de 2026. "
            "Las páginas de resúmenes de vídeos no se pudieron abrir desde el entorno de trabajo. "
            "Las secciones 7 y 8 se basan en las transcripciones automáticas de las lecciones del 31/08 y el 01/09/2026 "
            "aportadas por el lector. Fuentes consultadas:", NOTE),
          *[Paragraph(x, ParagraphStyle("src", parent=NOTE, leftIndent=12, bulletIndent=2),
                      bulletText="–") for x in [
              "Canal de YouTube: youtube.com/@innercircletrader (mentoría 2022, 2025 Lecture Series, "
              "2026 Smart Money Concepts Lectures, ICT Price Action Chronicles).",
              "A+ ICT Entry Checklist: videohighlight.com/v/lpam8F-N3EM",
              "Notas de la mentoría 2022: scribd.com/document/665909504/2022-ICT-Mentorship y "
              "scribd.com/document/686138475/ICT-Notes",
              "ICT Mentorship Month 8: ictmonth8.blogspot.com/2025/07/ict-mentorship-month-8-high-probability.html",
              "Silver Bullet: luxalgo.com/blog/ict-silver-bullet-setup-trading-methods/ y "
              "chartinglens.com/blog/ict-silver-bullet-strategy",
              "Power of Three: mql5.com/en/blogs/post/771729 y "
              "crttrader.blogspot.com/2025/08/ict-amd-po3-method-explained.html",
              "Lecciones 2026 (títulos): recapio.com/digest/ict-2026-smart-money-concepts-lecture-"
              "january-13-2026-by-the-inner-circle-trader y …-february-23-2026-…",
              "Archivo de Twitter Spaces: audioscrape.com/podcast/the-inner-circle-trader-twitter-spaces-archive",
              "Lección en directo de ICT, 31/08/2026 (NQ): How New Students Should Start Part 1: youtube.com/watch?v=BWEPtHZ1Y2Y",
              "Lección en directo de ICT, 01/09/2026 (NQ): How New Students Should Start Part 2: youtube.com/watch?v=djabvhihIM8",
              "Backtest TTFM de este repositorio: report/TTFM_Report.pdf y results/summary.json.",
          ]]]

    doc = SimpleDocTemplate(str(OUT), pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm,
                            topMargin=1.8 * cm, bottomMargin=1.8 * cm,
                            title="Metodología ICT", author="drjimenez")
    doc.build(s, onFirstPage=lambda c, d: None, onLaterPages=on_page)
    print("OK", OUT)


if __name__ == "__main__":
    build()
