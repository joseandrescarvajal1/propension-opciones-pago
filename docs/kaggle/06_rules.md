<!-- Fuente: Kaggle, competencia prueba-analitica-modelo-opciones-de-pago-season-3, pestaña 'rules'. Texto copiado tal cual. -->

# Tiempos y entregables
El propósito de la prueba es evaluar tus capacidades de análisis, diseño de soluciones de inteligencia artificial, desarrollo de modelos analíticos, prácticas de MLOps y AgentOps, arquitectura de sistemas basados en IA, experimentación, validación técnica y comunicación ejecutiva (*storytelling*).

La idea es que no dediques más de 30 horas en total al desarrollo de la prueba, incluyendo análisis, construcción de la solución, documentación y preparación de la presentación.

Es posible utilizar cualquier herramienta, framework o tecnología que consideres apropiada para resolver el problema (Python, R, Spark, SQL, plataformas cloud, frameworks de IA Generativa, herramientas de automatización y orquestación como n8n, LangGraph, CrewAI, Semantic Kernel, AutoGen, entre otras). Asimismo, podrás consultar documentación, referencias técnicas y recursos disponibles en internet.

No está permitido recibir asesoría directa de otras personas para resolver la prueba.

Puedes realizar los supuestos que consideres necesarios. La duplicidad, inconsistencia o falta de completitud en los datos es parte del problema a resolver.

No es obligatorio utilizar la totalidad de los datos o variables suministradas. La selección de información deberá estar soportada por tu metodología y objetivos de la solución.

No existe una única solución correcta. Inclusive, puede darse el caso de que concluyas que no es posible obtener un modelo predictivo o una solución agentica suficientemente robusta con la información suministrada. En dichos casos, se valorará especialmente la argumentación técnica y la metodología utilizada para llegar a dicha conclusión.

### Uso de Inteligencia Artificial Generativa

Se permite el uso de herramientas de Inteligencia Artificial Generativa como apoyo en cualquiera de las fases de la prueba.

Sin embargo, el candidato deberá declarar explícitamente cómo utilizó dichas herramientas durante el desarrollo, indicando para qué actividades fueron empleadas (generación de código, diseño arquitectónico, documentación, pruebas, ideación, análisis, entre otras) y qué decisiones técnicas fueron tomadas directamente por el candidato. La transparencia en el uso de estas herramientas hará parte de la evaluación.

## Entregables

### 1. Documento técnico

Documento donde expliques el proceso seguido para resolver la prueba.

El documento deberá incluir las etapas relevantes de la solución analítica y de la solución multiagente, así como los principales hallazgos, decisiones, supuestos, riesgos y conclusiones.

La extensión máxima será de ** 4 Mil caracteres**, excluyendo anexos, imagenes o tablas .

De manera opcional, podrás indicar cuáles datos o atributos adicionales incorporarías para mejorar significativamente la solución propuesta, considerando su viabilidad y costo de obtención.

### 2. Presentación ejecutiva

Presentación de máximo **15 minutos** donde expongas la solución integral propuesta. inclya de esos 15 minutos 5 minutos en qué presentaría y cómo lo presentaría los resultados (en 5 min) ante un equipo directivo sin conocimiento técnico que tuviera que aprobar el uso del modelo

El material de presentación no es necesario entregarlo junto con la prueba. Será utilizado durante la sesión de sustentación (Si accedes a esta fase de selección).

### 3. Archivo de resultados del modelo

Archivo `resultado_prueba.csv` (codificación UTF-8 y delimitado por comas) que contenga cada combinación cliente-obligación entregada en el archivo de calificación, agregando:

- `var_rpta_alt`
- `Prob_uno`

Formato esperado:

ID,var_rpta_alt,Prob_uno

250631#175418#912682,1,0.78234

217161#1054045#26297,0,0.23123

443187#754930#325412,1,0.89232

224370#328405#754753,0,0.42312

Donde la columna `ID` corresponde a la concatenación de:

`nit_enmascarado#num_oblig_orig_enmascarado#num_oblig_enmascarado`

### 4. Código y repositorio

Se deberán entregar los artefactos necesarios para reproducir la solución propuesta.

Idealmente se espera un repositorio Git (GitHub, GitLab, Azure DevOps o equivalente):

En caso de utilizar plataformas visuales, frameworks de agentes o herramientas de automatización (por ejemplo n8n, LangGraph, CrewAI, Semantic Kernel u otras), se deberán incluir diagramas, configuraciones o exportables que permitan comprender y reproducir la solución.

### 5. Diseño de arquitectura y operación de la solución

Se deberá presentar una propuesta arquitectónica de alto nivel que describa cómo operaría la solución en un entorno productivo para su despliegue y mantenimiento.

Se espera que esta propuesta describa el ciclo completo.

## Nota Importante

Los documentos, archivos y evidencias generados deberán ser enviados al correo desde el cual fue remitida esta prueba, antes de la fecha límite indicada en la comunicación recibida.
