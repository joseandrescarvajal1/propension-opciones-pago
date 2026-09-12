# -*- coding: utf-8 -*-
"""Corre una conversación real contra el agente desplegado y la dibuja como una captura de WhatsApp."""
import os
import re
import subprocess
import textwrap
from pathlib import Path

import httpx
import matplotlib.pyplot as plt
from dotenv import load_dotenv
from matplotlib.patches import FancyBboxPatch

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")
GC = r"C:\Users\USUARIO\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd"
URL = "https://agente-cobranza-demo-amdvve4e3q-uc.a.run.app"
tok = subprocess.run([GC, "auth", "print-identity-token"], capture_output=True, text=True).stdout.strip()
cab = {"X-API-Key": os.environ["AGENTE_API_KEY"], "Authorization": f"Bearer {tok}"}

httpx.post(URL + "/sandbox/reiniciar", headers=cab, timeout=180)   # conversaciones limpias
cl = httpx.get(URL + "/sandbox/clientes", headers=cab, timeout=60).json()["clientes"]
c = [x for x in cl if x["escenario"] == "E1_mora_temprana_alta_prob"][2]
ced = c["cedula"]
print("cliente:", c["nombre"], ced, "|", c["dias_mora"], "dias")

turnos = []


def hablar(msg):
    r = httpx.post(URL + "/chat", headers=cab, json={"thread_id": ced, "mensaje": msg}, timeout=180).json()
    turnos.append(("cliente", msg))
    turnos.append(("agente", r["respuesta"]))
    print(f">> {msg}\n<< {r['respuesta'][:110]}\n")
    return r


hablar("Hola, vi que tengo una cuota atrasada")
hablar(f"Mi cedula es {ced}")
cod = re.search(r"\b(\d{6})\b", httpx.get(URL + f"/sandbox/otp/{ced}", headers=cab, timeout=60).json()["sms"]["texto"]).group(1)
turnos.append(("sms", f"Bancolombia: tu código de verificación es {cod}. Vence en 5 minutos."))
hablar(cod)
hablar("Listo, acepto. Pago el viernes")

# ------------------------------------------------------------------ dibujo
FONDO, VERDE_WA, BLANCO_WA, SMS = "#ECE5DD", "#DCF8C6", "#FFFFFF", "#FFF4CE"
fig, ax = plt.subplots(figsize=(7.2, 11.5), dpi=150)
ax.set_xlim(0, 100); ax.set_facecolor(FONDO)
ax.axis("off")
fig.patch.set_facecolor(FONDO)

y = 0.0
alturas = []
for quien, texto in turnos:
    ancho = 58 if quien != "sms" else 70
    lineas = []
    for parrafo in texto.split("\n"):
        lineas += textwrap.wrap(parrafo, width=46) or [""]
    alturas.append((quien, lineas, len(lineas)))

total = sum(n * 1.55 + 0.9 + 1.4 for _, _, n in alturas) + 2.0   # alto de cada burbuja mas la separacion
ax.set_ylim(total, 0)

y = 1.0
for quien, lineas, n in alturas:
    alto = n * 1.55 + 0.9
    if quien == "cliente":
        x, ancho, col = 34, 62, BLANCO_WA
        etiqueta, ex = "Cliente", 34.5
    elif quien == "agente":
        x, ancho, col = 4, 62, VERDE_WA
        etiqueta, ex = "Bancolombia", 4.5
    else:
        x, ancho, col = 18, 64, SMS
        etiqueta, ex = "SMS", 18.5
    ax.add_patch(FancyBboxPatch((x, y), ancho, alto, boxstyle="round,pad=0.3,rounding_size=1.2",
                                facecolor=col, edgecolor="#D6D2CA", linewidth=0.7))
    ax.text(ex + 0.6, y + 0.75, etiqueta, fontsize=6.5, color="#7A7A7A", va="center")
    for i, ln in enumerate(lineas):
        ax.text(ex + 0.6, y + 1.9 + i * 1.55, ln, fontsize=8.4, color="#111111", va="center", family="DejaVu Sans")
    y += alto + 1.4

fig.tight_layout(pad=0.2)
salida = ROOT / "outputs" / "ppt" / "09_captura_chat.png"
fig.savefig(salida, bbox_inches="tight", facecolor=FONDO)
print("captura:", salida)
