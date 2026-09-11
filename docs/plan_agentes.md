# Plan de la Parte 2: sistema agéntico (50 % de la nota)

Aprobado por el candidato el 2026-09-11. Arquitectura definida por el candidato:
Deep Agents (LangChain) sobre Vertex AI (Gemini), sandbox con clientes simulados
(WhatsApp simulado + base de datos), verificación de identidad con OTP, guardrails como
nodos del grafo, API del agente en FastAPI con `thread_id` = cédula, y un front para
probar el modo reactivo y el proactivo.

## Etapa 1. Preparación
- Vertex AI habilitado en `propension-opciones-pago`; modelo Gemini 2.5 Flash (cambiable
  por configuración). Autenticación con la cuenta de servicio o ADC; sin llaves de LLM.
- Librerías: `deepagents`, `langchain-google-vertexai`, `langgraph`,
  `langgraph-checkpoint-sqlite`, `streamlit`.
- Variables en `.env`: `GCP_PROJECT_ID`, `GCP_REGION`, `LLM_MODELO`, `MODELO_API_URL`,
  `MODELO_API_KEY`, `AGENTE_API_KEY`.
- Estructura: `agente/sandbox`, `agente/herramientas`, `agente/grafo`, `agente/prompts`,
  `agente/api`, `agente/front`, `tests/agente`.

## Etapa 2. Sandbox: base de datos y WhatsApp simulado
- SQLite con tablas: clientes, obligaciones (con las 100 variables del modelo tomadas de
  obligaciones reales de enero 2024, enmascaradas), opciones_preaprobadas (máximo 3 por
  obligación), opciones_aplicadas (histórico para la espera de 3 a 4 meses), acuerdos,
  restricciones, otp, mensajes, trazas.
- `crear_sandbox.py` genera 40 clientes que cubren los siete escenarios; `perfiles.json`
  indica el escenario de cada uno. Sin datos personales reales.
- WhatsApp simulado: `enviar_plantilla`, `enviar_mensaje`, `bandeja` sobre la tabla
  mensajes.

## Etapa 3. Herramientas deterministas
`buscar_cliente`, `enviar_otp`, `validar_otp` (3 intentos, 5 minutos, bloqueo),
`consultar_deuda`, `evaluar_elegibilidad` (reglas de negocio en código, con la regla que
permite o impide cada oferta), `predecir_propension` (/predict y /explain de Cloud Run con
reserva al modelo local), `siguiente_mejor_accion`, `registrar_acuerdo`,
`registrar_opcion`, `escalar_a_humano`, `registrar_traza`. Pruebas unitarias.

## Etapa 4. Grafo con el deep agent y los guardrails
Estado compartido (hilo, cédula, verificado, cliente, acción, ofertas autorizadas,
escalamiento). Nodos: `guardrail_entrada`, `agente` (deep agent con subagentes de
negociación y de consulta), `guardrail_salida`, `escalamiento`. Checkpointer SQLite.
Prompts versionados en `agente/prompts/`.

## Etapa 5. API del agente (FastAPI)
`POST /chat`, `POST /proactivo`, `POST /proactivo/lote`, `GET /conversaciones/{id}`,
`GET /trazas/{id}`, `GET /sandbox/otp/{cedula}` (solo sandbox), `/health`. `X-API-Key`.
Dockerfile y `service.yaml` para Cloud Run.

## Etapa 6. Front (Streamlit)
Chat tipo WhatsApp (reactivo), gestión proactiva por cliente o lote, ficha del cliente con
el "teléfono" donde llega el OTP, visor de trazas y guardrails.

## Etapa 7. Pruebas por escenario
Unitarias (herramientas y reglas); funcionales e integración (siete escenarios guionados
contra el grafo real, aserciones deterministas + LLM juez con umbral); seguridad y
robustez (inyección, cédula ajena, OTP vencido, bloqueo, API caída, mensajes vacíos o
contradictorios). Informe `outputs/pruebas_agente.csv` y registro en MLflow.

## Etapa 8. LLMOps y documentación
Tokens, latencia y costo por turno en trazas y MLflow. `docs/operacion_agente.md` con la
propuesta de operación en producción (sin implementar). Bitácora, README y diagrama.

Estimado: 16 horas.
