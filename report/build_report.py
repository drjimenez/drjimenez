"""
build_report.py — Genera report/TTFM_Report.pdf a partir de results/ (summary.json, CSV y PNG).

Uso:  python3 report/build_report.py
Requisitos: reportlab, matplotlib, pandas (ver requirements.txt).
"""
from __future__ import annotations

import json
import os
from datetime import date

import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyArrowPatch

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (Image, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table,
                                TableStyle, ListFlowable, ListItem)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES = os.path.join(ROOT, "results")
OUT_DIR = os.path.join(ROOT, "report")
FIG_DIR = os.path.join(OUT_DIR, "figs")
PDF = os.path.join(OUT_DIR, "TTFM_Report.pdf")

PROFILES = ["intradia_4H_15m", "swing_1D_1H"]
PLABEL = {"intradia_4H_15m": "Intradía 4H -> 15m", "swing_1D_1H": "Swing 1D -> 1H"}
CLASSES = ["Forex", "Cripto", "Indices", "Commodities"]

# Paleta coherente con los gráficos de results/
INK, INK2, GRID, SURFACE = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"
BLUE, ORANGE, GREEN, RED, YELLOW = "#2a78d6", "#eb6834", "#1baf7a", "#e34948", "#eda100"
C_HEAD = colors.HexColor("#1f3b5c")
C_ROW = colors.HexColor("#f2f4f7")
C_POS = colors.HexColor("#0e7a4f")
C_NEG = colors.HexColor("#b3261e")

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "axes.edgecolor": GRID, "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
    "text.color": INK, "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6,
    "axes.spines.top": False, "axes.spines.right": False, "font.size": 9, "legend.frameon": False,
})


# ----------------------------------------------------------------------------- utilidades
def latin1(s: str) -> str:
    """Las fuentes estándar de reportlab (Helvetica) cubren latin-1: sustituye el resto."""
    rep = {"→": "->", "←": "<-", "✓": "OK", "✕": "x", "▲": "(alcista)", "▼": "(bajista)", "≥": ">=",
           "≤": "<=", "Ⓢ": "S", "×": "x", "−": "-", "–": "-", "—": "-", "…": "...", "∓": "-/+", "±": "+/-"}
    for k, v in rep.items():
        s = s.replace(k, v)
    return s.encode("latin-1", "replace").decode("latin-1")


def fmt(v, d=2, pct=False, sign=False):
    if v is None or (isinstance(v, float) and (np.isnan(v) or np.isinf(v))):
        return "-"
    s = f"{v:+.{d}f}" if sign else f"{v:.{d}f}"
    s = s.replace(".", ",")
    return s + ("%" if pct else "")


def load():
    with open(os.path.join(RES, "summary.json"), encoding="utf-8") as f:
        S = json.load(f)
    M = {p: pd.read_csv(os.path.join(RES, f"metrics_{p}.csv")) for p in PROFILES}
    T = {p: pd.read_csv(os.path.join(RES, f"trades_{p}.csv")) for p in PROFILES}
    MO = {p: pd.read_csv(os.path.join(RES, f"monthly_returns_{p}.csv"), index_col=0) for p in PROFILES}
    SENS = pd.read_csv(os.path.join(RES, "sensitivity.csv"))
    return S, M, T, MO, SENS


# ----------------------------------------------------------------------------- figuras propias
def fig_fractal_diagram(path):
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(10, 4.2), gridspec_kw=dict(width_ratios=[1, 1.35]))
    for ax in (a1, a2):
        ax.grid(False)
        ax.set_xticks([]); ax.set_yticks([])
        for sp in ax.spines.values():
            sp.set_visible(False)

    def candle(ax, x, o, h, l, c, w=0.6, alpha=1.0, ls="-"):
        col = GREEN if c >= o else RED
        ax.plot([x, x], [l, h], color=INK2, lw=1.2, alpha=alpha, ls=ls, zorder=1)
        ax.add_patch(Rectangle((x - w / 2, min(o, c)), w, abs(c - o) or 0.02, facecolor=col, edgecolor=col,
                               alpha=alpha, zorder=2, ls=ls))

    # --- panel HTF ---
    candle(a1, 1, 10.0, 11.0, 8.0, 9.0)            # C1
    candle(a1, 2, 9.0, 10.2, 6.8, 8.8)             # C2: barre low C1 y cierra dentro
    candle(a1, 3, 8.8, 10.4, 7.6, 10.1, alpha=0.45, ls="--")  # C3 en formación
    a1.plot([0.6, 4.7], [8.0, 8.0], color=BLUE, lw=1)
    a1.text(0.45, 8.0, "low C1", color=BLUE, va="center", ha="right", fontsize=8)
    a1.plot([1.7, 4.7], [10.2, 10.2], color=ORANGE, lw=1, ls="--")
    a1.text(3.45, 10.28, "high C2 = TP", color=ORANGE, va="bottom", fontsize=8)
    a1.plot([1.7, 4.7], [6.8, 6.8], color=ORANGE, lw=1, ls="--")
    a1.text(3.45, 6.72, "low C2 = SL\n(- buffer ATR)", color=ORANGE, va="top", fontsize=8)
    a1.annotate("sweep", xy=(2, 6.85), xytext=(1.25, 6.4), fontsize=8, color=RED,
                arrowprops=dict(arrowstyle="->", color=RED))
    for x, t in ((1, "C1"), (2, "C2"), (3, "C3")):
        a1.text(x, 11.4, t, ha="center", fontsize=10, fontweight="bold")
    a1.text(2, 5.7, "C2 barre el low de C1 y cierra dentro\n-> sesgo ALCISTA para C3", ha="center",
            fontsize=8, color=INK2)
    a1.set_xlim(0.0, 4.9); a1.set_ylim(5.2, 11.9)
    a1.set_title("Temporalidad alta (HTF): C1 - C2 - C3", fontsize=10)

    # --- panel LTF (inicio de C3) ---
    seq = [(8.55, 8.8, 8.5, 8.7), (8.7, 8.75, 8.3, 8.35), (8.35, 8.4, 7.9, 8.0), (8.0, 8.1, 7.65, 7.8),
           (7.8, 8.2, 7.7, 8.15), (8.15, 8.9, 8.1, 8.85), (8.85, 9.2, 8.7, 9.1), (9.1, 9.6, 9.0, 9.5),
           (9.5, 10.25, 9.4, 10.2)]
    for i, (o, h, l, c) in enumerate(seq):
        candle(a2, i + 1, o, h, l, c, w=0.55)
    a2.plot([1.72, 9.6], [8.7, 8.7], color="#a23bc4", lw=1.3, ls=":")
    a2.text(9.7, 8.7, "nivel CISD\n(apertura 1ª vela\nde la serie bajista)", color="#a23bc4", fontsize=7.5,
            va="center")
    a2.add_patch(Rectangle((1.6, 7.55), 2.8, 1.35, fill=False, ec=RED, lw=0.8, ls="--"))
    a2.text(3.0, 7.4, "serie bajista", color=RED, fontsize=7.5, ha="center", va="top")
    a2.annotate("CISD: cierre por encima\n-> ENTRADA long al cierre", xy=(6, 8.85), xytext=(3.2, 9.85),
                fontsize=8, color=INK, arrowprops=dict(arrowstyle="->", color=INK))
    a2.axhline(6.9, color=RED, lw=1, ls="--"); a2.text(0.6, 6.95, "SL", color=RED, fontsize=8, va="bottom")
    a2.axhline(10.2, color=GREEN, lw=1, ls="--"); a2.text(0.6, 10.25, "TP", color=GREEN, fontsize=8, va="bottom")
    a2.axvspan(0.5, 12.5, ymin=0, ymax=1, color=GREEN, alpha=0.04)
    a2.text(6.5, 6.55, "ventana de entrada: primeras maxEntryBars (12) velas LTF de C3", ha="center",
            fontsize=7.5, color=INK2)
    a2.set_xlim(0.3, 12.8); a2.set_ylim(6.3, 10.7)
    a2.set_title("Temporalidad baja (LTF) dentro de C3: CISD", fontsize=10)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def fig_costs(S, path):
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.4), sharey=False)
    for ax, p in zip(axes, PROFILES):
        gross = S["gross_no_costs"][p]
        names = CLASSES + ["GLOBAL"]
        net = [S["profiles"][p]["by_class"][c]["expectancy_R"] if c != "GLOBAL"
               else S["profiles"][p]["global_"]["expectancy_R"] for c in names]
        gr = [gross[c]["expectancy_R"] for c in names]
        x = np.arange(len(names))
        ax.bar(x - 0.2, gr, 0.38, color=BLUE, label="Sin costes (bruto)")
        ax.bar(x + 0.2, net, 0.38, color=ORANGE, label="Con costes (neto)")
        ax.axhline(0, color=INK2, lw=0.8)
        ax.set_xticks(x); ax.set_xticklabels(names, fontsize=8)
        ax.set_ylabel("Expectativa por trade (R)")
        ax.set_title(PLABEL[p], fontsize=10)
        ax.legend(fontsize=8, loc="lower left")
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def fig_stop_vs_cost(T, S, path):
    rt = (S["params"]["commission"] + S["params"]["slippage"]) * 2 * 100
    fig, ax = plt.subplots(figsize=(10, 3.2))
    x = np.arange(len(CLASSES))
    for k, (p, col) in enumerate(zip(PROFILES, (BLUE, ORANGE))):
        t = T[p].copy()
        t["risk_pct"] = (t.entry_price - t.sl).abs() / t.entry_price * 100
        med = [t[t.asset_class == c].risk_pct.median() for c in CLASSES]
        ax.bar(x + (k - 0.5) * 0.38, med, 0.38, color=col, label=f"Distancia mediana al SL - {PLABEL[p]}")
    ax.axhline(rt, color=RED, lw=1.4, ls="--")
    ax.text(len(CLASSES) - 0.45, rt, f" coste ida+vuelta {rt:.2f}%", color=RED, va="bottom", ha="right", fontsize=8)
    ax.set_xticks(x); ax.set_xticklabels(CLASSES)
    ax.set_ylabel("% del precio de entrada")
    ax.legend(fontsize=8, loc="upper left")
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def fig_sensitivity(SENS, path):
    piv = SENS.pivot(index="minRR", columns="slBufferATR", values="portfolio_return_pct")
    pf = SENS.pivot(index="minRR", columns="slBufferATR", values="trades")
    fig, ax = plt.subplots(figsize=(6.2, 3.0))
    v = np.abs(piv.values).max()
    im = ax.imshow(piv.values, cmap="RdBu", vmin=-v, vmax=v, aspect="auto")
    ax.grid(False)
    ax.set_xticks(range(piv.shape[1])); ax.set_xticklabels([f"{c:g}" for c in piv.columns])
    ax.set_yticks(range(piv.shape[0])); ax.set_yticklabels([f"{r:g}" for r in piv.index])
    ax.set_xlabel("slBufferATR"); ax.set_ylabel("minRR")
    for i in range(piv.shape[0]):
        for j in range(piv.shape[1]):
            val = piv.values[i, j]
            ax.text(j, i, f"{val:.1f}%\n({int(pf.values[i, j])} tr.)", ha="center", va="center", fontsize=8,
                    color="white" if abs(val) > v * 0.55 else INK)
    fig.colorbar(im, ax=ax, label="Retorno cartera (%)")
    ax.set_title("Sensibilidad intradía 4H -> 15m (neto de costes)", fontsize=10)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


# ----------------------------------------------------------------------------- estilos PDF
ss = getSampleStyleSheet()
H1 = ParagraphStyle("H1", parent=ss["Heading1"], fontName="Helvetica-Bold", fontSize=17, textColor=C_HEAD,
                    spaceBefore=4, spaceAfter=10)
H2 = ParagraphStyle("H2", parent=ss["Heading2"], fontName="Helvetica-Bold", fontSize=12.5, textColor=C_HEAD,
                    spaceBefore=10, spaceAfter=5)
BODY = ParagraphStyle("Body", parent=ss["BodyText"], fontName="Helvetica", fontSize=9.6, leading=13.6,
                      alignment=TA_JUSTIFY, spaceAfter=5)
SMALL = ParagraphStyle("Small", parent=BODY, fontSize=8, leading=10.5, textColor=colors.HexColor("#52514e"))
CAP = ParagraphStyle("Cap", parent=SMALL, alignment=TA_CENTER, spaceBefore=2, spaceAfter=8)
CELL = ParagraphStyle("Cell", parent=BODY, fontSize=8, leading=10, alignment=0, spaceAfter=0)
BOX = ParagraphStyle("Box", parent=BODY, backColor=colors.HexColor("#eef3f9"), borderColor=C_HEAD,
                     borderWidth=0.6, borderPadding=7, spaceBefore=6, spaceAfter=10)


def P(t, st=BODY):
    return Paragraph(latin1(t), st)


def bullets(items, st=BODY):
    return ListFlowable([ListItem(P(i, st), leftIndent=12, value="-") for i in items], bulletType="bullet",
                        start="-", leftIndent=12, bulletFontSize=8)


def img(path, width_cm=17.0, caption=None):
    from PIL import Image as PILImage
    w, h = PILImage.open(path).size
    width = width_cm * cm
    parts = [Image(path, width=width, height=width * h / w)]
    if caption:
        parts.append(P(caption, CAP))
    return KeepTogether(parts)


def table(rows, col_w=None, num_from=1, color_cols=(), font=7.8, zebra=True):
    data = [[latin1(str(c)) for c in r] for r in rows]
    t = Table(data, colWidths=col_w, repeatRows=1, hAlign="CENTER")
    st = [("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"), ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
          ("FONTSIZE", (0, 0), (-1, -1), font), ("BACKGROUND", (0, 0), (-1, 0), C_HEAD),
          ("TEXTCOLOR", (0, 0), (-1, 0), colors.white), ("ALIGN", (num_from, 0), (-1, -1), "RIGHT"),
          ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("TOPPADDING", (0, 0), (-1, -1), 1.8),
          ("BOTTOMPADDING", (0, 0), (-1, -1), 1.8), ("LINEBELOW", (0, 0), (-1, -1), 0.25, colors.HexColor("#d0d4da"))]
    if zebra:
        for i in range(1, len(data)):
            if i % 2 == 0:
                st.append(("BACKGROUND", (0, i), (-1, i), C_ROW))
    for j in color_cols:
        for i in range(1, len(data)):
            s = data[i][j].replace("%", "").replace(",", ".")
            try:
                v = float(s)
            except ValueError:
                continue
            st.append(("TEXTCOLOR", (j, i), (j, i), C_POS if v > 0 else C_NEG if v < 0 else colors.black))
    for i, r in enumerate(data):
        if r[0] in ("GLOBAL", "CARTERA"):
            st.append(("FONTNAME", (0, i), (-1, i), "Helvetica-Bold"))
    t.setStyle(TableStyle(st))
    return t


def on_page(canvas, doc):
    if doc.page == 1:
        return
    canvas.saveState()
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(colors.HexColor("#7a7a7a"))
    canvas.drawString(2 * cm, 1.2 * cm, latin1("TTFM - Modelo Fractal estilo TTrades | Informe de backtest"))
    canvas.drawRightString(A4[0] - 2 * cm, 1.2 * cm, f"Página {doc.page}".encode("latin-1").decode("latin-1"))
    canvas.setStrokeColor(colors.HexColor("#d0d4da"))
    canvas.line(2 * cm, 1.5 * cm, A4[0] - 2 * cm, 1.5 * cm)
    canvas.restoreState()


# ----------------------------------------------------------------------------- tablas de métricas
def metric_rows(rows_src, with_bh=True):
    head = ["Grupo", "Trades", "Win %", "PF", "Exp. (R)", "Retorno %", "Max DD %", "Sharpe"]
    if with_bh:
        head.append("B&H %")
    out = [head]
    for name, m in rows_src:
        r = [name, int(m["trades"]), fmt(m["win_rate_pct"], 1), fmt(m["profit_factor"]), fmt(m["expectancy_R"], 2, sign=True),
             fmt(m["return_pct"], 2, sign=True), fmt(m["max_dd_pct"], 2), fmt(m["sharpe_daily"], 2)]
        if with_bh:
            r.append(fmt(m["buy_hold_pct"], 2, sign=True))
        out.append(r)
    return out


def class_table(S, p):
    pr = S["profiles"][p]
    rows = [(c, pr["by_class"][c]) for c in CLASSES if c in pr["by_class"]] + [("GLOBAL", pr["global_"])]
    return table(metric_rows(rows), color_cols=(4, 5, 8))


def asset_table(M, p):
    m = M[p][M[p].level == "asset"]
    rows = [[r["name"], r["asset_class"], int(r["trades"]), fmt(r["win_rate_pct"], 1), fmt(r["profit_factor"]),
             fmt(r["expectancy_R"], 2, sign=True), fmt(r["return_pct"], 2, sign=True), fmt(r["max_dd_pct"], 2),
             fmt(r["buy_hold_pct"], 2, sign=True), int(r["cisd_signals"]), int(r["rejected_minRR"])]
            for _, r in m.iterrows()]
    head = ["Activo", "Clase", "Trades", "Win %", "PF", "Exp. (R)", "Ret. %", "Max DD %", "B&H %", "CISD",
            "Rech. RR"]
    return table([head] + rows, num_from=2, color_cols=(5, 6, 8), font=7.4)


# ----------------------------------------------------------------------------- documento
def build():
    os.makedirs(FIG_DIR, exist_ok=True)
    S, M, T, MO, SENS = load()
    fd = os.path.join(FIG_DIR, "fractal_diagram.png")
    fc = os.path.join(FIG_DIR, "costs_impact.png")
    fsc = os.path.join(FIG_DIR, "stop_vs_cost.png")
    fs = os.path.join(FIG_DIR, "sensitivity_heatmap.png")
    fig_fractal_diagram(fd)
    fig_costs(S, fc)
    fig_stop_vs_cost(T, S, fsc)
    fig_sensitivity(SENS, fs)

    pa = S["params"]
    gi, gs = S["profiles"]["intradia_4H_15m"]["global_"], S["profiles"]["swing_1D_1H"]["global_"]
    gri, grs = S["gross_no_costs"]["intradia_4H_15m"]["GLOBAL"], S["gross_no_costs"]["swing_1D_1H"]["GLOBAL"]
    swa = S["profiles"]["swing_1D_1H"]["by_asset"]
    swc = S["profiles"]["swing_1D_1H"]["by_class"]
    best_sens = SENS.sort_values("portfolio_return_pct", ascending=False).iloc[0]
    rt_cost = (pa["commission"] + pa["slippage"]) * 2 * 100
    ti = T["intradia_4H_15m"].copy()
    ti["risk_pct"] = (ti.entry_price - ti.sl).abs() / ti.entry_price * 100
    med_risk_i = ti.risk_pct.median()
    ts = T["swing_1D_1H"].copy()
    ts["risk_pct"] = (ts.entry_price - ts.sl).abs() / ts.entry_price * 100
    med_risk_s = ts.risk_pct.median()
    period = f"{S['period']['start']} a {S['period']['end']}"

    story = []
    # ------------------------------------------------------------------ portada
    story += [Spacer(1, 4.5 * cm),
              P("TTFM", ParagraphStyle("t0", parent=H1, fontSize=40, leading=46, alignment=TA_CENTER)),
              P("Modelo Fractal estilo TTrades", ParagraphStyle("t1", parent=H1, fontSize=22, leading=28,
                                                                alignment=TA_CENTER)),
              Spacer(1, 0.4 * cm),
              P("Indicador y estrategia para TradingView (Pine Script v6) y backtest independiente en Python",
                ParagraphStyle("t2", parent=BODY, fontSize=12.5, leading=17, alignment=TA_CENTER)),
              Spacer(1, 1.6 * cm),
              P(f"Período analizado: {period} (más de 7 meses)<br/>"
                "Universo: Forex, Cripto, Índices y Commodities (9 instrumentos)<br/>"
                "Perfiles: intradía 4H -> 15m y swing 1D -> 1H<br/>"
                f"Fecha del informe: {date.today().strftime('%d/%m/%Y')}",
                ParagraphStyle("t3", parent=BODY, fontSize=11, leading=17, alignment=TA_CENTER)),
              Spacer(1, 4.5 * cm),
              P("Documento de investigación. No constituye asesoramiento financiero ni recomendación de inversión. "
                "Rentabilidades pasadas simuladas no garantizan resultados futuros.",
                ParagraphStyle("t4", parent=SMALL, alignment=TA_CENTER)),
              PageBreak()]

    # ------------------------------------------------------------------ índice

    # ------------------------------------------------------------------ 1. resumen ejecutivo
    story += [P("1. Resumen ejecutivo", H1),
              P("Se ha implementado de forma mecánica el <i>fractal model</i> divulgado por TTrades: una vela de "
                "temporalidad alta (C2) barre la liquidez de la vela anterior (C1) y cierra de vuelta dentro de su "
                "rango; durante la vela siguiente (C3) se busca en temporalidad baja un <i>Change In State of "
                "Delivery</i> (CISD) que confirme el giro, con stop en el extremo barrido y objetivo en el extremo "
                "opuesto de C2. El modelo se ha codificado tres veces con la misma especificación: un indicador "
                "Pine v6, una estrategia Pine v6 para el Strategy Tester y un motor de backtest en Python que es el "
                "que produce todas las cifras de este informe."),
              P("<b>Conclusión honesta:</b> en la versión mecanizada y con costes realistas la estrategia "
                "<b>no fue rentable en intradía</b> y quedó <b>prácticamente plana en swing</b>. Las commodities "
                "(oro y plata) en el perfil swing fueron el único segmento claramente positivo.", BOX)]
    kp = [["Métrica (global, neto de costes)", PLABEL["intradia_4H_15m"], PLABEL["swing_1D_1H"]],
          ["Trades", int(gi["trades"]), int(gs["trades"])],
          ["Win rate", fmt(gi["win_rate_pct"], 1, True), fmt(gs["win_rate_pct"], 1, True)],
          ["Profit factor", fmt(gi["profit_factor"]), fmt(gs["profit_factor"])],
          ["Expectativa por trade", fmt(gi["expectancy_R"], 2, sign=True) + " R", fmt(gs["expectancy_R"], 2, sign=True) + " R"],
          ["Retorno cartera", fmt(gi["return_pct"], 2, True, True), fmt(gs["return_pct"], 2, True, True)],
          ["Máximo drawdown", fmt(gi["max_dd_pct"], 2, True), fmt(gs["max_dd_pct"], 2, True)],
          ["Retorno sin costes (bruto)", fmt(gri["return_pct"], 2, True, True), fmt(grs["return_pct"], 2, True, True)],
          ["Buy & hold medio del universo", fmt(gi["buy_hold_pct"], 2, True, True), fmt(gs["buy_hold_pct"], 2, True, True)]]
    story += [table(kp, col_w=[6.5 * cm, 4.5 * cm, 4.5 * cm]), Spacer(1, 0.3 * cm)]
    story += [bullets([
        f"<b>Intradía 4H -> 15m:</b> {int(gi['trades'])} operaciones, acierto del {fmt(gi['win_rate_pct'], 1)}% y "
        f"profit factor {fmt(gi['profit_factor'])}. Retorno de la cartera {fmt(gi['return_pct'], 2, True, True)} con "
        f"drawdown máximo de {fmt(gi['max_dd_pct'], 2, True)}. Sin costes el resultado habría sido casi nulo "
        f"({fmt(gri['return_pct'], 2, True, True)}, {fmt(gri['expectancy_R'], 2, sign=True)} R/trade): la señal no "
        "tiene ventaja estadística medible y los costes la convierten en claramente negativa.",
        f"<b>Swing 1D -> 1H:</b> {int(gs['trades'])} operaciones, acierto del {fmt(gs['win_rate_pct'], 1)}%, PF "
        f"{fmt(gs['profit_factor'])}, retorno {fmt(gs['return_pct'], 2, True, True)} (bruto "
        f"{fmt(grs['return_pct'], 2, True, True)}). La ventaja bruta es pequeña y los costes la anulan.",
        f"<b>Commodities en swing:</b> PF {fmt(swc['Commodities']['profit_factor'])} y "
        f"{fmt(swc['Commodities']['return_pct'], 2, True, True)}; XAU {fmt(swa['XAUUSDT']['return_pct'], 2, True, True)} y "
        f"XAG {fmt(swa['XAGUSDT']['return_pct'], 2, True, True)}, en un período en el que su buy &amp; hold cayó "
        f"({fmt(swa['XAUUSDT']['buy_hold_pct'], 1, True, True)} y {fmt(swa['XAGUSDT']['buy_hold_pct'], 1, True, True)}). "
        "Las muestras son pequeñas (7-12 trades por activo), por lo que no son concluyentes.",
        f"<b>Sensibilidad:</b> ninguna de las 9 combinaciones de minRR y buffer del SL probadas en intradía es "
        f"positiva; la menos mala (minRR {fmt(best_sens.minRR, 1)}, buffer {fmt(best_sens.slBufferATR, 2)} ATR) pierde "
        f"{fmt(best_sens.portfolio_return_pct, 2, True)} con solo {int(best_sens.trades)} operaciones.",
        f"<b>Causa principal de las pérdidas en intradía:</b> los stops son muy cortos (mediana {fmt(med_risk_i, 2)}% "
        f"del precio) frente a un coste de ida y vuelta de {fmt(rt_cost, 2)}%; en EURUSDT la mediana es inferior al "
        "propio coste, por lo que cada pérdida cuesta más de 2 R.",
    ])]
    story.append(PageBreak())

    # ------------------------------------------------------------------ 2. modelo
    story += [P("2. El modelo fractal (C1 / C2 / C3, sweep y CISD)", H1),
              P("La idea central del modelo es que el precio es fractal: cada vela de temporalidad alta (HTF) se "
                "construye con la misma secuencia de acumulación, manipulación y expansión que se observa en "
                "temporalidad baja (LTF). Una vela HTF que barre el extremo de la anterior y no consigue mantenerse "
                "fuera (cierra de nuevo dentro del rango) revela que la ruptura fue una toma de liquidez y no una "
                "continuación; la vela siguiente tiende entonces a desplazarse hacia el extremo opuesto."),
              bullets([
                  "<b>C1</b>: vela HTF cerrada que define el rango de referencia (su high y su low concentran "
                  "liquidez: stops y órdenes pendientes).",
                  "<b>C2</b>: vela HTF cerrada que <b>barre</b> un extremo de C1 y <b>cierra dentro</b> de su rango. "
                  "Sweep alcista: low(C2) &lt; low(C1) y close(C2) &gt; low(C1). Sweep bajista: high(C2) &gt; high(C1) "
                  "y close(C2) &lt; high(C1). Si C2 barre ambos extremos el caso es ambiguo y se descarta.",
                  "<b>C3</b>: vela HTF en curso, en la que se busca la entrada en LTF a favor del sesgo y hacia el "
                  "extremo opuesto de C2.",
                  "<b>CISD</b> (Change In State of Delivery): en sesgo alcista, el nivel es la apertura de la primera "
                  "vela de la serie más reciente de velas LTF bajistas consecutivas; un cierre LTF por encima de ese "
                  "nivel indica que el flujo pasó de vendedor a comprador y confirma la entrada. Simétrico en bajista.",
              ]),
              Spacer(1, 0.2 * cm),
              img(fd, 17, "Figura 1. Esquema del modelo: C2 barre el low de C1 y cierra dentro (sesgo alcista); "
                          "dentro de C3, el cierre LTF por encima del nivel CISD dispara la entrada. SL bajo el low de "
                          "C2 (menos un buffer de ATR) y TP en el high de C2."),
              P("La implementación construye las velas HTF a partir de las propias velas LTF (con "
                "<font face='Courier'>timeframe.change()</font> en Pine y con agregación barra a barra en Python), "
                "de modo que C1 y C2 sólo se conocen cuando están cerradas: no se usa "
                "<font face='Courier'>request.security</font> y no hay repintado ni información futura."),
              PageBreak()]

    # ------------------------------------------------------------------ 3. reglas
    story += [P("3. Reglas exactas de entrada, salida y gestión", H1),
              P("Las reglas están fijadas en <font face='Courier'>docs/SPEC.md</font> y son idénticas en el "
                "indicador, la estrategia Pine y el motor Python (las funciones de lógica de la estrategia son copia "
                "literal de las del indicador; se ha verificado con un <i>diff</i>)."),
              P("Detección del setup (en la primera vela LTF de cada nueva vela HTF)", H2),
              bullets(["C1 = penúltima vela HTF cerrada; C2 = última vela HTF cerrada; C3 = vela HTF en curso.",
                       "Sesgo +1 si sweep alcista, -1 si sweep bajista, 0 si no hay sweep o si es ambiguo.",
                       "La primera vela HTF del histórico (posiblemente incompleta) se descarta."]),
              P("Evaluación en cada vela LTF de C3 (orden conservador)", H2),
              bullets(["1) <b>Invalidación</b>: si el precio rompe el extremo barrido de C2 (low &lt; low(C2) en largo, "
                       "high &gt; high(C2) en corto) el setup se cancela.",
                       f"2) <b>Expiración</b>: si han transcurrido más de maxEntryBars = {pa['maxEntryBars']} velas LTF "
                       "de C3 (la primera vela de C3 cuenta como 1) sin CISD.",
                       "3) <b>Objetivo alcanzado</b>: si el precio toca el extremo opuesto de C2 antes del CISD, la "
                       "oportunidad se da por perdida.",
                       "4) <b>CISD</b>: cierre LTF a través del nivel CISD vigente. Cada nivel sólo puede confirmar "
                       "una vez (se consume al ser cruzado por un cierre, haya sesgo o no)."]),
              P("Entrada, stop y objetivo", H2),
              bullets(["Entrada al <b>cierre</b> de la vela LTF que confirma el CISD.",
                       f"Stop loss = extremo barrido de C2 -/+ slBufferATR x ATR14(LTF), con slBufferATR = {pa['slBufferATR']}.",
                       "Take profit = extremo opuesto de C2.",
                       f"Si R:R = recompensa / riesgo &lt; minRR = {pa['minRR']} la señal se omite, pero el setup sigue "
                       "activo y un CISD posterior (con otra serie) puede valer.",
                       "Un único trade por setup HTF y una sola posición abierta por activo; si llega una señal válida "
                       "con posición abierta se consume sin entrar."]),
              P("Gestión y costes", H2),
              bullets(["La posición se mantiene hasta SL o TP, aunque C3 haya cerrado (timeExitBars = 0, sin salida "
                       "por tiempo).",
                       "Si una misma vela LTF toca SL y TP se asume SL primero (conservador). Si la vela abre más allá "
                       "del nivel (gap) se ejecuta a la apertura.",
                       f"Riesgo fijo del {pa['risk'] * 100:g}% del equity por operación (interés compuesto), tamaño = "
                       f"riesgo / distancia al SL, con tope de nocional de {pa['maxLeverage']:g}x el equity.",
                       f"Comisión {pa['commission'] * 100:g}% por lado y slippage {pa['slippage'] * 100:g}% por lado en "
                       f"Python (coste total ida y vuelta {fmt(rt_cost, 2)}%). En Pine: comisión 0,04% y 1 tick de slippage."]),
              PageBreak()]

    # ------------------------------------------------------------------ 4. arquitectura
    arch = [["Ruta", "Contenido", "Responsable"],
            ["docs/SPEC.md", "Especificación común de reglas, universo y estructura", "Común"],
            ["pine/ttfm_indicator.pine", "Indicador Pine v6: velas HTF, C1/C2, sweep, CISD, SL/TP, tabla y alertas", "Agente 1"],
            ["pine/README_indicator.md", "Guía de uso del indicador", "Agente 1"],
            ["pine/ttfm_strategy.pine", "Estrategia Pine v6 (Strategy Tester) con la misma lógica", "Agente 2"],
            ["backtest/data_loader.py", "Descarga y caché de klines del archivo público de Binance", "Agente 2"],
            ["backtest/ttfm_engine.py", "Motor de señales y simulador barra a barra con asserts anti look-ahead", "Agente 2"],
            ["backtest/run_backtest.py", "Ejecuta ambos perfiles, métricas, costes, sensibilidad y gráficos", "Agente 2"],
            ["results/", "CSV de trades y métricas, summary.json y gráficos PNG", "Agente 2"],
            ["report/build_report.py", "Genera este PDF a partir de results/", "Agente 3"],
            ["README.md", "Documentación general del proyecto", "Agente 3"]]
    story += [P("4. Arquitectura del proyecto y roles de los agentes", H1),
              P("El trabajo se repartió entre tres agentes que compartieron una única especificación:"),
              bullets(["<b>Agente 1 - Indicador.</b> Infraestructura visual en Pine v6: construcción manual de velas "
                       "HTF, proyección de C1/C2, detección de sweep, máquina de estados del setup, CISD, niveles de "
                       "entrada/SL/TP, tabla de estado y alertas. Sus funciones de lógica son la referencia.",
                       "<b>Agente 2 - Estrategia y backtest.</b> Estrategia Pine que reutiliza literalmente las funciones "
                       "del indicador y añade la ejecución de órdenes; motor Python equivalente, descarga de datos, "
                       "simulación de ambos perfiles y generación de resultados.",
                       "<b>Agente 3 - Dirección e integración.</b> Revisión cruzada de la lógica Pine frente al motor "
                       "Python, revisión de sintaxis Pine v6, corrección de defectos, reproducción del backtest de punta a "
                       "punta, README y este informe."]),
              Spacer(1, 0.2 * cm), table(arch, col_w=[4.6 * cm, 9.6 * cm, 2.4 * cm], num_from=99),
              P("Revisión de integración", H2),
              P("Se comprobó que las tres implementaciones siguen el mismo orden de evaluación (invalidación -> "
                "expiración -> objetivo -> CISD), la misma definición de nivel CISD (apertura de la primera vela de la "
                "serie opuesta más reciente, consumida al cruzarse), el mismo descarte de la primera vela HTF parcial y "
                "de los sweeps ambiguos, el mismo ATR de Wilder de 14 periodos, minRR = 1,0, maxEntryBars = 12 y "
                "slBufferATR = 0,1. Se corrigió un defecto en la estrategia Pine: el margen (5%, es decir 20x) coincidía "
                "exactamente con el tope de tamaño de 20x, por lo que las posiciones limitadas por apalancamiento podían "
                "sufrir <i>margin calls</i> del emulador de TradingView antes de llegar al stop, algo que el motor Python "
                "no modela; se bajó a 2% para que el tope lo fije sólo el parámetro de apalancamiento máximo. El backtest "
                "se re-ejecutó de punta a punta y reproduce exactamente las cifras de summary.json."),
              PageBreak()]

    # ------------------------------------------------------------------ 5. datos y metodología
    uni = [["Clase", "Símbolo (proxy)", "Mercado", "Representa", "B&H %"]]
    rep = {"EURUSDT": ("Spot", "EUR/USD"), "BTCUSDT": ("Spot", "Bitcoin"), "ETHUSDT": ("Spot", "Ether"),
           "SOLUSDT": ("Spot", "Solana"), "SPYUSDT": ("Perpetuo USD-M", "S&P 500 (SPY)"),
           "QQQUSDT": ("Perpetuo USD-M", "Nasdaq 100 (QQQ)"), "XAUUSDT": ("Perpetuo USD-M", "Oro"),
           "XAGUSDT": ("Perpetuo USD-M", "Plata"), "CLUSDT": ("Perpetuo USD-M", "Petróleo WTI")}
    cls = {"EURUSDT": "Forex", "BTCUSDT": "Cripto", "ETHUSDT": "Cripto", "SOLUSDT": "Cripto", "SPYUSDT": "Indices",
           "QQQUSDT": "Indices", "XAUUSDT": "Commodities", "XAGUSDT": "Commodities", "CLUSDT": "Commodities"}
    for s, (mk, r) in rep.items():
        uni.append([cls[s], s, mk, r, fmt(S["buy_hold_pct"][s], 2, sign=True)])
    story += [P("5. Datos y metodología", H1),
              P(f"<b>Fuente.</b> Archivo público de Binance (data.binance.vision), velas de 15 minutos del {period}. "
                "Otras fuentes (Yahoo y similares) no eran accesibles desde el entorno de ejecución, por lo que se usan "
                "<b>proxies</b>: EURUSDT spot para el forex, los perpetuos TradFi SPYUSDT/QQQUSDT para índices y "
                "XAU/XAG/CL perpetuos para commodities. Las velas de 1H, 4H y 1D se derivan por agregación en UTC "
                "(alineadas a 00:00 UTC, como TradingView en cripto)."),
              table(uni, col_w=[2.6 * cm, 3 * cm, 3.4 * cm, 4 * cm, 2.2 * cm], num_from=4, color_cols=(4,)),
              Spacer(1, 0.2 * cm),
              P("Cobertura: " + "; ".join(f"{k}: {latin1(v)}" for k, v in S["data_notes"].items() if not v.startswith("21504")) +
                ". El resto de símbolos tiene 21.504 velas completas.", SMALL),
              P("Simulación", H2),
              bullets(["Motor barra a barra en LTF: las velas HTF se construyen a partir de las LTF y C1/C2 sólo se "
                       "usan una vez cerradas; las órdenes de salida (stop/limit) actúan desde la vela siguiente a la "
                       "entrada.",
                       f"Capital inicial {pa['initial_capital']:,.0f} USD por activo; riesgo {pa['risk'] * 100:g}% del "
                       "equity por operación; costes como en la sección 3.".replace(",", "."),
                       "<b>Cartera</b>: media equiponderada de las curvas de equity de cada activo (cada uno opera su "
                       "propia subcuenta). Las cifras por clase son la media de los activos de esa clase.",
                       "Sharpe calculado con rendimientos diarios anualizados (raíz de 365). Profit factor = beneficio "
                       "bruto / pérdida bruta. Expectativa en múltiplos de R (riesgo planificado), neta de costes.",
                       "Buy &amp; hold = variación del precio entre la primera apertura y el último cierre del período."]),
              P("Controles anti look-ahead y de coherencia", H2),
              P(latin1(S["sanity_checks"]) + ". Además: nº de trades acotado por el nº de velas HTF, precios de entrada "
                "dentro del rango de la vela de confirmación, SL y TP al lado correcto de la entrada y toda salida por SL "
                "con R negativo. Todos los asserts pasan en ambos perfiles."),
              PageBreak()]

    # ------------------------------------------------------------------ 6 y 7. resultados por perfil
    for k, p in enumerate(PROFILES):
        g = S["profiles"][p]["global_"]
        sec = 6 + k
        story += [P(f"{sec}. Resultados: perfil {PLABEL[p]}", H1),
                  P(f"Período {period}. Métricas netas de comisiones y slippage. Retorno y drawdown sobre la cartera "
                    "equiponderada de la clase (o del universo en GLOBAL)."),
                  P("Por clase de activo", H2), class_table(S, p), Spacer(1, 0.2 * cm),
                  P("Por activo", H2), asset_table(M, p),
                  P("CISD = señales CISD en dirección del sesgo durante la ventana de entrada; Rech. RR = señales "
                    "omitidas por R:R &lt; minRR (el setup siguió activo).", SMALL)]
        if p == "intradia_4H_15m":
            story += [P(f"<b>Lectura.</b> El perfil intradía genera {int(g['trades'])} operaciones con un R:R "
                        f"planificado medio de {fmt(g['avg_planned_rr'])}, pero la ganancia media realizada es "
                        f"{fmt(g['avg_win_R'], 2, sign=True)} R y la pérdida media {fmt(g['avg_loss_R'], 2)} R: los costes "
                        "recortan las ganancias y agrandan las pérdidas porque se expresan sobre stops muy estrechos. "
                        "Todas las clases pierden; el forex (EURUSDT) es el peor por tener los stops más cortos en "
                        "términos relativos. CLUSDT queda prácticamente plano. "
                        f"{int(g['rejected_minRR'])} de {int(g['cisd_signals'])} CISD se descartaron por R:R &lt; 1: el "
                        "CISD suele llegar cuando el precio ya ha recorrido buena parte del rango de C2.")]
        else:
            story += [P(f"<b>Lectura.</b> En swing la frecuencia cae a {int(g['trades'])} operaciones y los stops son "
                        "unas tres veces más amplios, por lo que el peso relativo de los costes es mucho menor. El "
                        "resultado global es casi plano. Oro y plata son positivos con PF cercanos o superiores a 2 y "
                        "SPYUSDT ligeramente positivo; cripto (sobre todo SOL) y QQQ restan. Con 6-12 operaciones por "
                        "activo, estas diferencias están dentro de lo que puede explicar el azar.")]
        mo = MO[p].copy()
        mo_rows = [["Activo"] + list(mo.columns)] + [[i] + [fmt(v, 2, sign=True) for v in r] for i, r in mo.iterrows()]
        story += [KeepTogether([P("Retornos mensuales (%)", H2),
                                table(mo_rows, color_cols=tuple(range(1, len(mo.columns) + 1)), font=7.2)]),
                  PageBreak()]

    # ------------------------------------------------------------------ 8. gráficos
    story += [P("8. Comparativa y gráficos", H1),
              img(os.path.join(RES, "equity_global.png"), 16.5,
                  "Figura 2. Curva de equity de la cartera global en ambos perfiles frente al buy & hold medio."),
              img(os.path.join(RES, "equity_by_class.png"), 17, "Figura 3. Curvas de equity por clase de activo."),
              PageBreak(),
              img(os.path.join(RES, "metrics_by_asset.png"), 17, "Figura 4. Métricas por activo y perfil."),
              img(os.path.join(RES, "r_distribution.png"), 16.5,
                  "Figura 5. Distribución de resultados por operación en múltiplos de R."),
              PageBreak(),
              img(os.path.join(RES, "monthly_heatmap.png"), 17, "Figura 6. Mapa de calor de retornos mensuales."),
              P("La curva intradía desciende de forma casi continua, señal de una expectativa negativa estable más que "
                "de un mal período puntual. La curva swing oscila alrededor del capital inicial. La distribución de R "
                "muestra pérdidas que superan -1 R (efecto de costes y gaps) y ganancias que rara vez alcanzan el R:R "
                "planificado completo.")]

    # ------------------------------------------------------------------ 9. sensibilidad
    sens_rows = [["minRR", "Buffer SL (ATR)", "Trades", "Win %", "PF", "Exp. (R)", "Retorno %", "Max DD %"]]
    for _, r in SENS.iterrows():
        sens_rows.append([fmt(r.minRR, 1), fmt(r.slBufferATR, 2), int(r.trades), fmt(r.win_rate_pct, 1),
                          fmt(r.profit_factor), fmt(r.expectancy_R, 2, sign=True),
                          fmt(r.portfolio_return_pct, 2, sign=True), fmt(r.max_dd_pct, 2)])
    story += [P("9. Análisis de sensibilidad", H1),
              P("Se repitió el backtest intradía (cartera global, neto de costes) para minRR en {1,0; 1,5; 2,0} y buffer "
                "del stop en {0; 0,1; 0,25} x ATR14."),
              table(sens_rows, num_from=0, color_cols=(5, 6)), Spacer(1, 0.3 * cm),
              img(fs, 11, "Figura 7. Retorno de la cartera intradía según minRR y buffer del stop."),
              P("<b>Lectura.</b> Ninguna combinación es rentable. Exigir más R:R reduce mucho el número de operaciones y, "
                "con ello, las pérdidas absolutas, pero la expectativa por operación sigue siendo negativa (entre -0,6 y "
                "-0,9 R). Un buffer mayor del stop ayuda de forma sistemática: ensancha el stop y reduce el peso "
                "relativo de los costes, lo que confirma el diagnóstico de la sección siguiente. Al tratarse de una "
                "rejilla pequeña elegida a priori, el riesgo de sobreajuste es bajo, pero tampoco se ha encontrado una "
                "región robusta positiva."),
              PageBreak()]

    # ------------------------------------------------------------------ 10. costes
    cost_rows = [["Perfil", "Clase", "Exp. bruta (R)", "Exp. neta (R)", "Ret. bruto %", "Ret. neto %", "PF bruto", "PF neto"]]
    for p in PROFILES:
        for c in CLASSES + ["GLOBAL"]:
            gr = S["gross_no_costs"][p][c]
            nt = S["profiles"][p]["global_"] if c == "GLOBAL" else S["profiles"][p]["by_class"][c]
            cost_rows.append([PLABEL[p].split(" ")[0], c, fmt(gr["expectancy_R"], 2, sign=True),
                              fmt(nt["expectancy_R"], 2, sign=True), fmt(gr["return_pct"], 2, sign=True),
                              fmt(nt["return_pct"], 2, sign=True), fmt(gr["profit_factor"]), fmt(nt["profit_factor"])])
    story += [P("10. Impacto de los costes (bruto vs neto)", H1),
              P("La misma simulación se repitió con comisión y slippage a cero. La comparación separa la calidad de la "
                "señal (resultado bruto) del efecto de la ejecución (diferencia bruto - neto)."),
              table(cost_rows, num_from=2, color_cols=(2, 3, 4, 5), font=7.4), Spacer(1, 0.25 * cm),
              img(fc, 16.5, "Figura 8. Expectativa por operación con y sin costes, por clase."),
              img(fsc, 16, f"Figura 9. Distancia mediana al stop frente al coste de ida y vuelta ({fmt(rt_cost, 2)}%)."),
              P(f"<b>Diagnóstico.</b> En intradía la distancia mediana al stop es {fmt(med_risk_i, 2)}% del precio "
                f"(EURUSDT apenas {fmt(ti[ti.asset_class == 'Forex'].risk_pct.median(), 3)}%, índices "
                f"{fmt(ti[ti.asset_class == 'Indices'].risk_pct.median(), 2)}%), frente a un coste de ida y vuelta de "
                f"{fmt(rt_cost, 2)}%. Eso supone, de media, en torno a {fmt(rt_cost / med_risk_i, 2)} R de coste por "
                "operación, más que cualquier ventaja que pueda tener la señal: la expectativa pasa de "
                f"{fmt(gri['expectancy_R'], 2, sign=True)} R bruta a {fmt(gi['expectancy_R'], 2, sign=True)} R neta. "
                f"En swing la mediana es {fmt(med_risk_s, 2)}% y el coste equivale a unos "
                f"{fmt(rt_cost / med_risk_s, 2)} R; la expectativa bruta positiva "
                f"({fmt(grs['expectancy_R'], 2, sign=True)} R) se queda en {fmt(gs['expectancy_R'], 2, sign=True)} R. "
                "Los índices y el forex intradía tienen expectativa bruta positiva que los costes destruyen por completo; "
                "con un broker de CFD/futuros con spreads más bajos el resultado sería menos negativo, pero la ventaja "
                "bruta observada es demasiado pequeña para considerarla fiable."),
              PageBreak()]

    # ------------------------------------------------------------------ 11. limitaciones
    story += [P("11. Limitaciones", H1),
              bullets(["<b>Proxies de datos.</b> EURUSDT spot de Binance no es el mercado interbancario de EUR/USD (su "
                       "liquidez y spreads son distintos); SPYUSDT/QQQUSDT y XAU/XAG/CL son perpetuos que cotizan 24/7 y "
                       "no reproducen las sesiones, gaps y horarios de los mercados subyacentes ni sus velas de 4H/1D por "
                       "sesión. En TradingView con datos del mercado real los resultados serán distintos.",
                       "<b>Período corto.</b> Algo más de 7 meses; en swing hay sólo 86 operaciones en total y entre 6 y "
                       "12 por activo. Los intervalos de confianza son muy amplios.",
                       "<b>Mecanización de un modelo discrecional.</b> TTrades aplica el modelo con contexto (niveles HTF, "
                       "sesiones, SMT, fair value gaps, narrativa). Aquí se opera cualquier sweep que cumpla la regla, sin "
                       "filtros de calidad; el resultado mide la regla, no al trader.",
                       "<b>Ejecución.</b> Entrada al cierre con slippage fijo; SL primero cuando SL y TP coinciden en la "
                       "misma vela; sin financiación de perpetuos (funding) ni swaps; sin límites de liquidez.",
                       "<b>Pine no compilado aquí.</b> El indicador y la estrategia se revisaron a fondo pero no pudieron "
                       "compilarse en TradingView desde este entorno. El Strategy Tester puede ordenar SL/TP dentro de una "
                       "vela de forma distinta (heurística OHLC) y usa slippage en ticks, por lo que sus cifras no "
                       "coincidirán exactamente con las de Python.",
                       "<b>Alineación HTF.</b> Las velas HTF se alinean a 00:00 UTC. En instrumentos con sesión "
                       "(acciones, futuros CME, forex con cierre 17:00 NY) TradingView alinea según la sesión del "
                       "símbolo, lo que cambia C1/C2."])]

    # ------------------------------------------------------------------ 12. recomendaciones
    story += [P("12. Recomendaciones de mejora", H1),
              P("Las siguientes líneas de trabajo se proponen como hipótesis a validar fuera de muestra, no como "
                "ajustes para mejorar este backtest:"),
              bullets(["<b>Filtrar por sesiones (killzones).</b> Operar sólo CISD formados en las aperturas de Londres y "
                       "Nueva York, donde el modelo original sitúa la manipulación y la expansión.",
                       "<b>Priorizar HTF diaria con LTF de 1 hora</b> (o 4H con 15m sólo en sesión): stops más amplios "
                       "reducen el peso de los costes, que es el principal problema detectado.",
                       "<b>R:R mínimo más alto y stop mínimo en múltiplos de coste.</b> Por ejemplo minRR 2 y descartar "
                       "operaciones cuyo stop sea inferior a 5-10 veces el coste de ida y vuelta.",
                       "<b>Centrarse en commodities</b> (oro y plata), el único segmento positivo en swing, ampliando el "
                       "histórico para confirmar si la ventaja es estable.",
                       "<b>Confirmaciones adicionales.</b> Divergencia SMT entre activos correlacionados (ES/NQ, XAU/XAG, "
                       "EUR/GBP), fair value gap en la vela de CISD o desplazamiento mínimo de la vela de confirmación.",
                       "<b>Gestión.</b> TP parcial en el 50% de C2 con stop a break-even, o salida por tiempo al cierre de "
                       "C3, para capturar la parte más probable del recorrido.",
                       "<b>Validación.</b> Datos del mercado real (futuros CME, forex de broker), 2-3 años de histórico, "
                       "walk-forward y test de Monte Carlo sobre el orden de las operaciones."])]

    # ------------------------------------------------------------------ anexos
    par = [["Parámetro", "Valor", "Descripción"],
           ["HTF / LTF", "4H / 15m y 1D / 1H", "Perfiles intradía y swing"],
           ["minRR", fmt(pa["minRR"], 1), "R:R mínimo para aceptar la señal"],
           ["slBufferATR", fmt(pa["slBufferATR"], 2), "Buffer del stop en múltiplos de ATR14 LTF"],
           ["atrLen", str(pa["atrLen"]), "Periodo del ATR (Wilder)"],
           ["maxEntryBars", str(pa["maxEntryBars"]), "Velas LTF de C3 en las que se permite entrar (0 = sin límite)"],
           ["timeExitBars", str(pa["timeExitBars"]), "Salida por tiempo (0 = desactivada)"],
           ["Cancelar en objetivo", "Sí", "Cancela el setup si se alcanza el TP antes del CISD"],
           ["Riesgo", f"{pa['risk'] * 100:g}%", "Del equity por operación"],
           ["Tope de apalancamiento", f"{pa['maxLeverage']:g}x", "Nocional máximo / equity"],
           ["Comisión", f"{pa['commission'] * 100:g}% por lado", "Python y Pine"],
           ["Slippage", f"{pa['slippage'] * 100:g}% por lado", "Python (Pine: 1 tick)"],
           ["Capital inicial", "10.000 USD", "Por activo"],
           ["Período", period, "Entradas filtradas a este rango"]]
    story += [PageBreak(), P("Anexo A. Parámetros", H1),
              table(par, col_w=[4 * cm, 4 * cm, 8.6 * cm], num_from=99),
              P("Anexo B. Uso en TradingView", H1),
              bullets(["Abrir el gráfico del instrumento en <b>15 minutos</b> (perfil intradía, HTF 240) o en <b>1 hora</b> "
                       "(perfil swing, HTF D).",
                       "Abrir el <b>Pine Editor</b>, crear un script nuevo, pegar el contenido de "
                       "<font face='Courier'>pine/ttfm_indicator.pine</font>, guardar y pulsar <b>Añadir al gráfico</b>. "
                       "Repetir en otro script con <font face='Courier'>pine/ttfm_strategy.pine</font>.",
                       "En los ajustes elegir la <b>Temporalidad HTF</b> (240 o D; Auto la deduce del gráfico) y, si se "
                       "desea, minRR, buffer del SL y maxEntryBars. La HTF debe ser mayor que la del gráfico.",
                       "El indicador dibuja las velas HTF C1/C2/C3 a la derecha, las líneas de C1 y C2, los sweeps, el "
                       "nivel CISD pendiente, la confirmación y los niveles de entrada/SL/TP, además de una tabla de "
                       "estado. Las alertas disponibles son: sweep alcista/bajista y CISD long/short.",
                       "La estrategia abre las órdenes en el <b>Strategy Tester</b> (pestaña inferior) con comisión 0,04%, "
                       "1 tick de slippage, riesgo del 1% y filtro de fechas configurable. Para comparar con Python, usar "
                       "el mismo período y revisar los valores de la ventana de datos (sesgo, estado, niveles CISD).",
                       "Aviso: el código no ha sido compilado en TradingView desde este entorno; si el editor muestra algún "
                       "aviso, revisar la línea indicada. Ninguna de estas herramientas constituye asesoramiento "
                       "financiero."])]

    doc = SimpleDocTemplate(PDF, pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm, topMargin=1.8 * cm,
                            bottomMargin=2 * cm, title="TTFM - Modelo Fractal estilo TTrades - Informe",
                            author="Proyecto TTFM", subject="Backtest del modelo fractal")
    doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
    print("PDF generado:", PDF)


if __name__ == "__main__":
    build()
