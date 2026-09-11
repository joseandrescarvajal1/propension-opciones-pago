# Documento técnico

Prueba Analítica: Modelo Opciones de Pago (season 3). Entregable 1.
Repositorio: https://github.com/joseandrescarvajal1/propension-opciones-pago
Arquitectura, operación y diagramas: `docs/arquitectura.md`

### Resultados

| | |
|---|---|
| F1 público (Kaggle) | 0,71421 |
| F1 / AUC en diciembre (validación temporal) | 0,6972 / 0,7659 |
| Umbral · variables | 0,33 · 100 |
| Pruebas | 126 deterministas · 78 verificaciones de escenario |
| Desplegado en Cloud Run | modelo, agente y front |

---

## Parte 1. Solución analítica

**Dataset.** Uní las cinco fuentes por obligación y mes con una regla que me impuse desde el
principio: toda variable se corta en t-1, porque usar el mes en curso es fuga y en producción esos
datos no existen. Construí 156 variables y elegí 100.

**El hallazgo que cambió mi enfoque.** Con partición aleatoria obtenía F1 de 0,747, pero Kaggle me
devolvía 0,704. Entendí que una misma obligación aparece en varios meses, así que esa partición
filtra información entre conjuntos. Pasé a validación temporal, entrenando hasta noviembre y
midiendo en diciembre, y desde ahí el resultado local anticipó el público.

**Modelo.** LightGBM con Optuna sobre esa validación. El umbral óptimo resultó 0,33, no 0,5, y lo
guardé dentro del paquete: convertir probabilidad en clase es una decisión de negocio que quiero
poder ajustar sin reentrenar.

**Techo de la métrica.** El 49 % de los ceros son obligaciones sin registro de oferta: no se sabe
si el cliente rechazó o nunca se le ofreció, y de ese tipo es el 91 % de mis falsos positivos. La
precisión la limita la ambigüedad de la etiqueta, no el modelo.

**Producción.** Dejé el entrenamiento reproducible en un comando, el paquete versionado en Cloud
Storage, la API en Cloud Run con despliegue continuo y monitoreo mensual de deriva.

## Parte 2. Sistema agéntico

Diseñé un grafo de LangGraph: guardrail de entrada, agente sobre Gemini en Vertex AI, guardrail de
salida y escalamiento a gestor humano, con nueve herramientas.

**Mi decisión central.** El modelo de lenguaje nunca decide qué se puede ofrecer. Una herramienta
determinista aplica las reglas y devuelve la lista cerrada de ofertas autorizadas; el agente solo
propone lo que está en ella y el guardrail lo verifica. Si inventa una oferta, la respuesta se
bloquea. Así las reglas quedan auditables.

**Integración.** El agente consume `/explain` y recibe la probabilidad y los factores que la
explican. La probabilidad desempata entre ofrecer una opción o proponer un acuerdo a cinco días:
medí que cambia la acción en el 35 % de los casos. Los factores son la justificación que lee el
cliente.

**Seguridad.** Exijo un código de un solo uso antes de revelar cualquier dato. Las herramientas
piden identidad verificada, así que el acceso no depende del criterio del modelo; los guardrails
detienen inyección, suplantación y consultas sobre terceros.

**Evaluación.** Monté una suite determinista que corre en cada cambio y otra que ejecuta los siete
perfiles del enunciado contra el sistema real. Esta detectó que el agente decía haber enviado un
código sin llamar a la herramienta, evitando el bloqueo por fuerza bruta: nacía de una
alucinación, así que ninguna prueba unitaria lo habría visto.

## Supuestos, riesgos y conclusión

**Supuestos y riesgos.** Asumí que "interesado sin aceptar" cuenta como aceptación, según la
definición de negocio; modelé las reglas desde el enunciado; los clientes del prototipo son
simulados. La ambigüedad de la etiqueta limita el F1 alcanzable y la cuota del modelo de lenguaje
debe reservarse antes de operar con volumen.

**Conclusión.** Entrego la solución desplegada y validada de extremo a extremo. Para mí el valor
no está en la última décima de F1, sino en convertir la probabilidad en una acción concreta,
trazable y auditable. Lo que más la mejoraría es registrar la oferta realizada, techo actual de la
métrica.

---

## Declaración de uso de inteligencia artificial generativa

Usé Claude Code (Anthropic) como asistente de programación durante todo el desarrollo: código,
sistema agéntico, pruebas, infraestructura y documentación, incluido este texto, que redacté a
partir de la bitácora del proyecto.

Las decisiones fueron mías: el corte temporal en t-1; el cambio a validación temporal tras
detectar la discrepancia con Kaggle; la selección de variables y modelos; el tratamiento de la
ambigüedad de la etiqueta; y la arquitectura agéntica, incluidos Deep Agents, la verificación por
código de un solo uso y los guardrails como nodos del grafo. Revisé y validé cada componente.

La solución usa Gemini 2.5 Flash en Vertex AI y valores SHAP para la explicabilidad.
