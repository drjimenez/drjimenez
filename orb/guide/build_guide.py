"""
build_guide.py — Genera la guía imprimible orb/guide/Guia_ORB_Fibonacci.pdf:
cómo interpretar los valores del indicador y del dashboard y qué lógica seguir antes de entrar.

Las cifras salen de la base de datos del estudio (results/dukascopy/orb_study.sqlite) y de la
rejilla de reglas (results/dukascopy/strategy_grid.csv), así que se regeneran con los datos.

Uso:  python3 orb/guide/build_guide.py
"""
from __future__ import annotations

import os
import sqlite3

import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (Image, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table,
                                TableStyle)

HERE = os.path.dirname(os.path.abspath(__file__))
ORB = os.path.dirname(HERE)
RES = os.path.join(ORB, "results", "dukascopy")
PDF = os.path.join(HERE, "Guia_ORB_Fibonacci.pdf")
FIG = os.path.join(HERE, "figs")

# Fuente con ✓ ✗ ▲ ▼ (DejaVu, incluida en matplotlib)
FD = os.path.join(os.path.dirname(matplotlib.__file__), "mpl-data", "fonts", "ttf")
pdfmetrics.registerFont(TTFont("DV", os.path.join(FD, "DejaVuSans.ttf")))
pdfmetrics.registerFont(TTFont("DVB", os.path.join(FD, "DejaVuSans-Bold.ttf")))
pdfmetrics.registerFont(TTFont("DVI", os.path.join(FD, "DejaVuSans-Oblique.ttf")))
pdfmetrics.registerFontFamily("DV", normal="DV", bold="DVB", italic="DVI", boldItalic="DVB")

INK, INK2, GRID = "#111111", "#4a4a4a", "#d9d9d9"
BLUE, ORANGE, GREEN, RED = "#2a78d6", "#eb6834", "#1baf7a", "#c2441a"
C_HEAD = colors.HexColor("#1f3b5c")
C_ROW = colors.HexColor("#f3f5f8")

ST = {
    "h1": ParagraphStyle("h1", fontName="DVB", fontSize=17, leading=21, spaceAfter=4, textColor=colors.HexColor(INK)),
    "sub": ParagraphStyle("sub", fontName="DV", fontSize=9.5, leading=13, textColor=colors.HexColor(INK2), spaceAfter=8),
    "h2": ParagraphStyle("h2", fontName="DVB", fontSize=12.5, leading=16, spaceBefore=10, spaceAfter=5, textColor=C_HEAD),
    "h3": ParagraphStyle("h3", fontName="DVB", fontSize=10, leading=13, spaceBefore=6, spaceAfter=3),
    "p": ParagraphStyle("p", fontName="DV", fontSize=9, leading=12.6, spaceAfter=5, alignment=TA_LEFT),
    "small": ParagraphStyle("small", fontName="DV", fontSize=7.8, leading=10.4, textColor=colors.HexColor(INK2)),
    "cell": ParagraphStyle("cell", fontName="DV", fontSize=8, leading=10.4),
    "cellb": ParagraphStyle("cellb", fontName="DVB", fontSize=8, leading=10.4),
    "box": ParagraphStyle("box", fontName="DV", fontSize=9, leading=12.6),
}

plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 8.5, "axes.spines.top": False,
                     "axes.spines.right": False, "savefig.facecolor": "white"})


def P(t, s="p"):
    return Paragraph(t, ST[s])


def table(rows, widths, head=True, zebra=True, bold_first_col=False):
    data = [[P(str(c), "cellb" if (head and i == 0) or (bold_first_col and j == 0) else "cell")
             for j, c in enumerate(r)] for i, r in enumerate(rows)]
    t = Table(data, colWidths=widths, repeatRows=1 if head else 0)
    style = [("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor(GRID)),
             ("VALIGN", (0, 0), (-1, -1), "TOP"),
             ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4),
             ("TOPPADDING", (0, 0), (-1, -1), 2.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5)]
    if head:
        style += [("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e6ebf2"))]
    if zebra:
        for i in range(1 if head else 0, len(rows)):
            if i % 2 == 0:
                style.append(("BACKGROUND", (0, i), (-1, i), C_ROW))
    t.setStyle(TableStyle(style))
    return t


def boxed(flow, color="#1f3b5c", bg="#f3f6fa"):
    t = Table([[flow]], colWidths=[17 * cm])
    t.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), 1, colors.HexColor(color)),
                           ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(bg)),
                           ("LEFTPADDING", (0, 0), (-1, -1), 8), ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                           ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
    return t


# ----------------------------------------------------------------------------------------------
# Datos
# ----------------------------------------------------------------------------------------------

def load():
    con = sqlite3.connect(os.path.join(RES, "orb_study.sqlite"))
    e = pd.read_sql("SELECT * FROM events WHERE break_dir != 'none'", con)
    cuts = {}
    for (s, n), g in e.groupby(["session", "or_min"]):
        cuts[(s, n)] = tuple(g.or_vs_adr.dropna().quantile([1 / 3, 2 / 3]).values)
    e["ter"] = [("n/d" if not np.isfinite(v) else "pequeño" if v < cuts[(s, n)][0] else
                 "medio" if v < cuts[(s, n)][1] else "grande") for s, n, v in zip(e.session, e.or_min, e.or_vs_adr)]
    grid = pd.read_csv(os.path.join(RES, "strategy_grid.csv"))
    return e, grid, cuts


def pct(x):
    return f"{100 * x:.0f} %"


def before(g, ext, ret):
    te, tr = g[f"t_ext_{ext}"], g[f"t_ret_{ret}"]
    return (te.notna() & (tr.isna() | (te < tr))).mean()


# ----------------------------------------------------------------------------------------------
# Figuras
# ----------------------------------------------------------------------------------------------

def fig_levels(path):
    """Esquema del rango de apertura, Fibonacci, ruptura, retest y proyección 1.618."""
    fig, ax = plt.subplots(figsize=(7.2, 3.6))
    H, L = 1.0, 0.0
    lv = {"1 (mínimo del OR)": 0.0, "0,5": 0.5, "0 (máximo, nivel roto)": 1.0}
    ax.axvspan(0, 15, color="#e6ebf2", lw=0)
    ax.text(7.5, 1.72, "Rango de apertura\n15 o 20 min", ha="center", fontsize=8, color=INK2)
    for y, txt in [(H, "Máximo del rango = nivel roto (retroceso 0)"), (L, "Mínimo del rango = extremo opuesto (retroceso 1)")]:
        ax.axhline(y, color=BLUE, lw=1.6)
        ax.text(101, y, txt, va="center", fontsize=7.5, color=BLUE)
    for f in [0.236, 0.382, 0.5, 0.618, 0.786]:
        y = H - f
        ax.axhline(y, color=BLUE, lw=0.7, ls=":", alpha=0.8 if f == 0.5 else 0.5)
        ax.text(101, y, f"retroceso {f:g}".replace(".", ","), va="center", fontsize=6.8, color=INK2)
    for e_, name in [(0.272, "1,272"), (0.618, "1,618 = take profit"), (1.0, "2,0")]:
        y = H + e_
        is_tp = e_ == 0.618
        ax.axhline(y, color=GREEN if is_tp else GRID, lw=2 if is_tp else 0.9, ls="-" if is_tp else "--")
        ax.text(101, y, f"extensión {name}", va="center", fontsize=7.5 if is_tp else 6.8,
                color=GREEN if is_tp else INK2, fontweight="bold" if is_tp else None)
    # trayectoria ejemplo
    xs = [0, 3, 6, 9, 12, 15, 18, 21, 26, 32, 38, 44, 52, 60, 68, 78, 88, 96]
    ys = [0.5, 0.8, 0.3, 0.9, 0.2, 0.7, 1.15, 1.25, 1.05, 0.95, 1.0, 1.2, 1.35, 1.3, 1.45, 1.62, 1.55, 1.6]
    ax.plot(xs, ys, color=INK, lw=1.4)
    ax.annotate("Ruptura: primera vela\nque CIERRA fuera", xy=(18, 1.15), xytext=(17, 2.05), fontsize=7.5,
                arrowprops=dict(arrowstyle="->", color=INK2), color=INK)
    ax.annotate("Retest: vuelve a tocar\nel nivel roto", xy=(32, 0.95), xytext=(28, 0.35), fontsize=7.5,
                arrowprops=dict(arrowstyle="->", color=INK2), color=INK)
    ax.annotate("1,618 alcanzado ✓", xy=(78, 1.62), xytext=(58, 1.95), fontsize=7.5,
                arrowprops=dict(arrowstyle="->", color=GREEN), color=GREEN)
    ax.annotate("", xy=(98, H), xytext=(98, H + 0.618), arrowprops=dict(arrowstyle="<->", color=GREEN, lw=1))
    ax.text(96, H + 0.3, "0,618 × R", ha="right", fontsize=7, color=GREEN)
    ax.annotate("", xy=(-3, L), xytext=(-3, H), arrowprops=dict(arrowstyle="<->", color=BLUE, lw=1))
    ax.text(-4, 0.5, "R", ha="right", va="center", fontsize=8, color=BLUE)
    ax.set_xlim(-8, 100)
    ax.set_ylim(-0.15, 2.25)
    ax.axis("off")
    fig.savefig(path, dpi=220, bbox_inches="tight")
    plt.close(fig)


def fig_tree(path, e):
    """Árbol de escenarios con porcentajes (NY y Londres, OR 15)."""
    fig, axes = plt.subplots(2, 1, figsize=(7.4, 4.4))
    for ax, ses, txt in zip(axes, ["London", "NewYork"], ["Londres · OR 15 min", "Nueva York · OR 15 min"]):
        g = e[(e.session == ses) & (e.or_min == 15)]
        sc = g.scenario.value_counts(normalize=True)
        ret = 1 - sc.get("directa", 0)
        opp = sc.get("giro_continua", 0) + sc.get("giro_rechazo", 0)
        nodes = [
            (0.04, 0.45, f"Ruptura\n(n = {len(g)})", INK),
            (0.27, 0.85, f"No vuelve\n{pct(sc.get('directa', 0))}", "#0f3f80"),
            (0.27, 0.30, f"Vuelve al nivel roto\n{pct(ret)}", INK),
            (0.57, 0.80, f"Continúa en la 1.ª dirección\n{pct(sc.get('retest_continua', 0))}", BLUE),
            (0.57, 0.40, f"Va al otro extremo\n{pct(opp)}", INK),
            (0.57, 0.00, f"Se queda en rango\n{pct(sc.get('rango', 0))}", "#888888"),
            (0.88, 0.60, f"Rompe y continúa\n{pct(sc.get('giro_continua', 0))}", ORANGE),
            (0.88, 0.20, f"Rechazado\n{pct(sc.get('giro_rechazo', 0))}", "#b07d00"),
        ]
        edges = [(0, 1), (0, 2), (2, 3), (2, 4), (2, 5), (4, 6), (4, 7)]
        for a, b in edges:
            ax.plot([nodes[a][0], nodes[b][0]], [nodes[a][1], nodes[b][1]], color="#bdbdbd", lw=1.1, zorder=0)
        for x, y, t, c in nodes:
            ax.text(x, y, t, ha="center", va="center", fontsize=7, color=c,
                    bbox=dict(boxstyle="round,pad=0.3", fc="white", ec=c, lw=0.8))
        ax.set_title(txt, fontsize=8.5, loc="left")
        ax.set_xlim(-0.06, 1.02)
        ax.set_ylim(-0.15, 1.0)
        ax.axis("off")
    fig.text(0.01, -0.03, "Porcentajes sobre el total de rupturas, 2022-2026, NAS100 + US500. «Continúa» = llega a 1,272 "
             "antes de tocar el extremo opuesto.", fontsize=6.5, color=INK2)
    fig.savefig(path, dpi=220, bbox_inches="tight")
    plt.close(fig)


# ----------------------------------------------------------------------------------------------
# Documento
# ----------------------------------------------------------------------------------------------

def footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("DV", 7)
    canvas.setFillColor(colors.HexColor(INK2))
    canvas.drawString(2 * cm, 1.2 * cm, "Guía ORB Londres/NY + Fibonacci · estudio NAS100 + US500, 1 min, 2022-2026 · "
                                         "material educativo, no es asesoramiento financiero")
    canvas.drawRightString(19 * cm, 1.2 * cm, f"{doc.page}")
    canvas.restoreState()


def build():
    os.makedirs(FIG, exist_ok=True)
    e, grid, cuts = load()
    fig_levels(os.path.join(FIG, "niveles.png"))
    fig_tree(os.path.join(FIG, "arbol.png"), e)

    # --- cifras ---
    def g_(s, n=15, t=None):
        g = e[(e.session == s) & (e.or_min == n)]
        return g if t is None else g[g.ter == t]

    ref = []
    for name, ev in [("Vuelve al nivel roto (retest)", lambda g: g.retest.astype(float).gt(0).mean()),
                     ("Retrocede al 50 % del rango", lambda g: g.t_ret_0500.notna().mean()),
                     ("Toca el extremo opuesto (100 %)", lambda g: g.t_ret_1000.notna().mean()),
                     ("Llega a la extensión 1,272", lambda g: g.t_ext_0272.notna().mean()),
                     ("Llega a la extensión 1,618", lambda g: g.t_ext_0618.notna().mean()),
                     ("1,618 antes de tocar el extremo opuesto", lambda g: before(g, "0618", "1000")),
                     ("1,618 antes de retroceder al 50 %", lambda g: before(g, "0618", "0500"))]:
        ref.append([name] + [pct(ev(g_(s, n))) for s in ["London", "NewYork"] for n in [15, 20]])

    size_rows = []
    for t in ["pequeño", "medio", "grande"]:
        r = [t.capitalize()]
        for s in ["London", "NewYork"]:
            g = g_(s, 15, t)
            r += [pct(g.t_ret_1000.notna().mean()), pct(g.t_ext_0618.notna().mean()), pct(before(g, "0618", "1000"))]
        size_rows.append(r)

    def cond(g, after):
        if after == "50":
            s = g[g.t_ret_0500.notna() & (g.t_ext_0618.isna() | (g.t_ext_0618 > g.t_ret_0500))]
        else:
            s = g[g.t_ret_1000.notna() & (g.t_ext_0618.isna() | (g.t_ext_0618 > g.t_ret_1000))]
        return s.t_ext_0618.notna().mean()

    state_rows = []
    for t in ["pequeño", "medio", "grande", None]:
        r = [(t or "todos").capitalize()]
        for s in ["London", "NewYork"]:
            g = g_(s, 15, t)
            r += [pct(g.t_ext_0618.notna().mean()), pct(cond(g, "50")), pct(cond(g, "100"))]
        state_rows.append(r)

    # rejilla: combinaciones clave, IS + OOS juntos
    def comb(ses, entry, stop, tgt):
        x = grid[(grid.symbol == "ALL") & (grid.session == ses) & (grid.or_min == 15) & (grid.model == "continuacion")
                 & (grid.entry == entry) & (grid.stop == stop) & (grid.target == tgt)].iloc[0]
        n = x.IS_n + x.OOS_n
        win = (x.IS_win_pct * x.IS_n + x.OOS_win_pct * x.OOS_n) / n
        rg = (x.IS_exp_R_gross * x.IS_n + x.OOS_exp_R_gross * x.OOS_n) / n
        rn = (x.IS_exp_R * x.IS_n + x.OOS_exp_R * x.OOS_n) / n
        return int(n), win, rg, rn

    be_rows = []
    for entry, etxt in [("0.0", "Límite en el nivel roto (0)"), ("0.382", "Límite en el retroceso 0,382"),
                        ("break", "Al cierre de la vela de ruptura")]:
        for stop in [1.0, 0.786]:
            for tgt, ttxt in [(0.618, "1,618"), (0.272, "1,272")]:
                n, win, rg, rn = comb("NewYork", entry, stop, tgt)
                if entry == "break":
                    need = "—"
                else:
                    ex = -float(entry)
                    need = f"{100 * (ex + stop) / ((ex + stop) + (tgt - ex)):.0f} %"
                be_rows.append([etxt, f"{stop:g}".replace(".", ","), ttxt, n, f"{win:.0f} %", need,
                                f"{rg:+.2f}", f"{rn:+.2f}"])

    nyg = g_("NewYork")
    p_ret = nyg.retest.astype(float).gt(0).mean()

    # --- documento ---
    doc = SimpleDocTemplate(PDF, pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm, topMargin=1.6 * cm,
                            bottomMargin=1.8 * cm, title="Guía ORB Londres/NY + Fibonacci",
                            author="Estudio ORB (orb/)")
    S = []
    S += [P("Guía: cómo leer el indicador ORB + Fibonacci y cuándo entrar", "h1"),
          P("Rango de apertura de Londres (08:00) y Nueva York (09:30) en Nasdaq 100 y S&amp;P 500 · "
            f"probabilidades medidas con velas de 1 minuto de 2022 a 2026 ({len(e):,} rupturas)".replace(",", "."), "sub"),
          boxed(P("<b>Aviso.</b> Las probabilidades describen lo que pasó en el pasado y no garantizan nada. En el "
                  "estudio, <b>ninguna regla fija de entrada, stop y objetivo sobre el rango de apertura fue rentable "
                  "por sí sola</b> después de costes. Esta guía explica cómo usar las probabilidades para decidir y "
                  "gestionar; practica en demo antes de arriesgar dinero.", "box"), "#c2441a", "#fdf3ef"),
          Spacer(1, 6)]

    # 1. Conceptos
    S += [P("1. Los conceptos en una figura", "h2"),
          Image(os.path.join(FIG, "niveles.png"), width=17 * cm, height=8.5 * cm),
          table([["Término", "Qué es"],
                 ["Rango de apertura (OR)", "Máximo y mínimo de los primeros 15 o 20 minutos desde la apertura. "
                                            "<b>R</b> = máximo − mínimo."],
                 ["Ruptura", "La primera vela que <b>cierra</b> fuera del rango. Una mecha que sale y vuelve no cuenta."],
                 ["Nivel roto", "El extremo del rango por el que sale el precio (máximo si rompe al alza)."],
                 ["Retest", "El precio vuelve a tocar el nivel roto después de la ruptura."],
                 ["Retrocesos 0,236 … 1", "Niveles dentro del rango medidos desde el nivel roto: 0,5 es la mitad y "
                                          "1 es el extremo opuesto."],
                 ["Extensiones 1,272 / 1,618 / 2,0", "Fibonacci trazado del extremo opuesto (0) al nivel roto (1). "
                                                     "El 1,618 está 0,618 × R más allá del nivel roto."],
                 ["Tamaño del rango", "R comparado con el rango medio de la sesión de Nueva York de los 20 días "
                                      "anteriores: pequeño, medio o grande (terciles históricos)."],
                 ["Contexto previo", "Lo que hizo el precio antes de abrir (Londres 00:00-08:00, NY 04:00-09:30): al "
                                     "alza o a la baja si el cambio neto es ≥ 40 % del rango de esa ventana, si no en rango."]],
                [4.2 * cm, 12.8 * cm])]

    # 2. Indicador
    S += [PageBreak(), P("2. Qué dibuja el indicador en el gráfico", "h2"),
          table([["Elemento", "Cómo se ve", "Cómo leerlo"],
                 ["Rango de apertura", "Dos líneas gruesas (azul Londres, naranja NY) y etiqueta «OR»",
                  "Zona de referencia del día. No operes dentro de ella."],
                 ["Retrocesos", "Líneas punteadas dentro del rango; el 50 % más marcado",
                  "Donde suele volver el precio tras romper. El 50 % es el nivel de control."],
                 ["Extensiones", "Líneas discontinuas por encima y por debajo",
                  "Objetivos posibles: 1,272 (cercano), 1,618 (principal), 2,0 (ambicioso)."],
                 ["▲ / ▼ ruptura", "Etiqueta en la vela que cierra fuera del rango", "Empieza el seguimiento."],
                 ["retest", "Etiqueta pequeña al volver al nivel roto", "Ocurre casi siempre: no es una señal de fallo."],
                 ["Proyección 1,618", "Línea verde gruesa con la probabilidad",
                  "Se actualiza: baja si el precio toca el 50 % o el extremo opuesto antes de llegar."],
                 ["1,618 alcanzado ✓ / no alcanzado", "Texto de la etiqueta al llegar o al cerrar la sesión",
                  "Resultado del día, queda en el historial del gráfico."]],
                [3.6 * cm, 5.4 * cm, 8 * cm]),
          P("3. Cómo leer la tabla de registro", "h2"),
          P("La tabla se va llenando en tres etapas por cada bolsa. Las columnas <b>hoy</b> son la última apertura; "
            "las columnas <b>en el gráfico</b> suman todas las aperturas cargadas y sirven de backtesting."),
          table([["Fila", "Qué significa", "Qué hacer con ella"],
                 ["1 · Antes de la apertura", "Al alza, a la baja o en rango", "Contexto. Influye poco en el resultado."],
                 ["Rompe al alza", "Probabilidad de que la primera ruptura sea alcista (≈ 50-54 %)",
                  "Es casi una moneda al aire: <b>no apuestes la dirección antes de la ruptura</b>."],
                 ["2 · Tamaño del rango", "Pequeño, medio o grande", "La condición que más cambia las probabilidades."],
                 ["3 · Ruptura", "▲ o ▼ con la hora, o «esperando»", "Desde aquí cuentan las demás filas."],
                 ["Vuelve / 50 % / Extremo opuesto / 1.618 / Vuelve y continúa / Gira y continúa",
                  "Probabilidad histórica de cada condición para ese tamaño de rango",
                  "Úsalas para colocar entrada, stop y objetivo (sección 5)."],
                 ["✓  …  ✗", "✓ ya se cumplió · … sigue posible · ✗ terminó la sesión sin cumplirse", ""],
                 ["pron. X % · real Y %", "Probabilidad media que se dio frente a lo que pasó en las aperturas del gráfico",
                  "Si real ≈ pron., las probabilidades funcionan en ese símbolo y proveedor. Si difieren mucho, desconfía."],
                 ["Escenario", "Resultado final al cerrar la sesión", "Para tu diario de operaciones."]],
                [4.4 * cm, 6.2 * cm, 6.4 * cm])]

    # 4. Probabilidades de referencia
    S += [PageBreak(), P("4. Probabilidades de referencia", "h2"),
          P("Después de la ruptura (porcentaje de días en que ocurre antes del fin de la sesión: 12:00 en Londres, "
            "16:00 en Nueva York):"),
          table([["Condición", "Londres 15m", "Londres 20m", "NY 15m", "NY 20m"]] + ref,
                [6.6 * cm, 2.6 * cm, 2.6 * cm, 2.6 * cm, 2.6 * cm]),
          Spacer(1, 6),
          Image(os.path.join(FIG, "arbol.png"), width=15 * cm, height=9.2 * cm),
          P("Según el tamaño del rango (OR 15 min):", "h3"),
          table([["Tamaño", "Londres: extremo opuesto", "Londres: llega a 1,618", "Londres: 1,618 antes del opuesto",
                  "NY: extremo opuesto", "NY: llega a 1,618", "NY: 1,618 antes del opuesto"]] + size_rows,
                [2 * cm] + [2.5 * cm] * 6),
          P("Probabilidad de llegar a 1,618 según lo que ya hizo el precio (OR 15 min):", "h3"),
          table([["Tamaño", "Londres al romper", "Londres si ya tocó el 50 %", "Londres si ya tocó el opuesto",
                  "NY al romper", "NY si ya tocó el 50 %", "NY si ya tocó el opuesto"]] + state_rows,
                [2 * cm] + [2.5 * cm] * 6),
          P("Lectura: un rango <b>pequeño</b> se rompe con más fuerza (llega más a 1,618) pero también se cruza más "
            "entero. Un rango <b>grande</b> se extiende menos. Si el precio ya volvió al extremo opuesto, la "
            "probabilidad de 1,618 cae a la mitad o menos: la idea original está debilitada.", "small")]

    # 5. Regla de oro
    S += [PageBreak(), P("5. La regla de oro: probabilidad frente a punto de equilibrio", "h2"),
          P("Una probabilidad alta no basta. Lo que importa es si supera el porcentaje de aciertos que necesitas "
            "para no perder con tu stop y tu objetivo:"),
          boxed(P("<b>Aciertos necesarios = riesgo / (riesgo + beneficio)</b><br/>"
                  "Ejemplo: entras en el nivel roto, stop en el extremo opuesto (riesgo = 1 R) y objetivo en 1,618 "
                  "(beneficio = 0,618 R). Necesitas acertar 1 / 1,618 = <b>62 %</b>. Históricamente se llega a 1,618 "
                  "antes que al extremo opuesto alrededor del 59-66 % de las veces: <b>prácticamente empatado, y "
                  "negativo tras costes</b>.", "box")),
          Spacer(1, 6),
          P("Resultado real de estas combinaciones en Nueva York, OR 15 min, 2022-2026 (coste 1 pb por lado; "
            "«R» = resultado medio por operación en unidades de riesgo):"),
          table([["Entrada", "Stop", "Objetivo", "Operac.", "Llega al objetivo", "Necesita",
                  "R bruto", "R neto"]] + be_rows,
                [4.4 * cm, 1.2 * cm, 1.8 * cm, 1.6 * cm, 2.4 * cm, 1.9 * cm, 1.8 * cm, 1.9 * cm]),
          P("Ninguna combinación supera con claridad su punto de equilibrio. Por eso esta guía no da una regla "
            "automática: las probabilidades sirven para <b>filtrar</b> (solo operar cuando hay ventaja adicional), "
            "<b>colocar</b> stop y objetivo con sentido, y <b>salir</b> cuando la probabilidad cae.", "small")]

    # 5b. De 1.618 a 2.0 (agente de estrategia)
    ext = os.path.join(RES, "strategy")
    pt = pd.read_csv(os.path.join(ext, "ext2_prob_tam_rango.csv"))
    pg = pd.read_csv(os.path.join(ext, "ext2_prob_general.csv"))
    mg = pd.read_csv(os.path.join(ext, "ext2_gestion.csv"))
    e2 = []
    for t in ["pequeño", "medio", "grande", "todos"]:
        r = [t.capitalize()]
        for ses in ["London", "NewYork"]:
            q = (pg[(pg.session == ses) & (pg.or_min == 15)] if t == "todos" else
                 pt[(pt.session == ses) & (pt.or_min == 15) & (pt.tam_rango == t)]).iloc[0]
            r += [f"{q['llega_2']:.0f} %", f"{q['2_tras_volver_1.272']:.0f} %", f"{q['2_tras_volver_nivel roto']:.0f} %"]
        e2.append(r)
    g15 = pg[pg.or_min == 15]
    nr = 100 - g15["vuelve_nivel roto_antes_de_2"].mean()
    mgl = mg[mg.or_min == 15]["stop en 1.272"].mean()
    S += [P("5b. Más allá del 1,618: ¿llega a 2,0?", "h2"),
          P("Una vez que el precio toca 1,618, el indicador proyecta 2,0 (línea morada) con esta probabilidad, que "
            "baja si antes vuelve a 1,272 o al nivel roto (OR 15 min, 2022-2026):"),
          table([["Tamaño", "Londres: llega a 2,0", "Londres si volvió a 1,272", "Londres si volvió al nivel roto",
                  "NY: llega a 2,0", "NY si volvió a 1,272", "NY si volvió al nivel roto"]] + e2,
                [2 * cm] + [2.5 * cm] * 6),
          P(f"<b>Ojo con la lectura.</b> «Llega a 2,0» cuenta también los días que antes retroceden hasta el nivel roto. "
            f"Llegar a 2,0 <b>antes</b> de volver al nivel roto ocurre ≈ {nr:.0f} % de las veces, casi exactamente el "
            "62 % que necesita esa operación (entrar en 1,618, stop en el nivel roto, objetivo 2,0). Como entrada nueva "
            "en 1,618 no hay ventaja: ninguna de las variantes probadas fue positiva tras costes.", "small"),
          P(f"<b>Como gestión</b> de una operación que ya llevas desde el retest: al tocar 1,618, dejar correr hasta 2,0 "
            f"con el stop subido a 1,272 termina de media en ≈ {1 + (mgl - 1):.2f} frente a 1,618 si cobras ahí. Es "
            "prácticamente lo mismo; dejar correr solo añade variación. Una opción razonable: cerrar la mitad en 1,618 "
            "y dejar la otra mitad hacia 2,0 con el stop en 1,272.", "small")]

    # 6. Lógica de entrada
    S += [PageBreak(), P("6. Lógica a seguir antes de entrar", "h2"),
          table([["Momento", "Qué miras", "Decisión"],
                 ["Antes de la apertura", "Noticias del día (CPI, FOMC, NFP), contexto previo, rango medio diario",
                  "Con noticias fuertes en la primera hora, no operes el ORB. El contexto previo solo es informativo."],
                 ["Cierre del rango (08:15/08:20 o 09:45/09:50)", "Tamaño del rango",
                  "Pequeño: más extensión, pero también más cruces completos; stop amplio. Grande: objetivos cortos "
                  "(1,272) o no operar."],
                 ["Ruptura", "Vela que cierra fuera; probabilidades de la tabla",
                  f"<b>No persigas la vela de ruptura</b>: vuelve al nivel roto el {pct(p_ret)} de las veces. "
                  "Espera el retest."],
                 ["Retest del nivel roto", "¿Vuelve y aguanta? ¿Sigue dentro del rango sin pasar del 50 %?",
                  "Posible entrada a favor de la ruptura con stop por debajo del 0,786 o del extremo opuesto y "
                  "objetivo 1,272 / 1,618. Comprueba la regla de oro con tu stop real."],
                 ["El precio toca el 50 %", "Probabilidad de 1,618 en la etiqueta verde",
                  "Si baja de tu punto de equilibrio, reduce el objetivo a 1,272 o no entres."],
                 ["El precio toca el extremo opuesto", "Probabilidad de 1,618 muy baja",
                  "La idea de continuación queda invalidada: cierra o no entres. Una ruptura del otro lado con "
                  "cierre fuera es el escenario «gira y continúa» (≈ 1 de cada 5 días)."],
                 ["En la operación", "Objetivo 1,272 / 1,618 y hora",
                  "Si llega a 1,272 puedes mover el stop a entrada. Al tocar 1,618: cobra, o cierra la mitad y deja el resto "
                  "hacia 2,0 con el stop en 1,272 (sección 5b). Cierra antes del fin del horizonte (12:00 / 16:00)."]],
                [3.6 * cm, 5.2 * cm, 8.2 * cm])]

    # 7. Gap y riesgo
    S += [P("7. Patrón candidato: el gap de Nueva York (P5)", "h2"),
          P("Fibonacci trazado entre el <b>cierre de las 16:00 del día anterior</b> (nivel 1) y la <b>apertura de las "
            "09:30</b> (nivel 0). Con un <b>gap grande</b> (más de la mitad del rango diario medio), cuando el precio "
            "llega al cierre anterior se entra en esa misma dirección, con stop en 0,618 y objetivo en 1,618 del gap."),
          table([["", "Operaciones", "Llega al objetivo", "R neto por operación"],
                 ["2022-2024 (para elegirlo)", "95", "38 %", "+0,14"],
                 ["2025-2026 (comprobación)", "83", "40 %", "+0,27"]],
                [5.5 * cm, 3.5 * cm, 3.5 * cm, 4.5 * cm]),
          P("Es el único patrón que mantuvo resultado positivo en las dos mitades y en los dos índices (y en 4 de 5 "
            "años), pero salió de entre 240 combinaciones probadas y la muestra es pequeña (≈ 40 operaciones al año): "
            "trátalo como <b>candidato a validar</b> en demo, no como una ventaja demostrada. Pista útil: si el rango de "
            "15 min de NY rompe <b>hacia el cierre anterior</b>, el gap se cierra el 70 % de los días; si rompe a favor "
            "del gap, solo el 34 %.", "small"),
          P("8. Gestión del riesgo", "h2"),
          table([["Regla", "Por qué"],
                 ["Arriesga como máximo el 0,5-1 % de la cuenta por operación",
                  "Con un acierto del 55-65 % son normales rachas de 4-6 pérdidas seguidas."],
                 ["Calcula el tamaño con la distancia real al stop", "El rango cambia mucho de un día a otro."],
                 ["Incluye spread y comisión en la cuenta del punto de equilibrio",
                  "En Londres el rango mediano es ≈ 13 pb: los costes pesan mucho."],
                 ["Una operación por sesión y por índice", "Evita operar por revancha tras un stop."],
                 ["Anota cada operación con la probabilidad que tenías y el resultado",
                  "Así compruebas, como en la columna «en el gráfico», si tus decisiones superan al azar."]],
                [7.5 * cm, 9.5 * cm])]

    # 9. Hoja de verificación
    chk = ["¿Hay noticias de alto impacto en la primera hora? → si sí, no opero el ORB.",
           "¿Cerró el rango? Tamaño: pequeño / medio / grande.",
           "¿Hubo ruptura con CIERRE fuera del rango? Dirección: ▲ / ▼.",
           "¿Esperé el retest en vez de perseguir la vela de ruptura?",
           "Stop elegido: retroceso ______ · Objetivo: extensión ______",
           "Aciertos necesarios = riesgo / (riesgo + beneficio) = ______ %",
           "Probabilidad histórica del objetivo (tabla / etiqueta verde) = ______ %",
           "¿La probabilidad supera con margen los aciertos necesarios más los costes? → si no, no entro.",
           "¿El precio ya tocó el extremo opuesto? → si sí, no entro a favor de la primera ruptura.",
           "Riesgo en dinero ≤ 1 % de la cuenta · Tamaño de posición calculado.",
           "Hora límite para cerrar: 12:00 (Londres) / 16:00 (Nueva York).",
           "Anotado en el diario: probabilidad, entrada, stop, objetivo, resultado."]
    rows = [["☐", P(c, "cell")] for c in chk]
    t = Table([[P(r[0], "cell"), r[1]] for r in rows], colWidths=[0.8 * cm, 16.2 * cm])
    t.setStyle(TableStyle([("LINEBELOW", (0, 0), (-1, -1), 0.4, colors.HexColor(GRID)),
                           ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("TOPPADDING", (0, 0), (-1, -1), 6),
                           ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
    S += [Spacer(1, 4), KeepTogether([P("9. Hoja de verificación antes de entrar (para imprimir)", "h2"), t])]

    doc.build(S, onFirstPage=footer, onLaterPages=footer)
    print(PDF)


if __name__ == "__main__":
    build()
