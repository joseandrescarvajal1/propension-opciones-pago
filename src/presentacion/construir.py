# -*- coding: utf-8 -*-
"""Construye outputs/presentacion_opciones_de_pago.pptx: 20 diapositivas con notas del orador."""
from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches, Pt

ROOT = Path(__file__).resolve().parents[2]
FIG = ROOT / "outputs" / "ppt"
SALIDA = ROOT / "outputs" / "presentacion_opciones_de_pago.pptx"

AZUL = RGBColor(0x2A, 0x78, 0xD6)
NARANJA = RGBColor(0xEB, 0x68, 0x34)
VERDE = RGBColor(0x2E, 0x9E, 0x6B)
ROJO = RGBColor(0xD1, 0x49, 0x5B)
GRIS = RGBColor(0x6B, 0x6B, 0x6B)
TEXTO = RGBColor(0x33, 0x33, 0x33)
CLARO = RGBColor(0xF3, 0xF5, 0xF8)
BLANCO = RGBColor(0xFF, 0xFF, 0xFF)

prs = Presentation()
prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
W, H = prs.slide_width, prs.slide_height
VACIA = prs.slide_layouts[6]


def caja(slide, x, y, w, h, texto, tam=18, negrita=False, color=TEXTO, align=PP_ALIGN.LEFT, espacio=1.0):
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    for i, linea in enumerate(texto.split("\n")):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        p.line_spacing = espacio
        p.space_after = Pt(3) if linea.strip() else Pt(1)
        neg = negrita
        col = color
        t = linea
        if t.startswith("**") and t.endswith("**"):
            t, neg = t[2:-2], True
        if t.startswith("· "):
            t = "•  " + t[2:]
        r = p.add_run()
        r.text = t
        r.font.size = Pt(tam)
        r.font.bold = neg
        r.font.color.rgb = col
        r.font.name = "Segoe UI"
    return tb


def titulo(slide, texto, sub=None, color=AZUL):
    caja(slide, 0.7, 0.45, 12, 0.9, texto, tam=32, negrita=True, color=color)
    if sub:
        caja(slide, 0.7, 1.32, 12, 0.5, sub, tam=15, color=GRIS)


def banda(slide, color=AZUL, alto=0.14):
    s = slide.shapes.add_shape(1, 0, 0, W, Inches(alto))
    s.fill.solid(); s.fill.fore_color.rgb = color
    s.line.fill.background(); s.shadow.inherit = False


def bloque(slide, x, y, w, h, relleno, borde=None):
    s = slide.shapes.add_shape(5, Inches(x), Inches(y), Inches(w), Inches(h))
    s.fill.solid(); s.fill.fore_color.rgb = relleno
    if borde:
        s.line.color.rgb = borde; s.line.width = Pt(1.5)
    else:
        s.line.fill.background()
    s.shadow.inherit = False
    return s


def imagen(slide, nombre, x, y, w):
    slide.shapes.add_picture(str(FIG / nombre), Inches(x), Inches(y), width=Inches(w))


def numero(slide, n):
    caja(slide, 12.4, 6.95, 0.6, 0.3, str(n), tam=11, color=GRIS, align=PP_ALIGN.RIGHT)


def notas(slide, texto):
    slide.notes_slide.notes_text_frame.text = texto.strip()


def nueva(n=None, con_banda=True):
    s = prs.slides.add_slide(VACIA)
    if con_banda:
        banda(s)
    if n:
        numero(s, n)
    return s


# ============================================================ 1. PORTADA
s = nueva(con_banda=False)
bloque(s, 0, 0, 13.333, 7.5, AZUL)
caja(s, 1.2, 2.2, 11, 1.2, "Propensión a opciones de pago", tam=44, negrita=True, color=BLANCO)
caja(s, 1.2, 3.45, 11, 1.6, "De un modelo que estima quién acepta\na un agente que conversa, decide y deja rastro", tam=24, color=RGBColor(0xD7, 0xE6, 0xF8))
bloque(s, 1.2, 5.3, 0.09, 0.55, NARANJA)
caja(s, 1.5, 5.3, 10, 0.9, "José Carvajal  ·  Prueba Analítica Opciones de Pago, season 3", tam=16, color=RGBColor(0xD7, 0xE6, 0xF8))
notas(s, """Buenos días. En los próximos 15 minutos les cuento cómo resolví la prueba.
Los primeros 10 minutos son la parte técnica: los datos, tres hallazgos que cambiaron el diseño, el modelo y el sistema de agentes.
Los últimos 5 minutos cambio el tono por completo: es la versión que le presentaría a un comité directivo que tiene que aprobar el uso del modelo.
Una idea para empezar: el valor de esto no está en la última décima de F1, sino en que una probabilidad se convierta en una conversación concreta con el cliente.""")

# ============================================================ 2. EL PROBLEMA
s = nueva(2)
titulo(s, "El problema", "Qué pidió el banco y qué decidí construir")
bloque(s, 0.7, 2.0, 5.8, 2.0, CLARO)
caja(s, 1.0, 2.25, 5.2, 1.6, "**Lo que pide el enunciado**\nEstimar, con un mes de anticipación, qué obligaciones en mora\naceptarán una opción de pago. Y un prototipo de agentes que\ngestione a esos clientes.", tam=15)
bloque(s, 6.9, 2.0, 5.8, 2.0, CLARO)
caja(s, 7.2, 2.25, 5.2, 1.6, "**Para qué sirve**\nEl banco ya prioriza por lotes. La propensión entra como una\nvariable más para gestionar primero a quien más probablemente\nacepta, y dejar de contactar a todos por igual.", tam=15)
bloque(s, 0.7, 4.3, 12, 1.9, AZUL)
caja(s, 1.1, 4.6, 11.2, 1.4, "Mi decisión de alcance: no me quedé en el modelo.\nLo desplegué, lo puse a explicar cada predicción y construí encima el agente que\nconvierte esa probabilidad en una acción concreta sobre el cliente.", tam=20, color=BLANCO)
notas(s, """El enunciado tiene dos partes y quiero dejar claro desde el inicio cómo las entendí.
La primera es un modelo de propensión. La segunda, un prototipo de agentes.
Lo importante es el para qué: el banco ya tiene un sistema de priorización por lotes. Esta probabilidad entra ahí como una variable más, para dejar de contactar a todos por igual.
Mi decisión de alcance fue no quedarme en el notebook. El modelo está desplegado, explica cada predicción, y encima construí el agente. Todo lo que voy a mostrar está corriendo en la nube ahora mismo.""")

# ============================================================ 3. LOS DATOS
s = nueva(3)
titulo(s, "Los datos", "Cinco fuentes, cinco meses de historia, una etiqueta")
filas = [
    ("Gestiones y respuesta", "568 mil filas", "ago a dic 2023", "Trae la etiqueta: aceptó o no aceptó", AZUL),
    ("Scores del banco", "obligación y mes", "todo 2023", "Propensión, alerta temprana, auto-cura", GRIS),
    ("Cuotas y pagos", "obligación y mes", "todo 2023", "Cómo viene pagando, mediana de 12 meses", GRIS),
    ("Maestra de clientes", "cliente", "jul a dic 2023", "Demografía y finanzas, cubre el 80 %", GRIS),
    ("A predecir", "112 mil filas", "enero 2024", "Solo llaves: ninguna variable", NARANJA),
]
y = 2.1
for nombre, grano, periodo, aporte, col in filas:
    bloque(s, 0.7, y, 12, 0.82, CLARO)
    bloque(s, 0.7, y, 0.08, 0.82, col)
    caja(s, 1.0, y + 0.16, 3.0, 0.5, nombre, tam=15, negrita=True, color=col if col != GRIS else TEXTO)
    caja(s, 4.1, y + 0.18, 1.9, 0.5, grano, tam=13, color=GRIS)
    caja(s, 6.1, y + 0.18, 1.9, 0.5, periodo, tam=13, color=GRIS)
    caja(s, 8.1, y + 0.18, 4.4, 0.5, aporte, tam=13)
    y += 0.95
notas(s, """Cinco fuentes. La primera es la que trae la etiqueta: 568 mil filas de gestiones entre agosto y diciembre, donde sé si la obligación aceptó o no.
Las tres del medio son el historial: los scores que el banco ya calcula, el comportamiento de pago mes a mes, y la información del cliente.
Y la última es la clave de todo, y es el primer hallazgo que les quiero contar: el archivo de enero que tengo que predecir solo trae llaves.""")

# ============================================================ 4. HALLAZGO 1
s = nueva(4)
titulo(s, "Hallazgo 1: el archivo de enero viene vacío", "Y eso definió toda la arquitectura de variables", color=NARANJA)
imagen(s, "02_train_vs_test.png", 0.7, 2.0, 6.6)
bloque(s, 7.7, 2.0, 5.0, 4.4, CLARO)
caja(s, 8.0, 2.3, 4.4, 4.0, "**Lo que encontré**\nEn entrenamiento tengo 45 variables de la gestión.\nEn enero, ninguna.\n\n**Y algo peor**\nEsas 45 describen el resultado de la gestión\ndel mismo mes que quiero predecir.\nUsarlas sería mirar la respuesta.\n\n**La consecuencia**\nTodas las variables hay que construirlas\ndel histórico, con corte en el mes anterior.", tam=14)
notas(s, """Este fue el primer giro. Miré qué columnas tiene el archivo de entrenamiento y cuáles el de enero, y la diferencia es brutal: 45 variables contra ninguna.
Pero hay algo peor que la ausencia. Esas 45 variables describen el resultado de la gestión del mismo mes que quiero predecir: cuántas veces se contactó al cliente, qué alternativa se le ofreció, cómo terminó. Si las uso, estoy mirando la respuesta.
De aquí sale la regla que gobierna todo el proyecto: toda variable se corta en el mes anterior. Lo digo en la siguiente lámina.""")

# ============================================================ 5. EL CORTE EN t-1
s = nueva(5)
titulo(s, "La regla que gobierna todo: corte en t-1", "Si el dato no existe el día de la predicción, no entra al modelo")
# línea de tiempo
y0 = 2.6
bloque(s, 0.9, y0 + 0.55, 11.5, 0.06, RGBColor(0xDD, 0xDD, 0xDD))
meses = ["ago", "sep", "oct", "nov", "dic", "ENERO"]
for i, m in enumerate(meses):
    x = 0.9 + i * 1.95
    es_obj = i == 5
    col = NARANJA if es_obj else AZUL
    bloque(s, x, y0, 1.7, 1.15, col)
    caja(s, x, y0 + 0.35, 1.7, 0.5, m, tam=17, negrita=True, color=BLANCO, align=PP_ALIGN.CENTER)
caja(s, 0.9, y0 + 1.3, 9.7, 0.5, "historial disponible  →  con esto construyo las variables", tam=14, color=AZUL, align=PP_ALIGN.CENTER)
caja(s, 10.6, y0 + 1.3, 1.8, 0.5, "lo que predigo", tam=14, color=NARANJA, align=PP_ALIGN.CENTER)
bloque(s, 0.7, 4.9, 3.85, 1.5, CLARO)
caja(s, 1.0, 5.15, 3.3, 1.1, "**156 variables**\nconstruidas: tendencias,\nrachas, tasas históricas", tam=15)
bloque(s, 4.75, 4.9, 3.85, 1.5, CLARO)
caja(s, 5.05, 5.15, 3.3, 1.1, "**100 seleccionadas**\npor criterio de negocio,\nvarianza y correlación", tam=15)
bloque(s, 8.8, 4.9, 3.9, 1.5, VERDE)
caja(s, 9.1, 5.15, 3.3, 1.1, "**Cero fuga**\nel mismo código genera\nentrenamiento y predicción", tam=15, color=BLANCO)
notas(s, """Esta es la regla: para predecir enero, solo uso información que existía al cerrar diciembre.
Con eso construí 156 variables desde las tablas históricas: tendencias de pago, rachas de meses sin pagar, tasas históricas de aceptación por producto y segmento, y la historia de gestión de la obligación rezagada un mes.
De esas 156 seleccioné 100, descartando por criterio de negocio, por varianza casi nula y por correlación alta entre ellas.
El detalle que me parece importante: el mismo código genera las variables de entrenamiento y las de predicción. No hay dos caminos que se puedan desincronizar.""")

# ============================================================ 6. LA ETIQUETA
s = nueva(6)
titulo(s, "La etiqueta: balanceada y estable", "Buena noticia, no hay que pelear con el desbalance")
imagen(s, "01_etiqueta_por_mes.png", 1.6, 2.1, 8.4)
bloque(s, 0.7, 6.15, 12, 0.95, CLARO)
caja(s, 1.0, 6.35, 11.4, 0.6, "También encontré que la etiqueta tiene memoria: si la obligación aceptó el mes anterior, es mucho más probable que acepte otra vez. Esa señal la aproveché con variables rezagadas.", tam=15)
notas(s, """Aquí una buena noticia. La etiqueta está casi balanceada, alrededor del 48 % de aceptación, y es estable mes a mes, entre 46 y 49 por ciento.
Eso significa que no tengo que pelear con un desbalance severo, y que puedo entrenar con los cinco meses sin preocuparme de que la distribución cambie.
Otro hallazgo del EDA: la etiqueta tiene memoria. Si la obligación aceptó el mes pasado, es mucho más probable que acepte de nuevo. Esa señal la aproveché construyendo variables rezagadas del historial de gestión.""")

# ============================================================ 7. CALIDAD
s = nueva(7)
titulo(s, "Lo que encontré al revisar la calidad", "Cosas que rompen un pipeline si no se ven a tiempo")
items = [
    ("Nulos guardados como el texto \"None\"", "más de 500 mil líneas. Pandas los convierte solo; Spark y SQL no.", ROJO),
    ("Mora mayor a 90 días en un rango que llega a 90", "65 mil filas donde la mora máxima contradice el rango declarado.", NARANJA),
    ("Edades en cero o mayores a 100", "1.678 clientes. Y 728 con ingresos por encima de mil millones.", NARANJA),
    ("Porcentaje de pago infinito", "3.773 registros donde la cuota es cero y la división se dispara.", NARANJA),
    ("Columnas casi vacías", "tipo de vivienda 69 % nulo, nivel académico 57 %, nicho 53 %.", GRIS),
]
y = 2.15
for t, d, col in items:
    bloque(s, 0.7, y, 0.08, 0.88, col)
    caja(s, 1.0, y + 0.05, 11.3, 0.45, t, tam=16, negrita=True)
    caja(s, 1.0, y + 0.47, 11.3, 0.4, d, tam=13, color=GRIS)
    y += 1.0
notas(s, """Dedico una lámina a esto porque creo que separa un trabajo de exploración serio de uno superficial.
El primero es el más peligroso: hay más de 500 mil líneas donde el nulo viene guardado como el texto "None". Pandas lo convierte automáticamente y uno ni se entera, pero si este pipeline corre en Spark o en SQL, esas filas se tratan como un valor válido y el modelo aprende basura.
Los demás son inconsistencias de negocio: mora que supera el rango declarado, edades imposibles, divisiones por cero.
Ninguno me impidió avanzar, pero todos quedaron documentados, porque en producción hay que decidir qué hacer con cada uno.""")

# ============================================================ 8. HALLAZGO 2
s = nueva(8)
titulo(s, "Hallazgo 2: mi validación me estaba mintiendo", "El error que más me enseñó de toda la prueba", color=ROJO)
imagen(s, "03_validacion.png", 1.2, 1.95, 8.0)
bloque(s, 9.5, 2.1, 3.2, 4.2, CLARO)
caja(s, 9.75, 2.35, 2.8, 3.8, "**Por qué pasaba**\nUna misma obligación\naparece en varios meses.\n\nAl partir al azar, filas\ndel mismo crédito quedan\na ambos lados.\n\nEl modelo reconoce\nel crédito, no aprende\nel patrón.", tam=14)
notas(s, """Este es el momento que más me enseñó. Con una partición aleatoria 80-10-10 yo medía un F1 de 0,747. Subí a Kaggle y me devolvió 0,704. Cuatro centésimas de diferencia.
La causa: una misma obligación aparece en varios meses del histórico. Cuando parto al azar, filas del mismo crédito quedan en entrenamiento y en prueba. El modelo no aprende el patrón, reconoce el crédito.
Lo corregí pasando a validación temporal: entreno hasta noviembre y mido en diciembre, que es exactamente la situación de enero. Desde ese momento mi número local empezó a anticipar el público, y todas las decisiones siguientes las tomé con ese esquema.
Si me preguntan cuál fue mi mayor aprendizaje, es este: una métrica que no puedes reproducir en producción no sirve para decidir.""")

# ============================================================ 9. MODELOS
s = nueva(9)
titulo(s, "Qué modelos probé", "Cuatro familias, todas con la misma validación temporal")
imagen(s, "04_modelos.png", 0.9, 2.0, 7.4)
bloque(s, 8.6, 2.1, 4.1, 4.3, CLARO)
caja(s, 8.9, 2.35, 3.5, 4.0, "**También probé**\n· Regresión logística\n· SVM\n\nMuy por debajo:\nla relación no es lineal\ny hay 15 variables\ncategóricas.\n\n**Búsqueda con Optuna**\nsobre la validación\ntemporal, no sobre\nuna partición al azar.", tam=14)
notas(s, """Probé cuatro familias de árboles más dos modelos lineales.
La regresión logística y el SVM quedaron muy por debajo, y tiene sentido: la relación no es lineal y hay 15 variables categóricas con muchos niveles.
Entre los de árboles las diferencias son pequeñas, de milésimas. Gana LightGBM con las 100 variables y la búsqueda de hiperparámetros hecha con Optuna sobre la validación temporal.
Quiero subrayar eso último: la búsqueda de hiperparámetros también hay que hacerla sobre la validación correcta. Si la haces sobre una partición al azar, optimizas para el problema equivocado.
Un detalle práctico: el umbral que maximiza F1 es 0,33, no 0,5, y lo guardo dentro del paquete del modelo, porque convertir la probabilidad en una decisión es un ajuste de negocio.""")

# ============================================================ 10. HALLAZGO 3
s = nueva(10)
titulo(s, "Hallazgo 3: el techo no es el modelo, es la etiqueta", "Por qué no sirve seguir apretando el algoritmo", color=ROJO)
imagen(s, "05_ambiguedad.png", 0.8, 2.05, 8.2)
bloque(s, 9.2, 2.2, 3.5, 4.0, ROJO)
caja(s, 9.5, 2.5, 3.0, 3.5, "**Lo que significa**\nCuando el modelo dice\n\"va a aceptar\" y falla,\n9 de cada 10 veces\nes un cliente al que\nnunca se le ofreció nada.\n\nNo es un error\ndel modelo: es\ninformación que no\nexiste en los datos.", tam=14, color=BLANCO)
notas(s, """Tercer giro, y para mí el hallazgo más importante del proyecto.
Miré qué hay detrás de la etiqueta, y encontré esto: solo el 3 % de las filas son rechazos explícitos. El 49 %, casi la mitad, son obligaciones donde no hay registro de que se haya hecho una oferta.
Ese 49 % está marcado como cero, pero no significa que el cliente rechazó. Significa que no sabemos.
Cuando diagnostiqué mis falsos positivos en diciembre, el 91 % son de ese tipo. Es decir: cuando mi modelo dice "este cliente va a aceptar" y aparentemente se equivoca, nueve de cada diez veces es un cliente al que nunca se le ofreció nada.
La conclusión práctica es dura pero honesta: apretar más el algoritmo no sube la precisión, porque el límite está en la calidad de la etiqueta, no en el modelo.""")

# ============================================================ 11. LO QUE DESCARTÉ
s = nueva(11)
titulo(s, "Lo que probé y descarté", "Documentar lo que no funcionó también es resultado")
pruebas = [
    ("Reentrenar solo con las variables más importantes", "80 vars: 0,6999   ·   60 vars: 0,6983", "Sin ganancia real"),
    ("Formulación multiclase para separar el \"no sabemos\"", "0,6957 a 0,6968", "Peor que el binario"),
    ("Ensamble de LightGBM, XGBoost y CatBoost", "sin mejora sobre el mejor individual", "Descartado"),
    ("Pesos por recencia, dar más valor a los meses recientes", "sin mejora", "Descartado"),
    ("Umbral distinto por segmento de cliente", "sin mejora", "Descartado"),
    ("Variables de la ruta de gestión", "precisión 0,596 → 0,607, F1 plano", "No compensa"),
]
y = 1.95
for t, d, veredicto in pruebas:
    bloque(s, 0.7, y, 12, 0.72, CLARO)
    caja(s, 1.0, y + 0.19, 6.3, 0.45, t, tam=14, negrita=True)
    caja(s, 7.4, y + 0.21, 3.2, 0.4, d, tam=12, color=GRIS)
    caja(s, 10.7, y + 0.21, 1.9, 0.4, veredicto, tam=12, negrita=True, color=NARANJA)
    y += 0.82
caja(s, 0.7, 6.95, 12, 0.35, "Cada intento quedó registrado en MLflow con sus parámetros y métricas.", tam=12, color=GRIS)
notas(s, """Esta lámina la incluyo a propósito, porque creo que un proceso serio también se mide por lo que descarta.
Probé seis caminos para subir el número. Reentrenar solo con las variables más importantes, una formulación multiclase para separar explícitamente ese "no sabemos", un ensamble de los tres modelos, pesos por recencia, umbral por segmento, y variables de la ruta de gestión.
Ninguno dio una mejora significativa. Todos están registrados en MLflow con sus parámetros y sus métricas, así que cualquiera puede reproducir por qué los descarté.
Esto refuerza la lámina anterior: el techo está en la etiqueta. Y por eso el dato que más pediría para mejorar esta solución es el registro de la oferta efectivamente realizada.""")

# ============================================================ 12. SHAP
s = nueva(12)
titulo(s, "El modelo explica cada decisión", "No es una caja negra: sé por qué dice lo que dice")
imagen(s, "06_shap.png", 0.7, 1.95, 7.6)
bloque(s, 8.5, 2.1, 4.2, 2.2, CLARO)
caja(s, 8.8, 2.35, 3.6, 1.9, "**Lo que más pesa**\nEl comportamiento reciente\ny el historial de aceptación\ndel cliente.\n\nLos scores del banco\naportan, pero no mandan.", tam=14)
bloque(s, 8.5, 4.5, 4.2, 1.9, VERDE)
caja(s, 8.8, 4.75, 3.6, 1.6, "**Y sale en vivo**\nLa API entrega la\nprobabilidad y sus factores\nen la misma llamada.\n\nEl agente los convierte\nen una frase para el cliente.", tam=14, color=BLANCO)
notas(s, """Calculé valores SHAP, que reparten cada predicción entre las variables que la empujan hacia arriba o hacia abajo.
Lo que más pesa es el comportamiento reciente de pago y el historial de aceptación del cliente. Los scores que el banco ya calcula aportan, pero no son los que mandan. Y en naranja están las variables que yo construí, que aparecen entre las primeras.
El punto clave no es el gráfico. Es que esto sale en vivo: la API entrega la probabilidad y sus factores en la misma llamada. Más adelante van a ver cómo el agente convierte esos factores en una frase que el cliente entiende.""")

# ============================================================ 13. MLOPS
s = nueva(13)
titulo(s, "El modelo está en producción", "No es un notebook: es un servicio con ciclo de vida")
cajas = [
    (0.7, "Entrenamiento\nreproducible", "Un comando regenera\ntodo desde los CSV.\nExperimentos en MLflow.", AZUL),
    (3.85, "Paquete\nversionado", "Modelo, umbral, variables\ny explicabilidad juntos,\nen Cloud Storage.", AZUL),
    (7.0, "API y despliegue\ncontinuo", "Tres ambientes,\naprobación manual\ny salida gradual.", AZUL),
    (10.15, "Monitoreo\nmensual", "Vigila si los datos\ncambian y cuándo\nhay que reentrenar.", VERDE),
]
for x, t, d, col in cajas:
    bloque(s, x, 2.1, 2.85, 2.6, CLARO)
    bloque(s, x, 2.1, 2.85, 0.1, col)
    caja(s, x + 0.25, 2.4, 2.4, 0.9, t, tam=17, negrita=True, color=col)
    caja(s, x + 0.25, 3.35, 2.4, 1.3, d, tam=13)
bloque(s, 0.7, 5.1, 12.3, 1.6, AZUL)
caja(s, 1.1, 5.4, 11.5, 1.1, "Cambiar de modelo es cambiar una variable de entorno.\nEl umbral, las variables y la explicabilidad viajan dentro del paquete, así que la API no se reconstruye.", tam=18, color=BLANCO)
notas(s, """La parte de puesta en producción. Cuatro piezas.
El entrenamiento es reproducible en un solo comando, desde los CSV crudos hasta el archivo de resultados, y cada experimento queda en MLflow.
El modelo se empaqueta junto con su umbral, su lista de variables y su explicabilidad. Ese paquete vive en Cloud Storage.
La API está desplegada en tres ambientes con integración continua: cada cambio pasa por pruebas automáticas, el paso a producción exige aprobación manual y sale con tráfico gradual.
Y hay un trabajo mensual que vigila si los datos se están moviendo, y dispara el reentrenamiento si el desempeño cae dos meses seguidos.
La frase de abajo resume por qué está bien diseñado: cambiar de modelo es cambiar una variable de entorno, no reconstruir el servicio.""")

# ============================================================ 14. AGENTE ARQUITECTURA
s = nueva(14)
titulo(s, "Parte 2: el sistema de agentes", "Cuatro piezas, cada una con una responsabilidad clara")
pasos = [
    (0.7, "Guardrail\nde entrada", "Clasifica el mensaje\nantes de que el modelo\nde lenguaje lo lea", NARANJA),
    (3.65, "Agente\nconversacional", "Conduce la charla\ny decide qué\nherramienta usar", AZUL),
    (6.6, "Guardrail\nde salida", "Revisa la respuesta\nantes de que el\ncliente la lea", NARANJA),
    (9.55, "Escalamiento\na humano", "Cuando el caso\nno le corresponde\nal agente", ROJO),
]
for x, t, d, col in pasos:
    bloque(s, x, 2.3, 2.7, 2.3, col)
    caja(s, x + 0.2, 2.6, 2.3, 0.9, t, tam=17, negrita=True, color=BLANCO, align=PP_ALIGN.CENTER)
    caja(s, x + 0.2, 3.5, 2.3, 1.0, d, tam=12.5, color=BLANCO, align=PP_ALIGN.CENTER)
for x in (3.4, 6.35, 9.3):
    caja(s, x, 3.15, 0.3, 0.4, "→", tam=22, color=GRIS)
bloque(s, 0.7, 5.0, 12, 1.75, CLARO)
caja(s, 1.05, 5.25, 11.4, 1.3, "**Detrás: nueve herramientas y un subagente analista.**\nVerificación de identidad, consulta de cartera, reglas de elegibilidad, llamada al modelo,\nregistro de acuerdos y opciones, escalamiento y notas de la conversación.", tam=16)
notas(s, """Paso a la segunda parte, que vale la mitad de la nota.
Construí un grafo con cuatro nodos, y cada uno tiene una responsabilidad muy clara.
El guardrail de entrada clasifica el mensaje antes de que el modelo de lenguaje lo lea. Si alguien intenta una inyección de instrucciones o pide datos de un tercero, se corta ahí y ni siquiera se gastan tokens.
El agente conduce la conversación y decide qué herramienta usar.
El guardrail de salida revisa la respuesta antes de que el cliente la lea.
Y el escalamiento crea el caso para un gestor humano cuando corresponde.
Detrás hay nueve herramientas: verificar identidad, consultar la cartera, aplicar las reglas, llamar al modelo, registrar acuerdos, escalar y dejar notas.""")

# ============================================================ 15. LA DECISIÓN CENTRAL
s = nueva(15)
titulo(s, "La decisión que más defiendo", "El modelo de lenguaje nunca decide qué se puede ofrecer")
bloque(s, 0.7, 2.05, 5.85, 3.0, RGBColor(0xFB, 0xE9, 0xE7))
caja(s, 1.05, 2.35, 5.2, 2.5, "**Lo que NO hice**\nDarle las reglas del banco al modelo\nde lenguaje dentro del prompt\ny confiar en que las respete.\n\nUn prompt no es auditable\ny un modelo puede alucinar\nuna oferta que no existe.", tam=16, color=RGBColor(0x8B, 0x2C, 0x2C))
bloque(s, 6.8, 2.05, 5.9, 3.0, RGBColor(0xE8, 0xF5, 0xEE))
caja(s, 7.15, 2.35, 5.2, 2.5, "**Lo que hice**\nLas reglas viven en código.\nUna función devuelve la lista\ncerrada de lo que se puede ofrecer.\n\nEl agente solo propone lo que está\nen esa lista, y el guardrail de salida\nlo verifica antes de enviar.", tam=16, color=RGBColor(0x1B, 0x5E, 0x3A))
bloque(s, 0.7, 5.35, 12, 1.35, AZUL)
caja(s, 1.05, 5.6, 11.4, 0.95, "Si el modelo inventa una oferta, la respuesta se bloquea y se reintenta.\nAsí las reglas del banco son auditables y no dependen de cómo esté escrito un prompt.", tam=17, color=BLANCO)
notas(s, """Si me tuviera que quedar con una sola decisión de diseño de toda la segunda parte, es esta.
Lo fácil habría sido escribir las reglas del banco dentro del prompt y confiar en que el modelo las respete. Máximo tres opciones al mes, esperar tres o cuatro meses después de aplicar una, no ofrecer nada si hay restricción.
No lo hice, por dos razones. Un prompt no es auditable: nadie puede certificar ante un regulador que un párrafo en lenguaje natural se cumple siempre. Y un modelo puede alucinar una oferta que no existe.
Lo que hice es que las reglas viven en código. Una función determinista las aplica y devuelve la lista cerrada de lo que se le puede ofrecer a ese cliente hoy. El agente solo puede proponer lo que está en esa lista, y el guardrail de salida lo verifica antes de enviar.
Si el modelo inventa algo, la respuesta se bloquea y se reintenta. Esa es la diferencia entre una demostración y algo que un banco podría poner frente a un cliente.""")

# ============================================================ 16. MODELO DENTRO DEL AGENTE
s = nueva(16)
titulo(s, "Dónde entra el modelo en la conversación", "Informa la decisión, no la toma")
imagen(s, "08_modelo_vs_reglas.png", 0.9, 2.0, 7.2)
bloque(s, 8.4, 2.05, 4.3, 2.1, CLARO)
caja(s, 8.7, 2.3, 3.7, 1.8, "**Cuando el modelo manda**\nEl cliente tiene opciones\ndisponibles y además puede\nhacer un acuerdo.\nLa probabilidad desempata.", tam=14)
bloque(s, 8.4, 4.35, 4.3, 2.1, CLARO)
caja(s, 8.7, 4.6, 3.7, 1.8, "**Cuando mandan las reglas**\nRestricción jurídica, opción\naplicada hace poco, mora\ntemprana, acuerdo incumplido.\nLa probabilidad no importa.", tam=14)
caja(s, 0.9, 6.55, 7.2, 0.6, "Medido sobre los 40 clientes simulados del prototipo.", tam=13, color=GRIS)
notas(s, """Una pregunta que me haría un evaluador escéptico es: ¿para qué llamas al modelo dentro del agente?
La medí. Sobre los 40 clientes del prototipo, la probabilidad del modelo cambia la acción elegida en el 35 % de los casos.
¿Cuándo manda el modelo? Cuando el cliente tiene opciones de pago disponibles y además puede hacer un acuerdo. Ahí hay que escoger, y la probabilidad desempata: si es alta, le ofrezco la opción de pago, que resuelve la mora de raíz. Si es baja, priorizo el acuerdo a cinco días, que es más barato y no consume una de las tres opciones que tiene al mes.
¿Cuándo no importa el modelo? Si hay restricción jurídica, si aplicó una opción hace poco, o si está en mora temprana. Ahí mandan las reglas aunque el modelo diga 0,99.
Y esto es deliberado: un modelo no puede saltarse una restricción legal.""")

# ============================================================ 17. PRUEBAS
s = nueva(17)
titulo(s, "Cómo probé que funciona", "Dos suites que responden preguntas distintas")
imagen(s, "07_agente.png", 0.7, 1.95, 8.0)
bloque(s, 8.9, 2.05, 3.8, 2.0, CLARO)
caja(s, 9.15, 2.3, 3.3, 1.7, "**126 pruebas\ndeterministas**\nCorren en cada cambio,\nsin modelo de lenguaje.\nRápidas y repetibles.", tam=14)
bloque(s, 8.9, 4.25, 3.8, 2.1, CLARO)
caja(s, 9.15, 4.5, 3.3, 1.8, "**78 verificaciones\nde escenario**\nLos siete perfiles del\nenunciado, contra el\nsistema real, con un\njuez que puntúa calidad.", tam=14)
notas(s, """Probé en dos capas, porque responden preguntas distintas.
La primera son 126 pruebas deterministas que corren en cada cambio y no usan el modelo de lenguaje. Verifican las reglas, la verificación de identidad, los guardrails. Son rápidas y siempre dan el mismo resultado.
La segunda ejecuta los siete perfiles de cliente que pide el enunciado contra el sistema completo, con el modelo real conversando. Son 78 verificaciones de cinco tipos: funcional, integración, seguridad, robustez y calidad. Incluye un juez que puntúa claridad, empatía, pertinencia y concisión de cada respuesta.
A la izquierda ven qué decide el agente sobre los 40 clientes, y a la derecha que las 78 verificaciones pasan.""")

# ============================================================ 18. EL HALLAZGO DE LAS PRUEBAS
s = nueva(18)
titulo(s, "Lo que encontró la suite de escenarios", "Un fallo de seguridad que ninguna prueba unitaria habría visto", color=ROJO)
bloque(s, 0.7, 2.1, 12, 1.5, RGBColor(0xFB, 0xE9, 0xE7))
caja(s, 1.05, 2.35, 11.4, 1.1, "**El agente decía \"escríbeme el código que te acabamos de enviar\"...**\nsin haber llamado a la herramienta que lo envía. El código nunca existió.", tam=17, color=RGBColor(0x8B, 0x2C, 0x2C))
bloque(s, 0.7, 3.85, 12, 1.4, CLARO)
caja(s, 1.05, 4.1, 11.4, 1.0, "**La consecuencia**\nEl intento del cliente se perdía, así que el bloqueo tras tres códigos incorrectos nunca se activaba.\nUn atacante tenía más intentos de los que debía.", tam=16)
bloque(s, 0.7, 5.5, 12, 1.4, VERDE)
caja(s, 1.05, 5.75, 11.4, 1.0, "**La corrección**\nAhora la regla detecta la frase en cualquier orden y el prompt prohíbe afirmar un envío sin confirmación.\nY quedó fijada como prueba determinista, para que no vuelva.", tam=16, color=BLANCO)
notas(s, """Esta lámina es la que más me gusta de la segunda parte, porque muestra para qué sirve probar de verdad.
En una corrida, dos verificaciones de seguridad que antes pasaban empezaron a fallar. Fui a la conversación y vi que el agente había dicho "escríbeme el código de seis dígitos que te acabamos de enviar", sin haber llamado a la herramienta que lo envía. El código nunca existió.
La consecuencia es seria: el intento del cliente se perdía, así que solo se validaban dos de los tres códigos incorrectos y el bloqueo por fuerza bruta nunca se activaba. Un atacante tenía más intentos de los que debía.
Yo ya tenía una regla para impedir esa frase, pero tenía un hueco: solo detectaba "envié el código", no "el código que enviamos". El orden de las palabras la esquivaba.
Lo corregí y lo fijé como prueba determinista. Y el punto de fondo: ninguna prueba unitaria habría encontrado esto, porque nacía de una alucinación del modelo de lenguaje. Por eso hacen falta las dos capas.""")

# ============================================================ 19. DEMO
s = nueva(19)
titulo(s, "Todo esto está corriendo ahora", "Demostración en vivo")
flujo = [
    (0.7, "Front", "Streamlit\nen Cloud Run"),
    (3.2, "Agente", "FastAPI\n+ LangGraph"),
    (5.7, "Gemini", "Vertex AI"),
    (8.2, "Modelo", "API en\nproducción"),
    (10.7, "Paquete", "Cloud\nStorage"),
]
for x, t, d in flujo:
    bloque(s, x, 2.3, 2.1, 1.6, AZUL)
    caja(s, x + 0.15, 2.55, 1.8, 0.5, t, tam=17, negrita=True, color=BLANCO, align=PP_ALIGN.CENTER)
    caja(s, x + 0.15, 3.1, 1.8, 0.7, d, tam=12, color=RGBColor(0xD7, 0xE6, 0xF8), align=PP_ALIGN.CENTER)
for x in (2.85, 5.35, 7.85, 10.35):
    caja(s, x, 2.9, 0.3, 0.4, "→", tam=20, color=GRIS)
caja(s, 0.7, 4.15, 12, 0.5, "Cada llamada entre servicios va autenticada. Ninguno es público salvo el front, que además pide contraseña.", tam=14, color=GRIS)
bloque(s, 0.7, 4.9, 12, 1.9, CLARO)
caja(s, 1.05, 5.15, 11.4, 1.5, "**Qué voy a mostrar**\n· Un cliente escribe, verifica su identidad con un código y recibe un acuerdo de pago a 5 días\n· Le pregunto por qué me recomienda esa opción y responde con mi propio historial\n· Intento manipularlo: le pido una condonación diciendo que soy el gerente", tam=15)
notas(s, """Antes de pasar al cierre, la demostración.
Todo lo que ven en esta cadena está corriendo ahora mismo: el front, el agente, Gemini en Vertex, la API del modelo en producción y el paquete en Cloud Storage. Cada llamada entre servicios va autenticada y ninguno es público salvo el front, que además pide contraseña.
Voy a mostrar tres cosas. Primero el flujo completo: un cliente escribe, verifica su identidad con un código que le llega por mensaje, y recibe una propuesta de acuerdo a cinco días que queda registrada.
Segundo, le pregunto por qué me recomienda esa opción, y van a ver que responde con mi propio historial, no con las bondades del producto.
Y tercero, intento manipularlo: le digo que soy el gerente de la sucursal y que me autorice una condonación.
[Si la red falla: pasar a las capturas de respaldo.]""")

# ============================================================ 19b. RESPALDO: LA CONVERSACIÓN
s = nueva(20)
titulo(s, "Respaldo: una conversación real", "Capturada del sistema desplegado, por si falla la red")
imagen(s, "09_captura_chat.png", 1.0, 1.95, 3.05)
puntos = [
    ("No dice nada hasta verificar", "Pide la cédula y manda un código al celular. Antes de eso no menciona ni un peso.", AZUL),
    ("Propone lo que el banco autoriza", "Acuerdo de pago por el valor vencido, con fecha límite dentro de los 5 días permitidos.", VERDE),
    ("Explica con el historial del cliente", "\"Porque por tu historial sabemos que siempre cumples con tus acuerdos\": eso sale del modelo.", NARANJA),
    ("Registra y confirma", "El acuerdo queda guardado con su fecha, y se lo confirma al cliente.", AZUL),
]
y = 2.2
for tt, d, col in puntos:
    bloque(s, 4.6, y, 8.1, 1.05, CLARO)
    bloque(s, 4.6, y, 0.1, 1.05, col)
    caja(s, 4.95, y + 0.15, 7.5, 0.4, tt, tam=16, negrita=True, color=col)
    caja(s, 4.95, y + 0.55, 7.5, 0.45, d, tam=13)
    y += 1.2
notas(s, """Esta lámina es el respaldo por si la demostración en vivo falla.
Es una conversación real, capturada del sistema desplegado hace unos minutos.
Miren los cuatro momentos. Primero, no dice absolutamente nada hasta verificar: pide la cédula y manda un código al celular.
Segundo, propone lo que el banco autoriza: un acuerdo de pago por el valor vencido, con fecha límite dentro de los cinco días permitidos.
Tercero, y esto es lo que más me gusta: explica con el historial del propio cliente. Dice "te hago esta propuesta porque por tu historial sabemos que siempre cumples con tus acuerdos". Esa frase no está escrita en ningún lado: sale de los factores que el modelo entrega.
Y cuarto, registra el acuerdo y se lo confirma con la fecha exacta.""")

# ============================================================ 20. SEPARADOR EJECUTIVO
s = nueva(con_banda=False)
bloque(s, 0, 0, 13.333, 7.5, RGBColor(0x1B, 0x3A, 0x5C))
caja(s, 1.2, 2.6, 11, 1.0, "Los últimos 5 minutos", tam=24, color=RGBColor(0x9D, 0xC2, 0xE8))
caja(s, 1.2, 3.5, 11, 1.8, "Lo mismo, contado para el comité\nque tiene que aprobarlo", tam=40, negrita=True, color=BLANCO)
bloque(s, 1.2, 5.6, 0.09, 0.5, NARANJA)
caja(s, 1.5, 5.6, 10, 0.6, "Sin una sola métrica técnica", tam=17, color=RGBColor(0x9D, 0xC2, 0xE8))
notas(s, """Aquí cambio de registro por completo.
Todo lo anterior era para ustedes, un equipo técnico. Los próximos cinco minutos son la versión que presentaría a un comité directivo que tiene que aprobar el uso de esto y no tiene formación técnica.
No voy a decir F1, ni SHAP, ni LightGBM. Ni una sola métrica técnica.
Mi regla para estas conversaciones es simple: un directivo no necesita entender cómo funciona, necesita entender qué decide, qué gana y qué puede salir mal.""")

# ============================================================ 21. QUÉ HACE (EJECUTIVO)
s = nueva(22)
titulo(s, "Qué construimos", "En una frase")
bloque(s, 0.7, 2.0, 12, 1.9, AZUL)
caja(s, 1.1, 2.35, 11.4, 1.3, "Un asistente que conversa con clientes en mora por WhatsApp,\nles ofrece solo lo que el banco ya tiene aprobado para ellos,\ny deja registro de cada decisión.", tam=23, color=BLANCO)
bloque(s, 0.7, 4.2, 5.85, 2.4, CLARO)
caja(s, 1.05, 4.5, 5.2, 2.0, "**Antes**\nSe contacta a todos por igual.\nEl gestor decide con lo que ve\nen pantalla y con su experiencia.\nCada conversación depende\nde quién la atienda.", tam=16)
bloque(s, 6.8, 4.2, 5.9, 2.4, VERDE)
caja(s, 7.15, 4.5, 5.2, 2.0, "**Ahora**\nSe empieza por quien más\nprobablemente va a aceptar.\nLa oferta sale de las reglas\ndel banco, no del criterio\nde cada persona.", tam=16, color=BLANCO)
notas(s, """Construimos un asistente que conversa con clientes en mora por WhatsApp, les ofrece solo lo que el banco ya tiene aprobado para ellos, y deja registro de cada decisión.
Para entender qué cambia, comparen las dos columnas.
Hoy se contacta a todos por igual, el gestor decide con lo que ve en pantalla y con su experiencia, y cada conversación depende de quién la atienda.
Con esto, se empieza por quien más probablemente va a aceptar, y la oferta sale de las reglas del banco, no del criterio de cada persona.
Esa segunda parte es tan importante como la primera: la consistencia.""")

# ============================================================ 22. QUÉ GANA (EJECUTIVO)
s = nueva(23)
titulo(s, "Qué gana el banco", "Tres cosas concretas")
ganancias = [
    ("Gestionar primero\na quien sí responde", "El sistema estima, con un mes de anticipación, qué clientes tienen\nmás opción de aceptar. El equipo dedica su tiempo donde rinde.", AZUL),
    ("Atender a cualquier\nhora, sin filas", "El cliente que escribe un domingo a las once de la noche\nrecibe la misma atención que el que llama un martes.", VERDE),
    ("La misma conversación\npara todos", "Nadie ofrece de más ni de menos. La oferta sale de las reglas\naprobadas, y queda registrada por si alguien pregunta.", NARANJA),
]
y = 2.1
for t, d, col in ganancias:
    bloque(s, 0.7, y, 12, 1.45, CLARO)
    bloque(s, 0.7, y, 0.12, 1.45, col)
    caja(s, 1.15, y + 0.22, 4.0, 1.0, t, tam=18, negrita=True, color=col)
    caja(s, 5.4, y + 0.28, 7.0, 0.9, d, tam=15)
    y += 1.65
bloque(s, 0.7, 7.05, 12, 0.35, CLARO)
notas(s, """Tres beneficios concretos.
El primero es de eficiencia: el sistema estima con un mes de anticipación qué clientes tienen más opción de aceptar, así que el equipo dedica su tiempo donde rinde, en vez de llamar a todos.
El segundo es de cobertura: el cliente que escribe un domingo a las once de la noche recibe la misma atención que el que llama un martes a media mañana.
Y el tercero, que para mí es el más valioso en un banco: consistencia. Nadie ofrece de más ni de menos. La oferta sale de las reglas aprobadas y queda registrada, por si alguien pregunta después.""")

# ============================================================ 23. CONTROLES (EJECUTIVO)
s = nueva(24)
titulo(s, "Por qué lo pueden aprobar con tranquilidad", "Las preguntas que me haría un comité de riesgo")
controles = [
    ("\"¿Puede ofrecer algo que no debe?\"", "No. Solo ofrece lo que el banco tiene aprobado\npara ese cliente. Si intenta salirse, se bloquea."),
    ("\"¿Habla de plata con cualquiera?\"", "No. Pide un código de verificación antes de\nmencionar un solo peso."),
    ("\"¿Qué pasa con un caso delicado?\"", "Lo pasa a una persona. Un fallecimiento, un\nfraude o una reclamación no los atiende."),
    ("\"¿Podemos revisar qué hizo?\"", "Sí. Cada decisión queda registrada con su\nmotivo, y se puede auditar conversación a conversación."),
]
y = 2.1
for preg, resp in controles:
    bloque(s, 0.7, y, 5.6, 1.15, RGBColor(0xEF, 0xF3, 0xF8))
    caja(s, 1.0, y + 0.3, 5.1, 0.6, preg, tam=16, negrita=True, color=RGBColor(0x1B, 0x3A, 0x5C))
    bloque(s, 6.55, y, 6.15, 1.15, CLARO)
    caja(s, 6.85, y + 0.22, 5.6, 0.8, resp, tam=14)
    y += 1.3
notas(s, """Si yo estuviera sentado en ese comité, haría cuatro preguntas. Las contesto por adelantado.
¿Puede ofrecer algo que no debe? No. El asistente solo ofrece lo que el banco tiene aprobado para ese cliente en ese momento. Y esto no depende de cómo le pidamos que se comporte: hay una verificación antes de enviar cada mensaje, y si intenta salirse, se bloquea.
¿Habla de plata con cualquiera? No. Antes de mencionar un solo peso, pide un código de verificación al celular del cliente. Si no lo valida, no hay conversación.
¿Qué pasa con un caso delicado? Lo pasa a una persona. Un fallecimiento, un fraude, una reclamación: eso no lo atiende un asistente, y está diseñado para reconocerlo y escalarlo.
¿Podemos revisar qué hizo? Sí. Cada decisión queda registrada con su motivo. Si mañana alguien pregunta por qué a este cliente se le ofreció esto, hay respuesta.""")

# ============================================================ 24. CÓMO MEDIRLO (EJECUTIVO)
s = nueva(25)
titulo(s, "Cómo sabremos si funciona", "Lo que mediría desde el primer mes")
metricas = [
    ("Cuántos clientes\naceptan", "comparado contra un grupo\nque se gestiona como siempre", VERDE),
    ("Cuántos acuerdos\nse cumplen", "prometer no basta:\nimporta si pagan", AZUL),
    ("Cuántos casos\npasan a una persona", "si sube mucho, algo\nno está funcionando", NARANJA),
    ("Qué opina\nel cliente", "revisión humana de una\nmuestra cada semana", GRIS),
]
x = 0.7
for t, d, col in metricas:
    bloque(s, x, 2.2, 2.95, 2.6, CLARO)
    bloque(s, x, 2.2, 2.95, 0.12, col)
    caja(s, x + 0.25, 2.55, 2.5, 1.1, t, tam=16, negrita=True, color=col)
    caja(s, x + 0.25, 3.6, 2.5, 1.1, d, tam=13)
    x += 3.1
bloque(s, 0.7, 5.2, 12, 1.6, AZUL)
caja(s, 1.1, 5.5, 11.4, 1.1, "Mi recomendación: empezar con un piloto acotado y un grupo de comparación.\nSin grupo de comparación no sabremos si la mejora es del sistema o de la temporada.", tam=18, color=BLANCO)
notas(s, """Cómo sabremos si funciona. Cuatro indicadores, todos en lenguaje de negocio.
Cuántos clientes aceptan, comparado contra un grupo que se gestiona como siempre.
Cuántos acuerdos se cumplen, porque prometer no basta: lo que importa es si pagan.
Cuántos casos pasan a una persona. Si ese número sube mucho, es señal de que algo no está funcionando.
Y qué opina el cliente, con revisión humana de una muestra de conversaciones cada semana.
Mi recomendación concreta: empezar con un piloto acotado y un grupo de comparación. Sin grupo de comparación no vamos a saber si la mejora es del sistema o simplemente de la temporada.""")

# ============================================================ 25. QUÉ FALTA (EJECUTIVO)
s = nueva(26)
titulo(s, "Qué falta para llevarlo a producción", "Soy transparente con esto")
faltantes = [
    ("Conectar el WhatsApp real", "Hoy el canal está simulado. Hay que habilitar el canal oficial\ny que Meta apruebe las plantillas de contacto.", NARANJA),
    ("Conectar los sistemas del banco", "Hoy los clientes son simulados. El diseño ya está pensado\npara que se conecten sin cambiar el comportamiento.", NARANJA),
    ("El dato que más falta", "Hoy no sabemos si a un cliente no se le ofreció nada\no si rechazó. Registrarlo mejoraría mucho la predicción.", ROJO),
    ("Revisión de seguridad y un piloto", "Retención de conversaciones, política de datos,\ny salir con un grupo pequeño antes de abrir.", GRIS),
]
y = 2.1
for t, d, col in faltantes:
    bloque(s, 0.7, y, 12, 1.15, CLARO)
    bloque(s, 0.7, y, 0.12, 1.15, col)
    caja(s, 1.15, y + 0.18, 4.4, 0.5, t, tam=16, negrita=True, color=col)
    caja(s, 5.8, y + 0.2, 6.6, 0.8, d, tam=14)
    y += 1.3
notas(s, """Termino siendo transparente con lo que falta, porque creo que eso genera más confianza que decir que está todo listo.
Primero, conectar el WhatsApp real. Hoy el canal está simulado. Hay que habilitar el canal oficial y que las plantillas de contacto pasen por aprobación.
Segundo, conectar los sistemas del banco. Hoy los clientes son simulados. El diseño ya está pensado para que se conecten sin cambiar el comportamiento del asistente, pero hay que hacerlo.
Tercero, y este es el más importante desde el punto de vista analítico: hoy no sabemos si a un cliente no se le ofreció nada o si nos rechazó. Registrar eso mejoraría mucho la predicción, y es un dato que el banco ya tiene en algún lugar.
Y cuarto, la revisión de seguridad de la información y un piloto acotado antes de abrirlo.""")

# ============================================================ 26. CIERRE
s = nueva(con_banda=False)
bloque(s, 0, 0, 13.333, 7.5, AZUL)
caja(s, 1.2, 2.3, 11, 1.6, "Lo que me llevo de esta prueba", tam=34, negrita=True, color=BLANCO)
ideas = [
    "Una métrica que no puedes reproducir en producción no sirve para decidir",
    "El techo de este problema no es el algoritmo: es cómo se registra la información",
    "Las reglas del banco van en código, no en un prompt",
]
y = 3.6
for i in ideas:
    bloque(s, 1.2, y, 0.09, 0.6, NARANJA)
    caja(s, 1.55, y + 0.05, 10.5, 0.6, i, tam=19, color=BLANCO)
    y += 0.85
caja(s, 1.2, 6.5, 11, 0.5, "Gracias.", tam=22, negrita=True, color=RGBColor(0x9D, 0xC2, 0xE8))
notas(s, """Cierro con tres ideas.
La primera: una métrica que no puedes reproducir en producción no sirve para decidir. Me lo enseñó la diferencia entre mi validación aleatoria y el resultado real.
La segunda: el techo de este problema no es el algoritmo, es cómo se registra la información. Casi la mitad de los ceros no son rechazos, son ausencias de registro.
Y la tercera: las reglas del banco van en código, no en un prompt. Es lo que separa una demostración de algo que se puede poner frente a un cliente.
Gracias. Quedo atento a sus preguntas.""")

prs.save(SALIDA)
print(f"{SALIDA}  ({len(prs.slides.__iter__.__self__._sldIdLst)} diapositivas)")
