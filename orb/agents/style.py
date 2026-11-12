"""Estilo común de los gráficos (paleta de referencia del skill dataviz, modo claro)."""
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap

SURFACE, INK, INK2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
BLUE, ORANGE, GREEN, AMBER, PINK, GRAY = "#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#9a9893"
# directa, retest_continua, giro_continua, giro_rechazo, rango
SCEN_COLORS = ["#0f3f80", BLUE, ORANGE, AMBER, GRAY]
SEQ = LinearSegmentedColormap.from_list("seq", ["#f3f7fd", "#9cc1ef", "#2a78d6", "#0f3f80"])
DIV = LinearSegmentedColormap.from_list("div", ["#c2441a", "#f4b597", "#efeeec", "#9cc1ef", "#1c5fb0"])

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "axes.edgecolor": GRID, "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
    "text.color": INK, "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6,
    "axes.spines.top": False, "axes.spines.right": False, "font.size": 9, "lines.linewidth": 2,
    "legend.frameon": False,
})
