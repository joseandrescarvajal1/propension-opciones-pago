# -*- coding: utf-8 -*-
"""Genera las figuras de la presentación en outputs/ppt/ a partir de los datos reales."""
import json
import sqlite3
import sys
import warnings
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs" / "ppt"
OUT.mkdir(parents=True, exist_ok=True)

AZUL, NARANJA, GRIS, VERDE, ROJO, TEXTO = "#2a78d6", "#eb6834", "#c9c8c3", "#2e9e6b", "#d1495b", "#333333"
mpl.rcParams.update({"figure.dpi": 160, "savefig.dpi": 160, "font.size": 12, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.edgecolor": GRIS, "axes.grid": True, "grid.color": "#ededed", "axes.axisbelow": True,
                     "axes.titlesize": 15, "axes.titleweight": "bold", "axes.titlelocation": "left", "axes.labelcolor": TEXTO,
                     "xtick.color": TEXTO, "ytick.color": TEXTO, "figure.facecolor": "white"})


def guardar(fig, nombre):
    fig.tight_layout()
    fig.savefig(OUT / f"{nombre}.png", bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("  ", nombre)


# ---------------------------------------------------------------- 1. etiqueta por mes
print("1. etiqueta por mes")
tr = pd.read_parquet(ROOT / "data" / "processed" / "train.parquet", columns=["fecha_var_rpta_alt", "var_rpta_alt"])
g = tr.groupby("fecha_var_rpta_alt").var_rpta_alt.agg(["mean", "size"])
fig, ax = plt.subplots(figsize=(9, 4.6))
meses = ["ago 2023", "sep", "oct", "nov", "dic"]
b = ax.bar(meses, g["mean"] * 100, color=AZUL, width=0.6)
for r, v, n in zip(b, g["mean"] * 100, g["size"]):
    ax.text(r.get_x() + r.get_width() / 2, v + 1, f"{v:.1f} %", ha="center", fontweight="bold", color=TEXTO)
    ax.text(r.get_x() + r.get_width() / 2, 3, f"{n/1000:.0f} mil\nfilas", ha="center", fontsize=9, color="white")
ax.axhline(g["mean"].mean() * 100, color=NARANJA, ls="--", lw=1.5)
ax.text(4.35, g["mean"].mean() * 100 + 1, "promedio", color=NARANJA, fontsize=10, ha="right")
ax.set_ylim(0, 62); ax.set_ylabel("% de obligaciones que aceptan")
ax.set_title("La etiqueta está balanceada y es estable mes a mes")
guardar(fig, "01_etiqueta_por_mes")

# ------------------------------------------------- 2. lo que trae el test frente al train
print("2. cobertura train vs test")
fig, ax = plt.subplots(figsize=(9, 4.6))
cats = ["Entrenamiento\n(ago a dic 2023)", "Predicción\n(enero 2024)"]
llaves, gestion = [4, 4], [45, 0]
ax.bar(cats, llaves, color=AZUL, label="Llaves (cliente, obligación, mes)", width=0.5)
ax.bar(cats, gestion, bottom=llaves, color=NARANJA, label="Variables de la gestión del mes", width=0.5)
ax.text(0, 27, "45 variables\nno disponibles\npara predecir", ha="center", color="white", fontweight="bold")
ax.text(1, 8, "solo 4 llaves", ha="center", color=TEXTO, fontweight="bold")
ax.set_ylabel("columnas en el archivo"); ax.legend(frameon=False, loc="upper right")
ax.set_title("El archivo de enero solo trae llaves: todo hay que construirlo del histórico")
guardar(fig, "02_train_vs_test")

# ------------------------------------------------------------- 3. validación: el error
print("3. validacion aleatoria vs temporal")
fig, ax = plt.subplots(figsize=(9, 4.8))
x = np.arange(2); w = 0.36
local = [0.747, 0.6972]
kaggle = [0.7045, 0.71421]
b1 = ax.bar(x - w / 2, local, w, color=AZUL, label="F1 medido en mi validación")
b2 = ax.bar(x + w / 2, kaggle, w, color=NARANJA, label="F1 real en Kaggle")
for r, v in list(zip(b1, local)) + list(zip(b2, kaggle)):
    ax.text(r.get_x() + r.get_width() / 2, v + 0.006, f"{v:.4f}", ha="center", fontweight="bold", fontsize=11, color=TEXTO)
ax.annotate("", xy=(0, 0.7470), xytext=(0, 0.7045), arrowprops=dict(arrowstyle="<->", color=ROJO, lw=2.2))
ax.text(0.07, 0.7258, "brecha de 0,043:\nmi validación mentía", va="center", color=ROJO, fontweight="bold", fontsize=11)
ax.annotate("", xy=(1, 0.6972), xytext=(1, 0.71421), arrowprops=dict(arrowstyle="<->", color=VERDE, lw=2.2))
ax.text(1.07, 0.7057, "coherente:\nmido lo que pasa", va="center", color=VERDE, fontweight="bold", fontsize=11)
ax.set_xticks(x); ax.set_xticklabels(["Partición aleatoria 80/10/10", "Validación temporal\n(entreno ≤ nov, mido dic)"])
ax.set_ylim(0.66, 0.775); ax.set_xlim(-0.55, 1.75); ax.set_ylabel("F1"); ax.legend(frameon=False, loc="upper right", fontsize=10)
ax.set_title("El error que casi me cuesta la prueba")
guardar(fig, "03_validacion")

# --------------------------------------------------------------- 4. comparación de modelos
print("4. modelos")
mod = pd.DataFrame({
    "modelo": ["LightGBM base\n(77 vars)", "XGBoost\n+ Optuna", "CatBoost\n+ Optuna", "LightGBM final\n(100 vars, temporal)"],
    "kaggle": [0.70694, 0.70450, 0.70379, 0.71421],
})
fig, ax = plt.subplots(figsize=(9.5, 4.6))
col = [GRIS, GRIS, GRIS, AZUL]
b = ax.bar(mod.modelo, mod.kaggle, color=col, width=0.55)
for r, v in zip(b, mod.kaggle):
    ax.text(r.get_x() + r.get_width() / 2, v + 0.0012, f"{v:.5f}", ha="center", fontweight="bold", color=TEXTO)
ax.set_ylim(0.695, 0.720); ax.set_ylabel("F1 público (Kaggle)")
ax.set_title("Cuatro familias probadas; gana LightGBM con validación temporal")
guardar(fig, "04_modelos")

# ------------------------------------------------------- 5. el techo: etiqueta ambigua
print("5. ambiguedad de la etiqueta")
fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.6))
ax = axes[0]
et = pd.Series({"Aceptó la oferta": 47.9, "Rechazó explícitamente": 3.0, "Sin registro de oferta": 49.0})
col = [VERDE, NARANJA, ROJO]
ax.barh(et.index[::-1], et.values[::-1], color=col[::-1], height=0.6)
for i, v in enumerate(et.values[::-1]):
    ax.text(v + 0.8, i, f"{v:.1f} %", va="center", fontweight="bold", color=TEXTO)
ax.set_xlim(0, 60); ax.set_xlabel("% de las filas de entrenamiento"); ax.grid(axis="y", visible=False)
ax.set_title("Solo el 3 % son rechazos reales")
ax = axes[1]
ax.pie([91, 9], labels=["Sin registro\nde oferta", "Otros"], colors=[ROJO, GRIS], autopct="%1.0f %%",
       startangle=90, textprops={"fontweight": "bold", "color": TEXTO}, wedgeprops={"width": 0.45})
ax.set_title("De mis falsos positivos en diciembre")
guardar(fig, "05_ambiguedad")

# ------------------------------------------------------------------- 6. SHAP
print("6. SHAP")
sh = pd.read_csv(ROOT / "outputs" / "importancia_shap_v4.csv", index_col=0).iloc[:, 0].head(12)
sys.path.insert(0, str(ROOT / "agente"))
from herramientas.glosario import GLOSARIO  # noqa: E402

etiquetas = [GLOSARIO.get(i, i.replace("_", " "))[:48] for i in sh.index]
fig, ax = plt.subplots(figsize=(10.5, 5.2))
ax.barh(etiquetas[::-1], sh.values[::-1], color=[NARANJA if i.startswith("fe_") else AZUL for i in sh.index][::-1], height=0.65)
ax.set_xlabel("impacto promedio en la predicción"); ax.grid(axis="y", visible=False)
ax.set_title("Qué mira el modelo (naranja: variables que construí)")
guardar(fig, "06_shap")

# ------------------------------------------------------- 7. decisiones del agente
print("7. acciones del agente")
con = sqlite3.connect(ROOT / "agente" / "sandbox" / "sandbox.db")
perf = json.loads((ROOT / "agente" / "sandbox" / "perfiles.json").read_text(encoding="utf-8"))
acc = pd.Series({"Acuerdo de pago\na 5 días": 17, "Ofrecer opción\nde pago": 16, "Pasar a gestor\nhumano": 5, "Sin oferta\n(no elegible)": 2})
fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.6))
ax = axes[0]
b = ax.bar(acc.index, acc.values, color=[AZUL, VERDE, ROJO, GRIS], width=0.6)
for r, v in zip(b, acc.values):
    ax.text(r.get_x() + r.get_width() / 2, v + 0.3, str(v), ha="center", fontweight="bold", color=TEXTO)
ax.set_ylabel("clientes"); ax.set_ylim(0, 20)
ax.set_title("Qué decide el agente sobre 40 clientes")
ax = axes[1]
res = pd.read_csv(ROOT / "outputs" / "pruebas_agente_resumen.csv")
b = ax.barh(res.tipo[::-1], res.pruebas[::-1], color=VERDE, height=0.6)
for r, n in zip(b, res.pruebas[::-1]):
    ax.text(n + 0.4, r.get_y() + r.get_height() / 2, f"{n}/{n}", va="center", fontweight="bold", color=TEXTO)
ax.set_xlim(0, 38); ax.set_xlabel("verificaciones que pasan"); ax.grid(axis="y", visible=False)
ax.set_title("Pruebas del agente: 78 de 78")
guardar(fig, "07_agente")

# -------------------------------------------------------- 8. el modelo dentro del agente
print("8. aporte del modelo en la decision")
fig, ax = plt.subplots(figsize=(9, 4.4))
ax.barh(["Decisión"], [35], color=AZUL, height=0.45, label="La decide el modelo de propensión")
ax.barh(["Decisión"], [65], left=[35], color=GRIS, height=0.45, label="La deciden las reglas del banco")
ax.text(17.5, 0, "35 %", ha="center", va="center", color="white", fontweight="bold", fontsize=15)
ax.text(67.5, 0, "65 %", ha="center", va="center", color=TEXTO, fontweight="bold", fontsize=15)
ax.set_xlim(0, 100); ax.set_yticks([]); ax.grid(visible=False); ax.set_xlabel("% de los clientes")
ax.legend(frameon=False, loc="lower center", bbox_to_anchor=(0.5, -0.45), ncol=2)
for s in ("left", "bottom"):
    ax.spines[s].set_visible(False)
ax.set_title("Dónde manda el modelo y dónde mandan las reglas")
guardar(fig, "08_modelo_vs_reglas")

print("\nfiguras en", OUT)
