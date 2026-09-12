# -*- coding: utf-8 -*-
"""Edita la presentación existente conservando los cambios del candidato.
Añade: (1) el sandbox de clientes simulados, (2) cómo los valores SHAP entran al agente."""
# Se ejecutan SOBRE el archivo ya generado, para conservar los ajustes hechos a mano en PowerPoint.
# No vuelvas a correr construir.py después de editar el pptx: lo sobrescribe.
from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches, Pt

ROOT = Path(__file__).resolve().parents[2]
ARCHIVO = ROOT / "outputs" / "presentacion_opciones_de_pago.pptx"

AZUL = RGBColor(0x2A, 0x78, 0xD6)
NARANJA = RGBColor(0xEB, 0x68, 0x34)
VERDE = RGBColor(0x2E, 0x9E, 0x6B)
GRIS = RGBColor(0x6B, 0x6B, 0x6B)
TEXTO = RGBColor(0x33, 0x33, 0x33)
CLARO = RGBColor(0xF3, 0xF5, 0xF8)
BLANCO = RGBColor(0xFF, 0xFF, 0xFF)


def caja(slide, x, y, w, h, texto, tam=15, negrita=False, color=TEXTO, align=PP_ALIGN.LEFT):
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    for i, linea in enumerate(texto.split("\n")):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        p.line_spacing = 1.0
        p.space_after = Pt(3) if linea.strip() else Pt(1)
        t, neg = linea, negrita
        if t.startswith("**") and t.endswith("**"):
            t, neg = t[2:-2], True
        r = p.add_run()
        r.text = t
        r.font.size = Pt(tam)
        r.font.bold = neg
        r.font.color.rgb = color
        r.font.name = "Segoe UI"
    return tb


def bloque(slide, x, y, w, h, relleno):
    s = slide.shapes.add_shape(5, Inches(x), Inches(y), Inches(w), Inches(h))
    s.fill.solid(); s.fill.fore_color.rgb = relleno
    s.line.fill.background(); s.shadow.inherit = False
    return s


def texto_de(shape):
    return shape.text_frame.text


def reemplazar_texto(shape, nuevo):
    """Cambia el texto conservando el formato del primer run de cada párrafo."""
    tf = shape.text_frame
    lineas = nuevo.split("\n")
    base = tf.paragraphs[0].runs[0] if tf.paragraphs[0].runs else None
    fuente = (base.font.size, base.font.name, base.font.color.rgb if base.font.color and base.font.color.type is not None else TEXTO) if base else (Pt(15), "Segoe UI", TEXTO)
    negritas = [p.runs[0].font.bold if p.runs else False for p in tf.paragraphs]
    tf.clear()
    for i, ln in enumerate(lineas):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.line_spacing = 1.0
        p.space_after = Pt(3)
        t, neg = ln, (negritas[i] if i < len(negritas) else False)
        if t.startswith("**") and t.endswith("**"):
            t, neg = t[2:-2], True
        r = p.add_run()
        r.text = t
        r.font.size = fuente[0]
        r.font.name = fuente[1]
        r.font.color.rgb = fuente[2]
        r.font.bold = neg
    return shape


prs = Presentation(str(ARCHIVO))
lam = {i: s for i, s in enumerate(prs.slides, 1)}
print(f"{len(prs.slides)} diapositivas")

# ------------------------------------------------------------------ 1. SANDBOX en la lámina 14
s = lam[14]
caja_inferior = next(sh for sh in s.shapes if sh.has_text_frame and texto_de(sh).startswith("Detrás: nueve herramientas"))
reemplazar_texto(caja_inferior,
                 "**Detrás: nueve herramientas, un subagente analista y un sandbox propio.**\n"
                 "Herramientas: verificación de identidad, consulta de cartera, reglas de elegibilidad, llamada al modelo,\n"
                 "registro de acuerdos y opciones, y escalamiento. El sandbox simula los sistemas del banco y el canal de\n"
                 "WhatsApp, con 40 clientes ficticios construidos sobre variables reales enmascaradas.")
n = s.notes_slide.notes_text_frame
n.text = n.text + ("\nY una pieza que construí a propósito: un sandbox. Como no puedo conectarme a los sistemas del banco ni "
                   "usar datos reales de clientes, simulé ambas cosas: una base con 40 clientes ficticios, sus obligaciones, "
                   "sus opciones preaprobadas y sus restricciones, más un WhatsApp y un SMS simulados. "
                   "Las variables del modelo sí son reales, tomadas de enero y enmascaradas. "
                   "Eso me permitió construir escenarios a propósito para cada uno de los siete perfiles del enunciado, "
                   "y probar casos que en producción serían muy difíciles de reproducir, como un cliente fallecido o un intento de fraude.")
print("14: sandbox añadido")

# ------------------------------------------------------------------ 2. SANDBOX en la lámina 17
s = lam[17]
bloque(s, 0.19, 6.45, 12.0, 0.85, CLARO)
bloque(s, 0.19, 6.45, 0.1, 0.85, VERDE)
caja(s, 0.55, 6.62, 11.5, 0.6,
     "**Todo se prueba sobre el sandbox:** 40 clientes ficticios con sus obligaciones, opciones preaprobadas y restricciones,\n"
     "diseñados para cubrir los siete perfiles del enunciado. Sin un solo dato personal real.", tam=13)
n = s.notes_slide.notes_text_frame
n.text = n.text + ("\nLas dos suites corren sobre el sandbox que mencioné: 40 clientes ficticios diseñados a propósito para cubrir "
                   "los siete perfiles del enunciado. Hay clientes en mora temprana con alta propensión, clientes con varias "
                   "opciones disponibles, clientes que no son elegibles, clientes que incumplieron un acuerdo, y casos sensibles. "
                   "Ninguno tiene un dato personal real: los nombres, las cédulas y los teléfonos son inventados, y las variables "
                   "del modelo vienen de obligaciones reales ya enmascaradas.")
print("17: sandbox añadido")

# ------------------------------------------------------------------ 3. SHAP hacia el agente, lámina 12
s = lam[12]
bloque(s, 0.70, 5.62, 7.6, 1.42, VERDE)
caja(s, 1.0, 5.82, 7.0, 1.1,
     "**De este gráfico a la conversación**\n"
     "El agente recibe estos factores en cada llamada y los convierte en una frase:\n"
     "\"Te lo recomiendo porque, por tu historial, ya habías tomado una alternativa antes y te funcionó.\"",
     tam=13.5, color=BLANCO)
n = s.notes_slide.notes_text_frame
n.text = n.text + ("\nY quiero ser concreto con esto, porque es la conexión entre las dos partes de la prueba. "
                   "Estos factores no se quedan en un gráfico para mí. La API los entrega en la misma llamada en que da la "
                   "probabilidad, el agente los recibe, y tiene la instrucción de justificar toda propuesta con al menos uno de "
                   "ellos, traducido a lenguaje natural. La frase que ven abajo es real, sacada de una conversación del sistema "
                   "desplegado, y corresponde a los dos factores de mayor peso de ese cliente.")
print("12: SHAP hacia el agente añadido")

# ------------------------------------------------------------------ 4. reforzar la lámina 16
s = lam[16]
pie = next(sh for sh in s.shapes if sh.has_text_frame and texto_de(sh).startswith("Medido sobre los 40"))
reemplazar_texto(pie, "Medido sobre los 40 clientes del sandbox. Además de la probabilidad, el agente recibe los factores que la explican.")
print("16: nota ampliada")

prs.save(str(ARCHIVO))
print("guardado:", ARCHIVO)
