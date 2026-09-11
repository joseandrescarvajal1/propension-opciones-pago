# Operación del sistema agéntico en producción (propuesta, no implementada)

Propuesta de LLMOps para llevar el prototipo de `agente/` a producción, tal como pide el enunciado
("proponer, sin implementarlos, los mecanismos necesarios para operar la solución en producción").
Lo que ya existe en el prototipo se marca como **[hecho]**; lo demás es la propuesta.

## 1. Arquitectura de despliegue

| Componente | Prototipo | Producción |
|---|---|---|
| Canal | WhatsApp y SMS simulados en la tabla `mensajes` **[hecho]** | WhatsApp Business API (plantillas aprobadas por Meta para el proactivo; webhook de mensajes entrantes hacia `POST /chat`) y proveedor de SMS para el OTP |
| API del agente | FastAPI local (`agente/api/main.py`) **[hecho]**, `deploy/Dockerfile.agente` y `deploy/service_agente.yaml` **[hecho]** | Cloud Run por ambiente (dev, stage, prod) con el mismo CI/CD de la Parte 1: PR a `dev`, promoción a `stage` y `main`, canario 10/90 en prod |
| LLM | Gemini 2.5 Flash y Flash-Lite en Vertex AI (endpoint `global`) con ADC **[hecho]** | Igual, con la cuenta de servicio del Cloud Run (`aiplatform.user`); sin llaves de LLM; cuota reservada (Provisioned Throughput) para el volumen esperado |
| Modelo de la Parte 1 | `/explain` de la API en Cloud Run con reserva al paquete local **[hecho]** | Solo la API del ambiente correspondiente, invocada con token de identidad de la cuenta de servicio |
| Estado por hilo | SQLite (`checkpoints.db`) **[hecho]** | Checkpointer de LangGraph sobre Cloud SQL (Postgres) o Firestore; `thread_id` = cédula + canal |
| Datos del cliente | SQLite del sandbox **[hecho]** | Servicios del banco (core de cartera, motor de preaprobados, restricciones) detrás de las mismas herramientas; el agente no accede a bases directas |
| Trazas | Tabla `trazas` y MLflow **[hecho]** | BigQuery (trazas de negocio) + Cloud Logging; LangSmith o Vertex AI Agent Engine para las trazas del LLM (prompts, tokens, latencia por nodo) |
| Front de pruebas | Streamlit, en local y desplegado en Cloud Run con contraseña **[hecho]** | Consola del gestor humano (bandeja de escalamientos) integrada al CRM de cobranza, detrás del inicio de sesión corporativo (IAP o el proveedor de identidad del banco) |

## 2. Seguridad y cumplimiento

- Verificación de identidad con OTP (5 minutos, 3 intentos, 3 códigos por hora, bloqueo y escalamiento) **[hecho]**; en producción el OTP se envía por el proveedor de SMS y se valida contra el servicio de autenticación del banco. Nada se revela antes de verificar y las herramientas lo exigen aunque el LLM se confunda **[hecho]**.
- Las reglas de negocio viven en código (`evaluar_elegibilidad`) y las ofertas autorizadas son las únicas que el agente puede proponer; el guardrail de salida lo verifica **[hecho]**. En producción el motor de elegibilidad es el servicio oficial del banco y el guardrail conserva la lista de ofertas autorizadas por turno.
- Guardrail de entrada contra inyección, terceros, manipulación y casos sensibles **[hecho]**; en producción se añade el filtro de seguridad de Vertex (Safety settings) y una lista de patrones mantenida por seguridad de la información.
- Datos personales: el LLM solo ve el nombre de pila, la deuda y las ofertas del cliente verificado; no ve cédulas completas ni identificadores internos; los códigos OTP se guardan con hash y las trazas enmascaran cédula y código **[hecho]**. En producción: cifrado en reposo (CMEK), retención de conversaciones según política, y no usar datos de clientes para entrenar modelos (Vertex no entrena con los datos del cliente).
- Secretos en Secret Manager (`agente-api-key`, `propension-api-key`); el webhook de WhatsApp valida la firma de Meta.
- Escalamiento a gestor humano con resumen y prioridad **[hecho]**; en producción crea el caso en el CRM y notifica al equipo con SLA por prioridad (alta: mismo día).

## 3. Versionado y despliegue de prompts y modelos

- Prompts en archivos versionados en Git (`agente/prompts/*.md`, versión `v1`) **[hecho]**; cada cambio pasa por PR, por la suite determinista (72 pruebas) y por la suite de escenarios con LLM real (`agente/pruebas/escenarios.py`), cuyos resultados se registran en MLflow **[hecho]**.
- Cambio de LLM por configuración (`LLM_MODELO`, `LLM_MODELO_GUARDRAIL`) **[hecho]**; una nueva versión de Gemini se prueba primero en dev con la suite de escenarios y se promueve con canario.
- El modelo de propensión se cambia por `MODELO_RUTA`/versión del paquete en el bucket, sin tocar el agente **[hecho]**.

## 4. Evaluación continua y monitoreo

- Métricas por turno ya trazadas: ruta del grafo, guardrail activado, herramientas llamadas, tokens de entrada y salida, latencia por nodo **[hecho]**. En producción se agregan por día en BigQuery y se muestran en Looker Studio.
- Indicadores de negocio: tasa de verificación exitosa, acuerdos registrados por conversación, opciones aplicadas, tasa de escalamiento por motivo, cumplimiento de acuerdos a 5 días (se cruza con pagos), aceptación por acción recomendada (retroalimenta el modelo de la Parte 1).
- Indicadores de calidad y seguridad: respuestas bloqueadas por el guardrail de salida (umbral de alarma 5 %), reintentos, inyecciones detectadas, puntajes del juez LLM sobre una muestra diaria de conversaciones reales (claridad, empatía, pertinencia, concisión, umbral 4,0) **[hecho en la suite]**, revisión humana semanal de una muestra estratificada por escenario.
- Alertas: latencia p95 por turno > 25 s, tasa de error del LLM > 2 %, cuota de Vertex (429) > 1 %, caída de la API del modelo (fuente distinta de `api` > 5 %), costo diario por encima del presupuesto.
- Deriva: distribución de acciones decididas por día frente a la línea base (PSI, como en el monitoreo de la Parte 1) y cambios en la tasa de aceptación por acción.

## 5. Costos y capacidad

- Con el prototipo: 47 turnos de las pruebas consumieron en promedio unos 5.000 tokens por turno (contexto del deep agent más guardrails) y 4 a 9 s por turno. Con precios de Gemini 2.5 Flash eso equivale a fracciones de centavo de dólar por turno; una conversación típica de 5 turnos cuesta menos de 1 centavo de dólar.
- Capacidad: Cloud Run con concurrencia 20 y hasta 20 instancias atiende cientos de conversaciones simultáneas; el límite real es la cuota de Vertex, que se reserva por adelantado.
- Reducción de costo: caché de contexto de Vertex para el prompt del sistema, guardrails con Flash-Lite **[hecho]**, presupuesto de razonamiento acotado **[hecho]**.

## 6. Robustez y contingencia

- API del modelo caída: reserva al paquete local y luego a los scores del banco **[hecho]**; en producción, el paquete se descarga del bucket al arrancar y se registra la fuente en cada decisión.
- LLM caído o con cuota agotada: reintento con espera **[hecho]** y respuesta honesta que ofrece continuar más tarde o con un gestor **[hecho]**; en producción, conmutación a una región o modelo alterno por configuración.
- Mensajes vacíos, contradictorios, cédulas inexistentes, clientes sin teléfono: manejados sin LLM o con escalamiento **[hecho]**.
- Pruebas de carga antes de cada campaña proactiva (lote) y límite de envíos por hora acordado con el negocio.

## 7. Oportunidades de mejora identificadas

- Memoria de largo plazo por cliente (preferencias, horarios de contacto, motivos de rechazo) con el `store` de LangGraph.
- Negociación de valores parciales del acuerdo con reglas del negocio (hoy solo valor sugerido o mínimo).
- Evaluación con clientes simulados por un segundo LLM (conversaciones adversariales automáticas) para ampliar la cobertura de la suite.
- Recordatorio automático del acuerdo (plantilla ya definida) y seguimiento del cumplimiento.
- Ajuste del umbral de la estrategia por segmento y retroalimentación de la aceptación real al modelo de propensión.
