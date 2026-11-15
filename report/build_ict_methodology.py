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
            "cierres sobre el 50 % de las mechas. En la parte 3 (sección 9) explica cómo organiza "
            "toda esa información en cinco layouts separados, y en la parte 4 (sección 10) propone "
            "una rutina diaria de registro de tres fenómenos medibles. La parte 5 (sección 11) "
            "explica cómo convierte esos registros en operaciones hipotéticas (su forma de backtesting)."),
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
              ["First presented FVG (y variantes)", "Primer FVG después de las 09:30. <b>Con "
               "desplazamiento</b>: el primero cuyo tramo rompe un máximo o mínimo. <b>Reflection</b>: el "
               "primer FVG de sentido contrario al primero.", "Zonas de referencia para ese día y los "
               "siguientes (ver 11.6)."],
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

    # 9. Parte 3
    s += [PageBreak(), P("9. <i>How New Students Should Start, Part 3</i> (02/09/2026): gestionar la "
                         "información", H1),
          P("Lección grabada la noche del miércoles, sin operaciones. Su mensaje central: el problema "
            "del alumno nuevo no es que le falten herramientas, sino tener <b>demasiada información "
            "mezclada en un solo gráfico</b>. Rechaza los mapas de calor y de liquidez: \"apertura, "
            "máximo, mínimo y cierre en relación con el tiempo te dan todo lo que necesitas\". Cuenta "
            "que trabaja \"el 99 % del tiempo\" con papel y lápiz, y que su libreta contiene exactamente "
            "lo que se ve en sus gráficos."),
          *Q("You have to be a good manager of the information and the data… by managing the information "
             "and keeping record of where everything is, that's trading, folks.",
             "Tienes que gestionar bien la información y los datos. Gestionar la información y llevar "
             "registro de dónde está todo: eso es operar."),
          P("9.1 Un layout para cada tipo de información", H2),
          P("Al final de la lección habla de los <b>\"cinco pilares del reparto algorítmico del "
            "precio\"</b>. No los enumera de forma explícita, pero coinciden con los cinco layouts "
            "(espacios de trabajo) que muestra, cada uno con <i>solo</i> un tipo de dato:"),
          table([
              ["Layout", "Qué contiene", "Cómo se construye"],
              ["1. Monthly macro keys", "Apertura, máximo, mínimo y cierre de los <b>últimos 3 "
               "meses</b> y el máximo y mínimo de la <b>semana anterior</b> (lunes a viernes). Nada "
               "más: ni FVG, ni order blocks, ni huecos.",
               "Gráfico mensual. Máximos y mínimos en azul, aperturas en negro discontinuo, etiquetas "
               "tipo \"August 2026 monthly high\". Opcional: 12 meses para el contexto anual."],
              ["2. NWOG matrix", "Los huecos de apertura semanal de las <b>últimas 5 semanas</b>, en "
               "rotación.",
               "En horario electrónico (ETH): del cierre del viernes a las 16:59 a la apertura del "
               "domingo a las 18:00 (NY). Si el viernes es festivo, se usa el jueves. Etiqueta \"NWOG "
               "fecha\"; copia del layout cada trimestre."],
              ["3. NDOG matrix", "Huecos de apertura diaria.", "Diferencia entre el cierre de una "
               "sesión y la reapertura siguiente."],
              ["4. First presented FVG matrix", "El primer FVG que se forma <b>después de las 09:30</b> "
               "de cada día.", "Variante: el primer FVG que causa desplazamiento. En el ejemplo, el "
               "primero aparece pasadas las 09:38."],
              ["5. RTH opening range gap matrix", "Los huecos entre el cierre de la sesión regular "
               "(último precio de las 16:14) y la apertura de las 09:30.",
               "Con el gráfico en horario regular (RTH). Se buscan por fecha y hora en el calendario "
               "de la plataforma y se dividen con Fibonacci."],
          ], [3.4 * cm, 5.6 * cm, W - 9.0 * cm]),
          Spacer(1, 6),
          P("Luego tiene un gráfico de trabajo y salta de un layout a otro cuando necesita un dato. "
            "Las divisiones de Fibonacci se dibujan para leer, se apuntan en la libreta y se quitan "
            "para mantener limpio el gráfico."),
          P("9.2 Contexto mayor: premium o descuento en tres escalas", H2),
          *bullets(["<b>Rango de 3 meses</b>: el 2 de septiembre el precio estaba justo en su 50 %. "
                    "\"Estamos en equilibrio… así que exigimos que el semanal y el diario nos den "
                    "más información\".",
                    "<b>Semana anterior</b>: la semana abrió en la zona premium de ese rango y luego "
                    "bajó a descuento, rompiendo el mínimo de la semana anterior el miércoles "
                    "(durante la macro de 06:50–07:10).",
                    "<b>Cambios trimestrales</b> (<i>quarterly shifts</i>, mentoría 2016–2017): los "
                    "grandes movimientos de 1 a 3 meses, ligados a la estacionalidad. Es la "
                    "perspectiva del swing trader.",
                    "<b>Estacionalidad de índices</b>: septiembre suele ser bajista; el mínimo suele "
                    "llegar en septiembre u octubre (rara vez en noviembre) y después sube hasta la "
                    "primera semana de febrero. \"No es una panacea… es una regla general\"."]),
          P("9.3 Cómo transpone el FVG diario al gráfico de 1 minuto", H2),
          P("Revisa la caída del martes con un FVG / volume imbalance diario (sombreado en azul) en "
            "el que casi no hay cuerpos de vela:"),
          *bullets(["Si en el diario hay un hueco sin cuerpos, el precio debería atravesarlo "
                    "<b>rápido y sin oposición</b>, no \"a trompicones\". Así fue: el martes a las "
                    "03:00 cayó a través de él \"en cascada\" sin respetar los soportes clásicos.",
                    "En el gráfico de 1 minuto, los rebotes y frenos coinciden con los <b>octavos</b> "
                    "de ese FVG diario: cuadrante superior, octante superior, CE (50 %), octante "
                    "inferior, cuadrante inferior… \"Si es débil, no volverá al CE\".",
                    "Usa ese comportamiento como argumento de que el mercado es \"algorítmico, "
                    "programado\": duda que la presión de compra y venta coincida por casualidad con "
                    "sus niveles."]),
          P("9.4 Huecos anidados y \"shadow\"", H2),
          *bullets(["Si varios huecos de apertura (RTH) se solapan en una consolidación, manda <b>el "
                    "más grande</b> en el que esté el precio (el del martes 1, de más de 400 puntos).",
                    "En un contexto bajista, el rebote se detuvo exactamente en el <b>50 % (CE)</b> "
                    "del hueco del martes y luego bajó. Los niveles en octavos del hueco del 26 de "
                    "agosto también frenaron el precio.",
                    "<b>Shadow</b>: la zona donde se solapan dos huecos de apertura (el del martes y "
                    "el del miércoles). Si coincide con una vela bajista, \"así sabes que ese order "
                    "block es válido\". Lo considera un soporte o resistencia mucho más preciso que "
                    "una línea de soporte clásica.",
                    "Varias velas bajistas seguidas forman <b>un solo order block</b>; su nivel clave "
                    "es la apertura de la primera, que marca el cambio de estado de reparto (CISD)."]),
          P("9.5 Cuándo no operar", H2),
          P("Tras las 11:00 del miércoles de NFP, el precio quedó \"en tierra de nadie\" entre dos "
            "first presented FVG y lejos de cualquier NWOG. \"¿Qué escuela diría que hay que operar "
            "esto? Un jugador\". Él podría encontrar setups ahí, pero se abstiene para que el alumno "
            "aprenda que no hace falta operar siempre. Reitera que nunca ha prometido rentabilidad: "
            "promete \"una forma de leer el precio\"."),
          P("9.6 Qué aporta respecto a las partes 1 y 2", H2),
          table([
              ["Tema", "Aportación de la parte 3"],
              ["Organización", "Cinco layouts separados, cada uno con un solo tipo de dato, y la "
               "libreta como registro principal."],
              ["Contexto mayor", "Rango de 3 meses y semana anterior, no solo el mes anterior. "
               "Cambios trimestrales y estacionalidad anual de los índices."],
              ["Huecos", "Procedimiento exacto para los NWOG (16:59 del viernes → 18:00 del domingo, "
               "últimas 5 semanas) y los huecos RTH (16:14 → 09:30). Con huecos anidados, manda el "
               "mayor."],
              ["Order blocks", "Validados por un \"shadow\" (solapamiento de huecos); varias velas "
               "bajistas = un solo OB."],
              ["Estilos", "Dice que el mismo marco sirve para todo: posición (1–5 días, \"one shot, "
               "one kill\"), swing intradía y scalping."],
          ], [3.0 * cm, W - 3.0 * cm]),
          Spacer(1, 4),
          P("Observación crítica: con cinco layouts, varios huecos por layout y cada uno dividido en "
            "octavos, hay decenas de niveles a la vista. Con tantos niveles, casi cualquier giro del "
            "precio coincidirá con alguno por pura densidad, y la revisión a posteriori lo hará "
            "parecer \"programado\". Se puede comprobar: medir cuántas veces el precio reacciona en "
            "los octavos de un FVG diario o de un hueco frente a niveles colocados al azar con la "
            "misma densidad. Es la prueba clave de la idea del \"mercado algorítmico\".", BOX)]

    # 10. Parte 4
    s += [PageBreak(), P("10. <i>How New Students Should Start, Part 4</i>: los tres pilares del "
                         "registro diario", H1),
          P("Lección corta y muy práctica, grabada antes del Labor Day (lunes 7 de septiembre de 2026). "
            "Aquí no enseña a operar, sino una <b>rutina de unos 20 minutos al día</b> para entrenar el "
            "ojo: registrar con capturas de pantalla tres fenómenos que, según él, \"se repiten cada "
            "día, a una hora concreta y de una forma concreta\". Insiste en que <b>no es backtesting</b>; "
            "eso lo deja para la parte 5."),
          *Q("You don't have to have everything I teach. In fact, the worst thing I see happen is new "
             "students… try to learn as much as they can as fast as they can… only to find out they "
             "haven't learned anything.",
             "No necesitas todo lo que enseño. Lo peor que veo es a alumnos nuevos que intentan aprender "
             "todo lo más rápido posible… y descubren que no han aprendido nada."),
          P("10.1 Plan de seis semanas", H2),
          table([
              ["Semanas", "Qué hacer"],
              ["1–2", "Solo un pilar (el que elijas)."],
              ["3–4", "Añadir un segundo pilar."],
              ["5–6", "Añadir el tercero. A partir de ahí, los tres cada día."],
              ["Además", "Repetir lo mismo con <b>6 semanas de datos pasados</b>, para terminar con "
               "<b>12 semanas</b> registradas. <b>Un solo mercado: NQ</b>, aunque luego vayas a operar "
               "otro. Nada de Asia ni Londres al principio."],
              ["Alumnos con experiencia", "Pueden hacer los tres a la vez desde el principio, pero no "
               "saltarse la fase de registro."],
          ], [3.4 * cm, W - 3.4 * cm]),
          P("10.2 Pilar 1: la sesión premarket (07:00–09:00 NY)", H2),
          *bullets(["Trazar líneas verticales a las 07:00 y a las 09:00 y marcar el <b>máximo y el "
                    "mínimo</b> de ese tramo, más los <b>máximos o mínimos relativamente iguales</b> "
                    "(pools de liquidez).",
                    "Clasificar el tramo: <b>¿tendencia o consolidación?</b> (en la mentoría de 2016 "
                    "distingue cuatro fases: expansión, retroceso, reversión y consolidación; aquí lo "
                    "simplifica a dos).",
                    "Usarlo como pista del comportamiento tras las 09:30. En su ejemplo, el premarket "
                    "fue en tendencia y, tras una pequeña expansión a las 09:30, el resto del día "
                    "consolidó. La explicación es algo ambigua; lo que pide es <b>registrar la "
                    "relación cada día</b> para descubrirla uno mismo. \"No es una panacea\".",
                    "Setup \"de pan con mantequilla\": barrido de los mínimos iguales del premarket y "
                    "objetivo en el extremo opuesto de ese rango. Al llegar, \"has terminado por hoy\".",
                    "Qué anotar: máximo, mínimo, pools de liquidez (con precios), estado (tendencia o "
                    "consolidación) y <b>cuántos minutos después de las 09:30</b> reaccionó el precio "
                    "en esos niveles."]),
          P("10.3 Pilar 2: el 50 % del hueco de apertura (RTH)", H2),
          *bullets(["Gráfico de <b>1 minuto en horario regular (RTH)</b>. El hueco va del último precio "
                    "de las 16:14 del día anterior a la apertura de las 09:30.",
                    "Dibujar un rectángulo con la línea media activada: esa línea es el "
                    "<b>consequent encroachment (CE)</b>.",
                    "Registrar <b>si el precio llega al CE y cuándo</b>. Repite la cifra del 70 % antes "
                    "de las 10:00, pero ahora añade: <b>\"no me toméis la palabra… llevad el registro y "
                    "calculad la estadística a final de año\"</b>.",
                    "Uso práctico: el CE como objetivo para cualquier FVG u order block a favor, sin "
                    "necesidad de esperar al cierre completo del hueco."]),
          P("10.4 Pilar 3: Silver Bullet, primer FVG después de las 10:00", H2),
          *bullets(["En el gráfico de 1 minuto, buscar el <b>primer FVG que se forma desde la vela de "
                    "las 10:00</b> (esa vela puede contar). Incluir los volume imbalances (cuerpos que "
                    "no se tocan) en el FVG.",
                    "Extenderlo a la derecha hasta que el precio vuelva a él. Desde ahí, el movimiento "
                    "esperado es hacia el mínimo (o máximo) de corto plazo más cercano: la sell side o "
                    "la buy side.",
                    "Qué anotar: <b>hora de formación</b> (p. ej., 10:01), <b>minutos hasta el "
                    "retorno</b> al FVG y <b>recorrido en puntos</b> desde el retorno hasta el "
                    "extremo alcanzado.",
                    "Al principio se registra a posteriori, sin intentar adivinar la dirección. La "
                    "anticipación llega con la repetición."]),
          P("10.5 Plantilla de registro diario", H2),
          P("Tabla basada en lo que pide anotar en la lección, para copiar en una hoja de cálculo o un "
            "diario electrónico (sugiere etiquetas que permitan buscar por fecha y tema):", NOTE),
          table([
              ["Pilar", "Campos", "Etiqueta sugerida"],
              ["1. Premarket", "Fecha · máximo 07–09 · mínimo 07–09 · máximos/mínimos iguales (precio) · "
               "estado (tendencia/consolidación) · ¿qué pool se tomó tras las 09:30? · hora de la "
               "reacción · comportamiento del resto del día", "premarket-estado, premarket-liquidez"],
              ["2. Hueco RTH", "Cierre 16:14 · apertura 09:30 · tamaño del hueco · dirección (premium o "
               "descuento) · CE · ¿llegó al CE? · hora · ¿antes de las 10:00? · ¿cerró el hueco "
               "completo?", "rth-gap-ce"],
              ["3. Silver Bullet", "Hora del primer FVG ≥ 10:00 · alcista/bajista · límites del FVG · "
               "minutos hasta el retorno · objetivo (buy/sell side) · ¿lo alcanzó? · recorrido en "
               "puntos", "silver-bullet-10am"],
              ["Notas", "Observaciones, captura centrada con espacio para anotar y revisión del fin de "
               "semana", "revisión-semanal"],
          ], [2.6 * cm, W - 6.4 * cm, 3.8 * cm]),
          P("10.6 Método y actitud", H2),
          *bullets(["<b>Tres capturas al día</b>, centradas del máximo al mínimo y con espacio libre "
                    "para escribir observaciones. \"Si no puedes hacer esto, te prometo que no podrás "
                    "seguir las reglas de un modelo\".",
                    "Revisar las capturas el sábado o el domingo, con el mercado parado: aparecen "
                    "detalles que se pasaron por alto.",
                    "Orden y limpieza \"como si yo fuera tu profesor y pusiera nota\": es \"una señal de "
                    "carácter\". El diario será \"una máquina del tiempo\" años después.",
                    "Él lo hace cada día a mano en libretas de cuero; recomienda el formato electrónico "
                    "porque permite buscar. \"No es Netflix and chill viendo vídeos de ICT\"."]),
          Spacer(1, 4),
          P("Valoración: es la lección más fácil de aplicar y la más útil para comprobar el método. Los "
            "tres pilares están definidos por <b>hora y precio</b>, sin interpretación, así que se pueden "
            "medir de forma objetiva: frecuencia con la que el precio llega al CE del hueco antes de las "
            "10:00, relación entre el estado del premarket y el resto del día, y tasa de acierto del "
            "primer FVG después de las 10:00. Requieren datos de 1 minuto del futuro NQ real (sesión "
            "regular), no los proxies 24/7 del backtest TTFM.", BOX)]

    # 11. Parte 5
    s += [PageBreak(), P("11. <i>How New Students Should Start, Part 5</i>: cómo hace él el backtesting",
                         H1),
          P("Última lección de la serie. Retoma los tres pilares de la parte 4 sobre una sesión de NQ de "
            "septiembre de 2026 y enseña cómo convertir cada uno en una <b>operación hipotética "
            "registrada</b>: entrada, stop, objetivo, riesgo y drawdown. Para él, eso es backtesting; "
            "una simple captura a posteriori no lo es."),
          P("11.1 Herramientas: grabar la pantalla, no Market Replay", H2),
          *bullets(["<b>Market Replay \"es inútil… literalmente tóxico\"</b>: solo muestra la apertura y "
                    "el cierre de cada vela, no su \"vida completa\" (cómo forma el máximo y el mínimo "
                    "mientras está abierta).",
                    "Alternativa: <b>grabar la pantalla</b> todo el día con el gráfico de 1 minuto "
                    "(Windows + Alt + R en Windows) y revisarlo después, pausando y narrando con tu propia "
                    "voz. Con datos en diferido sirve igual: \"estás estudiando precio que ya ocurrió\".",
                    "Los datos en tiempo real de TradingView cuestan unos 7 $: \"si no tienes 7 $, no "
                    "tienes dinero para operar\". Banea a quien pide que le paguen cuentas o datos.",
                    "La misma lógica vale en cualquier temporalidad: \"la velocidad del gráfico de 1 "
                    "minuto es una ilusión\"."]),
          P("11.2 Cómo registrar cada operación hipotética", H2),
          table([
              ["Elemento", "Regla que da"],
              ["Precisión", "Anotar los precios exactos (apertura, máximo, mínimo, cierre) con la "
               "herramienta <i>price note</i>, no \"más o menos 560\". \"Si no eres preciso al "
               "registrar, tus operaciones nunca serán precisas\"."],
              ["Entrada realista", "En un FVG bajista, entrar en el <b>CE (50 %) o un tick por debajo</b>, "
               "no en el máximo exacto. Si el precio sube más, se puede añadir un contrato en la mitad "
               "superior (pirámide)."],
              ["Stop", "Un tick por encima del máximo de la <b>última vela que estuvo fuera del FVG</b> "
               "(su apertura, no solo la mecha), incluyendo el volume imbalance."],
              ["Objetivo", "Un tick antes del nivel (para asegurar la ejecución). Ampliar objetivos "
               "solo con experiencia."],
              ["Riesgo y drawdown", "Anotar el riesgo total y cuánto y durante cuántos minutos fue el "
               "precio en contra (\"el calor\"). Market Replay no enseña a vivir ese drawdown."],
              ["Tamaño", "Si el stop correcto es grande, usar micros: \"expectativas realistas, no un "
               "subidón de azúcar\"."],
              ["R:R", "No lo calcula: \"mis conceptos ya traen incorporado 3:1, 5:1\"."],
              ["Anotaciones", "Usar el espacio libre del gráfico; si falta sitio, letras (A, B, C) "
               "como leyenda con la explicación al lado. Describir vela a vela (p. ej., cada "
               "immediate rebalance)."],
          ], [3.0 * cm, W - 3.0 * cm]),
          P("11.3 El diario como \"cartas de amor a uno mismo\"", H2),
          P("Es la parte más llamativa de la lección. Pide escribir las observaciones <b>en tono "
            "positivo y seguro</b> (\"me encantó ver cómo…\", \"me agradó…\"), registrar las operaciones "
            "hipotéticas <b>como si se hubieran hecho</b>, y no escribir nunca en el diario las pérdidas "
            "o la frustración. Ni siquiera en un día real con pérdidas: se anota lo que se debería "
            "haber visto, \"como si lo hubieras hecho así\". Así, dice, se \"engaña al subconsciente\" "
            "para crear \"pseudoexperiencia\" y quitar el miedo, igual que haría un coach "
            "motivacional."),
          *Q("You're only recording the sweet sugary love letter stuff to yourself because your "
             "subconscious loves that.",
             "Solo registras lo dulce, cartas de amor a ti mismo, porque a tu subconsciente le encanta."),
          P("11.4 Los tres pilares aplicados a una sesión", H2),
          table([
              ["Pilar", "Lo que muestra en el ejemplo"],
              ["1. Premarket", "Divide el rango 07:00–09:00 con Fibonacci y corta las líneas a las "
               "09:00, para ver si coinciden con las del <b>opening range</b> (09:30–10:00). Un FVG "
               "bajista de las 11:09 retrocede justo al CE y al máximo del premarket y cae <b>94 puntos</b> "
               "hasta los mínimos iguales del premarket (29.370,50). Antes, otro FVG en premium dio "
               "más de 100 puntos."],
              ["2. Hueco RTH", "Hueco en descuento de <b>69 puntos</b>; el CE se alcanza 5 minutos "
               "después de las 09:30. Nuevo concepto: <b>proyecciones de desviación estándar</b> del "
               "hueco (Fibonacci del cierre a la apertura, nivel −1,0). Dice que marcaron \"al tick\" "
               "el máximo de la mañana y el mínimo de las 11:12 (29.386,25). También vuelve a los "
               "máximos iguales del cierre del día anterior (la macro de <i>market on close</i>)."],
              ["3. Silver Bullet", "El primer FVG (10:01, bajista) acabó dando <b>más de 175 puntos</b>, "
               "pero no lo vendió de inmediato por la <b>lunch macro</b>: el mercado tiende a buscar "
               "el mínimo formado en la hora de las 10:00. Además, un FVG posterior <b>con "
               "desplazamiento</b> (alcista, que rompe máximos) \"manda más\" que el primero y, al "
               "invertirse, sirve de entrada en corto: entrada en su mitad inferior, stop sobre la "
               "última vela fuera del FVG, parcial en los mínimos iguales."],
          ], [2.6 * cm, W - 2.6 * cm]),
          P("11.5 Otras afirmaciones de la lección", H2),
          *bullets(["<b>\"El rango de apertura (dealing range) es de 30 minutos\"</b> (09:30–10:00). "
                    "\"No me importa cuánta gente diga que son 5 o 15 minutos. Todos se equivocan\".",
                    "Los tres pilares \"encajan\": el premarket, el hueco y el Silver Bullet cuentan "
                    "juntos la narrativa del día. \"No estoy eligiendo lo que funciona aquí y no allí\".",
                    "Quienes \"pasan sus conceptos por la IA y dicen que no funcionan\" no tienen las "
                    "reglas, por ejemplo la del first presented FVG con desplazamiento.",
                    "La IA \"nunca podrá\" leer una vela mientras se forma; el ser humano sí. Compara "
                    "el backtesting con los diagramas que estudia un cirujano antes de operar."]),
          P("11.6 Ampliación: <i>NQ Futures Review &amp; 1st Presented Reflection FVG</i> (08/09/2026)", H2),
          P("Al día siguiente de la parte 5 (martes tras el Labor Day) aclara las reglas que, según él, "
            "faltan a quienes prueban sus conceptos. Distingue <b>tres PD arrays</b>:"),
          table([
              ["PD array", "Definición", "Uso que le da"],
              ["First presented FVG", "El primer FVG después de las 09:30, tenga o no desplazamiento.",
               "Útil, pero con menos peso."],
              ["FP con desplazamiento", "El primer FVG después de las 09:30 que forma parte de un tramo "
               "que <b>rompe un máximo o mínimo</b>.", "\"Mucha más importancia\" que el primero. Si hay "
               "un FVG antes, se clasifica igualmente el primero."],
              ["First presented reflection", "Si el primer FVG es alcista (BISI), el primer FVG bajista "
               "(SIBI) que se forma después, y viceversa: su \"imagen en el espejo\".", "Más fuerte si "
               "se forma en una macro (su ejemplo, a las 10:01). Lo usa días después: el del viernes 4 "
               "le sirvió el martes 8 para vender el máximo del día."],
          ], [3.4 * cm, 6.4 * cm, W - 9.8 * cm]),
          Spacer(1, 4),
          *bullets(["Su operación del martes: el precio abre, sube con una mecha por encima del FPR del "
                    "viernes y cierra por debajo (\"uno de los patrones de giro más fuertes\"). Vende "
                    "dentro de un FVG bajista pequeño, stop sobre la mecha, y sale en el CE del "
                    "<i>suspension block</i> del premarket: un objetivo \"fácil\" (<i>low hanging fruit</i>).",
                    "<b>Tras un festivo con horario reducido</b>, opera con 1 contrato en lugar de 6 y "
                    "busca objetivos cercanos: el volumen es raro y \"nadie sabe qué hará el mercado\".",
                    "Con el FPD bajista, exige que cualquier retroceso no toque la mitad superior; si un "
                    "cuerpo cierra sobre su 50 %, espera vuelta a la apertura de las 09:30.",
                    "Dice tener \"81\" PD arrays y que no hace falta conocerlos todos."]),
          P("Medido con estas definiciones en 755 sesiones (informe de medición, sección 5), ni el FPD "
            "ni el FPR se distinguen de cualquier otro FVG de 1 minuto.", NOTE),
          P("11.7 Ampliación: <i>Trading Premarket and Regular Session Liquidity</i> (18/09/2025)", H2),
          P("Revisión de una sesión de NQ (y del DXY y el EUR/USD) en una semana alcista cerca de máximos "
            "históricos. Reglas que aporta:"),
          *bullets(["<b>Cerca de máximos históricos</b>: dividir en cuartos (25, 50 y 75 %) todas las "
                    "mechas premium y discount de las velas diarias recientes de la subida. \"No intentes "
                    "adivinar el techo\".",
                    "<b>Jueves</b>: en una semana alcista, el jueves forma el máximo de la semana o un "
                    "\"máximo falso\" que se rompe después.",
                    "<b>Premarket y 08:30</b>: a las 07:00 empieza un tramo hacia la liquidez; justo antes de "
                    "la noticia de las 08:30 barre la buy side y vende hacia la sell side del premarket. "
                    "Como opera <i>contra</i> el sesgo diario, sale en el objetivo más fácil.",
                    "<b>Lunch macro</b>: en días alcistas, hacia las 11:30 el precio busca la primera sell "
                    "side destacada formada después de las 10:00 (lo simétrico en días bajistas).",
                    "<b>Reclaimed FVG</b>: un FVG que el precio supera y luego recupera su sentido original "
                    "(no es un inversion FVG). Dentro de él, el precio \"distorsiona el tiempo\" y consolida.",
                    "Otros: el <i>Market Maker Sell Model</i> visto como fractal en 1 minuto, el patrón "
                    "<i>Venom</i>, el <i>institutional order flow entry drill</i> (un FVG que el precio solo "
                    "roza con una vela) y una operación con su algoritmo \"Enigma\"."]),
          P("Medido en 755 sesiones (informe de medición, sección 6): la lunch macro no busca la liquidez "
            "contraria más que la favorable; el patrón del jueves aparece igual con los días barajados al "
            "azar; y el barrido del premarket en torno a las 08:30 no da ventaja (−0,16 R netos).", NOTE),
          P("11.8 Ampliación: <i>Monday Review On NQ &amp; PreMarket Session Rules Revisited</i> (24/08/2026)", H2),
          *bullets(["<b>La regla del premarket, precisada</b>: \"la idea de que el mercado consolide entre "
                    "las 7 y las 9: esas son las reglas\". Si consolida, a las 09:30 llega \"un gran "
                    "movimiento en una sola dirección\"; la dirección la da el análisis de temporalidad "
                    "alta (ese día, bajista hacia un volume imbalance diario y por estacionalidad).",
                    "<b>Cómo clasificar</b>: un empujón inicial que solo barre buy side (unos 40 minutos) "
                    "no es tendencia; si después el precio vuelve dentro y gira alrededor de la mitad del "
                    "rango, es consolidación. Se miran los <b>cuerpos</b>, no las mechas: \"la mecha es "
                    "donde se permite hacer el daño\".",
                    "Afirma que nadie más usa \"el 7 a 9\" para anticipar la mañana y que \"hay un "
                    "algoritmo\" aunque no pueda enseñar su código.",
                    "Reconoce que ese día <b>no pudo entrar</b>: la caída de las 09:30 fue demasiado rápida, "
                    "y su objetivo (el volume imbalance diario) no se alcanzó; con su plan habría saltado "
                    "el stop.",
                    "Otros detalles: un order block es válido si está \"anclado\" a un octante de un FVG "
                    "diario; aviso de no apalancarse en la semana de Jackson Hole."]),
          P("Medido en 742 sesiones con tres definiciones de consolidación (informe de medición, sección "
            "2): el movimiento grande de apertura ocurre el 26 % de los días, haya consolidado o no el "
            "premarket. El 24/08/2026 se cumplió, pero es un caso, no una regla.", NOTE),
          P("11.9 Valoración de su método de backtesting", H2),
          table([
              ["Aspecto", "Lo útil", "El problema"],
              ["Entradas y stops", "Reglas concretas y conservadoras: CE − 1 tick, stop + 1 tick, "
               "objetivo − 1 tick, registro del drawdown. Se pueden programar.", "Se eligen mirando el "
               "gráfico ya completo; sin una regla escrita antes, la elección queda sesgada."],
              ["Diario positivo", "Puede ayudar a mantener la constancia y reducir la ansiedad.",
               "Registrar solo lo bueno, y \"como si lo hubieras hecho\", es <b>sesgo de "
               "supervivencia</b>. Con un diario así no se puede calcular una tasa de acierto real y "
               "contradice el \"calcula la estadística a fin de año\" de la parte 4."],
              ["Reglas cambiantes", "Añade matices reales (lunch macro, FVG con desplazamiento).",
               "Cada nueva regla aparece después de ver el resultado (el primer FVG \"no valía\" "
               "porque había otro con desplazamiento). Así cualquier fallo se puede explicar a "
               "posteriori y el método se vuelve difícil de falsar."],
              ["Precisión \"al tick\"", "Las proyecciones del hueco son fáciles de medir.", "Con "
               "muchos niveles (−1, −2, octavos…) alguno coincidirá con el máximo o el mínimo; hay "
               "que comparar con niveles al azar."],
              ["IA y datos", "—", "La afirmación es falsa en lo técnico: los datos tick a tick "
               "registran cómo se forma cada vela, y un programa puede leerlos igual que una "
               "grabación de pantalla."],
          ], [2.8 * cm, 5.4 * cm, W - 8.2 * cm]),
          Spacer(1, 4),
          P("Recomendación práctica: llevar <b>dos registros</b>. Uno, su diario de entrenamiento, para "
            "aprender a ver los patrones. Otro, <b>estadístico y honesto</b>: reglas escritas antes de "
            "mirar el día, todas las señales (también las que fallan), resultado en R tras costes y "
            "drawdown. Solo el segundo dice si hay ventaja.", BOX)]

    # 12. Checklist
    s += [PageBreak(), P("12. Lista de comprobación antes de operar", H1),
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
              ["14", "¿Dónde está el precio respecto al rango de 3 meses y al de la semana anterior? "
               "¿Está en tierra de nadie entre PD arrays?", ""],
              ["15", "¿Ya hice mi trade del día o alcancé mi objetivo semanal?", ""],
          ], [0.8 * cm, W - 2.8 * cm, 2.0 * cm]),
          Spacer(1, 8),
          P("13. Gestión del riesgo y psicología", H1),
          *bullets(["Arriesga poco por operación (habla de 1 % o menos y de reducirlo tras pérdidas).",
                    "Pocas operaciones: prefiere un setup de alta probabilidad a muchas entradas.",
                    "Cierres parciales en liquidez interna y protección del stop.",
                    "Diario de operaciones y práctica en demo antes de usar dinero real.",
                    "Paciencia: el \"no trade\" es una posición. Si el día no ofrece el modelo, no se "
                    "fuerza.",
                    "Advierte que su contenido en YouTube es gratuito y que no pide dinero ni gestiona "
                    "fondos de nadie: quien se presente como ICT pidiendo dinero es falso."])]

    # 14. Valoración
    s += [P("14. Valoración crítica", H1),
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
                    "<b>Diario solo positivo</b>: en la parte 5 pide registrar las operaciones "
                    "hipotéticas \"como si se hubieran hecho\" y no anotar pérdidas. Eso impide medir "
                    "una tasa de acierto real (ver sección 11).",
                    "<b>Densidad de niveles</b>: con decenas de niveles (octavos de varios FVG y "
                    "huecos), casi cualquier giro coincide con alguno. Hay que compararlo con niveles "
                    "al azar antes de atribuirlo a un algoritmo (ver sección 9).",
                    "<b>Estadísticas que no se confirman</b>: medido en 755 sesiones del Nasdaq 100 "
                    "(informe aparte <i>ICT_Tres_Pilares_Medicion.pdf</i>), el 50 % del hueco se alcanza "
                    "antes de las 10:00 el 53 % de los días, no el 70 %, y un nivel a la misma distancia "
                    "en el lado contrario se alcanza igual de a menudo. Tampoco destacan las proyecciones "
                    "−1 del hueco, los niveles iguales ni la hora del Silver Bullet.",
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
            "narrativa. El punto de partida natural son los tres pilares de la parte 4 (premarket, "
            "CE del hueco RTH y Silver Bullet de las 10:00), porque ya están definidos por hora y precio.", BOX)]

    # Fuentes
    s += [P("Fuentes y método", H1),
          P("No se han podido ver los vídeos directamente. La parte general del informe combina el contenido público del "
            "canal tal como lo recogen notas y resúmenes, y búsquedas web del 15 de noviembre de 2026. "
            "Las páginas de resúmenes de vídeos no se pudieron abrir desde el entorno de trabajo. "
            "Las secciones 7 a 11 se basan en las transcripciones automáticas de las partes 1–5 de How New Students Should Start (31/08 a septiembre de 2026) "
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
              "Lección grabada de ICT, 02/09/2026: How New Students Should Start Part 3: youtube.com/watch?v=MB7clEZvF7s",
              "Lección grabada de ICT, septiembre de 2026: How New Students Should Start Part 4 \\ Pillars Of Daily Log Entries: youtube.com/watch?v=L81eMQhmXmc",
              "Revisión de ICT, 24/08/2026: Monday Review On NQ & PreMarket Session Rules Revisited (título probable): youtube.com/watch?v=grcLMbjs-zs",
              "Lección de ICT, 18/09/2025: Trading Premarket and Regular Session Liquidity",
              "Revisión de ICT, 08/09/2026: NQ Futures Review & 1st Presented Reflection FVG: youtube.com/watch?v=9W4YpyAg5RY",
              "Lección grabada de ICT, septiembre de 2026: How New Students Should Start Part 5 \\ Back Testing Properly: youtube.com/watch?v=xnbtp_j81lI",
              "Backtest TTFM de este repositorio: report/TTFM_Report.pdf y results/summary.json.",
          ]]]

    doc = SimpleDocTemplate(str(OUT), pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm,
                            topMargin=1.8 * cm, bottomMargin=1.8 * cm,
                            title="Metodología ICT", author="drjimenez")
    doc.build(s, onFirstPage=lambda c, d: None, onLaterPages=on_page)
    print("OK", OUT)


if __name__ == "__main__":
    build()
