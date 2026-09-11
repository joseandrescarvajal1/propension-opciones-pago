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

**Dataset.** Las cinco fuentes se unen por obligación y mes con una regla innegociable: toda
variable se corta en t-1, porque usar el mes en curso es fuga y en producción esos datos no
existen. De 156 variables construidas se seleccionaron 100.

**Hallazgo que cambió el enfoque.** La partición aleatoria daba F1 de 0,747 y Kaggle devolvía
0,704: una misma obligación aparece en varios meses, así que esa partición filtra información
entre conjuntos. Con validación temporal, entrenando hasta noviembre y midiendo en diciembre, el
resultado local pasó a anticipar el público.

**Modelo.** LightGBM con Optuna sobre esa validación. El umbral óptimo es 0,33, no 0,5, y viaja
dentro del paquete: convertir probabilidad en clase es una decisión de negocio, ajustable sin
reentrenar.

**Techo de la métrica.** El 49 % de los ceros son obligaciones sin registro de oferta: no se sabe
si el cliente rechazó o nunca se le ofreció, y de ese tipo es el 91 % de los falsos positivos. La
precisión la limita la ambigüedad de la etiqueta, no el modelo.

**Producción.** Entrenamiento reproducible en un comando, paquete versionado en Cloud Storage, API
en Cloud Run con despliegue continuo y monitoreo mensual de deriva.

## Parte 2. Sistema agéntico

Grafo de LangGraph: guardrail de entrada, agente sobre Gemini en Vertex AI, guardrail de salida y
escalamiento a gestor humano, con nueve herramientas.

**Decisión central.** El modelo de lenguaje nunca decide qué se puede ofrecer. Una herramienta
determinista aplica las reglas y devuelve la lista cerrada de ofertas autorizadas; el agente solo
propone lo que está en ella y el guardrail lo verifica. Si inventa una oferta, la respuesta se
bloquea. Así las reglas quedan auditables.

**Integración.** El agente consume `/explain` y recibe la probabilidad y los factores que la
explican. La probabilidad desempata entre ofrecer una opción o proponer un acuerdo a cinco días:
cambia la acción en el 35 % de los casos. Los factores son la justificación que lee el cliente.

**Seguridad.** Código de un solo uso antes de revelar cualquier dato. Las herramientas exigen
identidad verificada, así que el acceso no depende del criterio del modelo; los guardrails
detienen inyección, suplantación y consultas sobre terceros.

**Evaluación.** Una suite determinista en cada cambio y otra que ejecuta los siete perfiles del
enunciado contra el sistema real. Esta detectó que el agente decía haber enviado un código sin
llamar a la herramienta, evitando el bloqueo por fuerza bruta: nacía de una alucinación, así que
ninguna prueba unitaria lo habría visto.

## Supuestos, riesgos y conclusión

**Supuestos y riesgos.** "Interesado sin aceptar" cuenta como aceptación, según la definición de
negocio; las reglas se modelaron desde el enunciado; los clientes del prototipo son simulados. La
ambigüedad de la etiqueta limita el F1 alcanzable y la cuota del modelo de lenguaje debe
reservarse antes de operar con volumen.

**Conclusión.** La solución está desplegada y validada de extremo a extremo. El valor no está en
la última décima de F1, sino en convertir la probabilidad en una acción concreta, trazable y
auditable. Lo que más la mejoraría es registrar la oferta realizada, techo actual de la métrica.

---

## Declaración de uso de inteligencia artificial generativa

Se utilizó Claude Code (Anthropic) como asistente de programación en todo el desarrollo: código,
sistema agéntico, pruebas, infraestructura y documentación, incluido este texto, redactado a
partir de la bitácora del proyecto.

Las decisiones fueron del candidato: el corte temporal en t-1; el cambio a validación temporal
tras detectar la discrepancia con Kaggle; la selección de variables y modelos; el tratamiento de
la ambigüedad de la etiqueta; y la arquitectura agéntica, incluidos Deep Agents, la verificación
por código de un solo uso y los guardrails como nodos del grafo. Revisó y validó cada componente.

La solución usa Gemini 2.5 Flash en Vertex AI y valores SHAP para la explicabilidad.
