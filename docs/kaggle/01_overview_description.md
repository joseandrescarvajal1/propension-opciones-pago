<!-- Fuente: Kaggle, competencia prueba-analitica-modelo-opciones-de-pago-season-3, pestaña 'Description'. Texto copiado tal cual. -->

##Introducción

Bancolombia cuenta con un gran portafolio de productos de crédito para los diferentes segmentos de clientes; estos son otorgados mes a mes con ciertas obligaciones o compromisos bancarios, con cuotas que por lo general son mensuales. La gran mayoría de los clientes que adquieren una obligación, cumplen con sus promesas de pago, sin embargo, hay un porcentaje de clientes que mes a mes no lo hacen, y se catalogan como “obligaciones morosas”. 

La gestión de esa cartera que entra en mora se empieza a realizar desde el día 1 de mora, bajo diferentes estrategias. Una de ellas, es ofrecerles a los clientes ciertas opciones de pago, para que su altura de mora o días de mora no se incrementen, y por lo tanto, no sea una cartera que termine en procesos de judicialización o castigo, que implicaría amplios gastos de gestión, y hasta perdida del capital expuesto al cliente.
Las opciones de pago son un conjunto de diferentes estrategias que ayudan a alivianar la carga financiera que los clientes en mora están viviendo. Algunos ejemplos de opciones de pago son:

- Ampliaciones de plazo de la deuda
- Reducciones de cuota de la deuda
- Renegociación de tasa de interés
- Reestructuraciones de crédito 

Ahora, esas opciones de pago se manejan como un producto preaprobado, y no todos los clientes tienen acceso a ellas, e incluso solo se les es preaprobado como máximo 3 opciones de pago, por obligación del cliente, por mes. Las aplicaciones de estas opciones de pago son limitadas, es decir, una vez a la obligación se le haya aplicado una opción de pago, esta debe esperar por lo menos de 3 a 4 meses para poder aplicar a otra opción de pago (este tiempo varía dependiendo de la opción de pago aplicada).

Debido a la gran cantidad de clientes que el banco maneja, y que se encuentran en mora, existen diferentes mecanismos de gestión para cada cliente y obligación. Actualmente se cuenta con un sistema de priorización por lotes, basado en la exposición de la deuda y la probabilidad de pago, sin embargo, al negocio le gustaría conocer de forma anticipada (un mes) que tan probable es que un cliente acepte una de las opciones de pago, para que esta sea incorporada como una variable más, dentro de la priorización por lotes que actualmente existe, y de esta forma tener una eficiencia mayor, y una gestión más intensa sobre los clientes con alta probabilidad de aceptar una opción de pago, y por consiguiente ser más eficientes, y contribuir a que el índice de cartera vencida del banco se ralentice.

Además de las opciones de pago, existen acuerdos de pago orientados a la gestión temprana de la mora. Estos consisten en compromisos adquiridos por el cliente para realizar un pago dentro de un plazo máximo de cinco días después del contacto. Su ofrecimiento deberá considerar el perfil del cliente, su situación financiera, el estado de la obligación y las reglas de negocio definidas. Los acuerdos podrán gestionarse de manera recurrente en las distintas etapas de cobranza, siempre que el cliente no haya aceptado una opción de pago y no exista alguna restricción que impida su ofrecimiento.

## Detalle: Esta prueba analítica tiene dos partes:

### 1. Prueba de desarrollo analítico Machine Learning con MLOps

Esta prueba analítica tiene como objetivo diseñar y desarrollar un modelo de pronóstico, para una ventana de un mes, de si el cliente aceptará, o no, una de sus opciones pago preaprobadas; esto, sobre los clientes en mora, y asignados a gestión directa o de aliados.  Será necesario construir y *presentar una solución analítica E2E partiendo de una información dada y exclusivamente de ella para lograr dicho modelo, describiendo claramente como el modelo desarrollado cumple con cada uno de los criterios de MLOps (Preparación datos, Entrenamiento, inferencia, productizacion, despliegue continuo y monitoreo), **si es usted un candidato interno de Bancolombia, muestre como lo haría con los componentes y lineamientos actuales del banco.***

<h2>Definición de variable respuesta</h2>
<p>Se define como un modelo de propensión a la aceptación de opciones pago, al hecho que permita determinar las obligaciones de los clientes que están mora ACEPTEN una de las opciones de pago preaprobadas en el siguiente mes de gestión, para ello se debe construir un modelo de pronóstico donde nuestra variable respuesta es binaria y está definida como:</p>
<p>\[ Y_i = \left\{\begin{matrix}
1 : \textrm{Cuando el cliente i-esimo ACEPTO una opción de pago en su obligación} \\
0 : \textrm{Cuando el cliente i-esimo NO ACEPTO una opción de pago en su obligación}
\end{matrix}\right.
\\
i = 1, 2, ..., n\\
n := \textrm{Cantidad de clientes y obligaciones}
\]</p>

El modelo que debes desarrollar debe entregar la calificación de las obligaciones de un conjunto de clientes para un mes en específico, que no se encuentra en la información entregada para el desarrollo de la solución analítica. 

### 2. Desarrollo de un sistema agentico
 
Proponga e implemente un prototipo funcional de agentes de IA coordinados para gestionar de forma proactiva y reactiva a clientes en mora. El sistema deberá identificar la siguiente mejor acción y ofrecer únicamente acuerdos u opciones de pago para los que el cliente sea elegible, garantizando seguridad de la información, trazabilidad, cumplimiento de las reglas de negocio y escalamiento a un gestor humano cuando corresponda.

El candidato deberá definir y justificar la arquitectura, la responsabilidad del agente o los agentes, su coordinación y la integración con el modelo analítico de la primera parte. Asimismo, deberá demostrar el rendimiento individual del agente (determinado por sus criterios) y del sistema de extremo a extremo mediante pruebas funcionales, de integración, seguridad, robustez y calidad, documentando escenarios, métricas, umbrales de aceptación, resultados y oportunidades de mejora.

Para las pruebas (que ud quiera hacer) podrá utilizar la información proporcionada y complementarla con datos simulados para generar las conversaciones de los clientes y los perfiles de los clientes que utilizaran el sistema agentico, claramente identificados y sin información personal real bajo el criterio que cada uno disponga de cómo crearlo, Así ud también podrá determinar cómo y cuantas pruebas necesita para garantizar que su sistema agentico es robusto para sostener su estrategia de cobranza. Los escenarios o perfiles de clientes a simular son elegidos por el candidato y podrán incluir, entre otros:

La estrategia de cobranza y las reglas de negocio podrán definirse como parte de la prueba, considerando las reglas mínimas establecidas en la introducción para aplicar las opciones y planes de pago. Además, el sistema agentico podrá apoyarse en los resultados de modelos analíticos existentes o en modelos complementarios que usted defina para garantizar su correcto funcionamiento.

Algunos escenarios que debería considerar de perfiles de clientes:
- Cliente con mora temprana y alta probabilidad de pago, al que se le propone un acuerdo de pago dentro de los siguientes cinco días.
- Cliente elegible para varias opciones de pago, para quien el sistema debe seleccionar y explicar la alternativa más adecuada.
- Cliente no elegible o con una opción de pago aplicada recientemente, al que no se le deben presentar ofertas no autorizadas.
- Cliente que rechaza la propuesta, solicita otra alternativa o incumple un acuerdo previo.
- Cliente que contacta de forma reactiva para consultar su deuda, negociar o manifestar dificultades de pago.
- Información incompleta, contradictoria o indisponibilidad de un agente o servicio.
- Solicitudes sensibles, intentos de manipulación o situaciones que requieran transferencia a un gestor humano.

Finalmente, deberá proponer, sin implementarlos, los mecanismos necesarios para operar la solución en producción.

## Objetivo

Diseñar y desarrollar una solución integral de analítica e inteligencia artificial para apoyar la gestión proactiva y reactiva de clientes en mora. La solución deberá incluir:

1. **Una solución analítica E2E**, preparada para su puesta en producción, que genere para cada obligación un indicador de propensión a la aceptación de una opción de pago en el mes siguiente y contemple las diferentes etapas del ciclo de vida de *Machine Learning* y MLOps.

2. **Un prototipo funcional de sistema agentico**, que utilice la información disponible y los resultados analíticos para determinar la siguiente mejor acción y gestionar el ofrecimiento de acuerdos u opciones de pago, según la elegibilidad del cliente y las reglas de negocio.

Ambos componentes deberán contemplar criterios de seguridad, trazabilidad, explicabilidad, evaluación, escalabilidad y operación en producción.

### Consideración importante

Tanto el rendimiento predictivo del modelo como el rendimiento del sistema agentico son relevantes, pero no constituyen por sí solos el criterio de éxito de la prueba. Se valorarán especialmente la metodología, la arquitectura y la lógica aplicadas para resolver ambos retos, así como la comprensión del problema de negocio, la integración entre los componentes, la justificación de las decisiones técnicas y la viabilidad de la solución propuesta.

La evaluación también tendrá en cuenta la calidad de las pruebas, la aplicación de prácticas de MLOps y LLMOps, la gestión de riesgos y limitaciones, la documentación, las oportunidades de mejora identificadas y la claridad de la presentación final.
