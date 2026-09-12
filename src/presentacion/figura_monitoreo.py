# -*- coding: utf-8 -*-
"""Figura del monitoreo de distribuciones (índice de estabilidad poblacional) para la presentación."""
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs" / "ppt"
OUT.mkdir(parents=True, exist_ok=True)

AZUL, NARANJA, GRIS, VERDE, ROJO, TEXTO = "#2a78d6", "#eb6834", "#c9c8c3", "#2e9e6b", "#d1495b", "#333333"
mpl.rcParams.update({"figure.dpi": 160, "savefig.dpi": 160, "font.size": 12, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.edgecolor": GRIS, "axes.grid": True, "grid.color": "#ededed", "axes.axisbelow": True,
                     "axes.titlesize": 14, "axes.titleweight": "bold", "axes.titlelocation": "left", "axes.labelcolor": TEXTO,
                     "xtick.color": TEXTO, "ytick.color": TEXTO, "figure.facecolor": "white"})

d = pd.read_csv(ROOT / "outputs" / "monitoreo_202401.csv")
COLOR = {"estable": VERDE, "aviso": NARANJA, "alarma": ROJO}

fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.4), gridspec_kw={"width_ratios": [1, 1.35]})

# izquierda: reparto de las 100 variables
ax = axes[0]
conteo = d.estado.value_counts().reindex(["estable", "aviso", "alarma"])
b = ax.bar(["Estable\n(< 0,10)", "Aviso\n(0,10 a 0,25)", "Alarma\n(> 0,25)"], conteo.values,
           color=[VERDE, NARANJA, ROJO], width=0.6)
for r, v in zip(b, conteo.values):
    ax.text(r.get_x() + r.get_width() / 2, v + 1.5, str(v), ha="center", fontweight="bold", fontsize=15, color=TEXTO)
ax.set_ylim(0, 82); ax.set_ylabel("variables del modelo")
ax.set_title("Cómo se movieron las 100 variables")

# derecha: las que más se movieron
ax = axes[1]
top = d.nlargest(7, "psi").iloc[::-1]
etiquetas = {"fe_tasa_hist_segmento": "tasa histórica por segmento", "fe_tasa_hist_producto": "tasa histórica por producto",
             "fe_tasa_hist_aplicativo": "tasa histórica por sistema", "pag_n_pago_mas_3m": "meses pagando de más (3m)",
             "pag_meses_historial": "meses de historial disponible", "pag_marca_pago_t1": "comportamiento de pago previo",
             "pag_n_pago_mas_6m": "meses pagando de más (6m)"}
ax.barh([etiquetas.get(v, v) for v in top.variable], top.psi, color=[COLOR[e] for e in top.estado], height=0.62)
for i, v in enumerate(top.psi):
    ax.text(v + 0.12, i, f"{v:.1f}", va="center", fontweight="bold", fontsize=11, color=TEXTO)
ax.axvline(0.25, color=TEXTO, ls="--", lw=1.2)
ax.text(0.32, 6.35, "umbral de alarma", fontsize=10, color=TEXTO)
ax.set_xlim(0, 8.2); ax.grid(axis="y", visible=False); ax.set_xlabel("cuánto cambió la distribución")
ax.set_title("Las que más se movieron, y por qué")

fig.tight_layout()
fig.savefig(OUT / "10_monitoreo.png", bbox_inches="tight", facecolor="white")
print("figura:", OUT / "10_monitoreo.png")
print(d.estado.value_counts().to_string())
