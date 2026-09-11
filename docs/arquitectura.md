# Diseño de arquitectura y operación de la solución

Entregable 5 de la prueba. Describe cómo opera hoy la solución construida y cómo operaría en el
entorno productivo del banco, para las dos partes: el modelo de propensión y el sistema agéntico.

Lo construido y desplegado se marca **[implementado]**; lo demás es la propuesta de evolución.

---

## 1. Vista general

```mermaid
flowchart LR
    subgraph Datos["Fuentes de datos"]
        D1[(trtest<br/>gestiones y respuesta)]
        D2[(probabilidades<br/>scores del banco)]
        D3[(cuotas y pagos)]
        D4[(master customer)]
    end

    subgraph P1["Parte 1 · Solución analítica"]
        F[features.py<br/>corte t-1, sin fuga] --> E[entrenar.py<br/>validación temporal]
        E --> M[(Paquete del modelo<br/>Cloud Storage)]
        E -.registra.-> ML[(MLflow)]
        M --> API[API de propensión<br/>Cloud Run]
        API -.PSI mensual.-> MON[Job de monitoreo]
        MON -.si F1 cae.-> E
    end

    subgraph P2["Parte 2 · Sistema agéntico"]
        CH[Canal<br/>WhatsApp] --> AG[API del agente<br/>Cloud Run]
        AG --> GR[Grafo LangGraph<br/>guardrails + deep agent]
        GR --> LLM[Vertex AI<br/>Gemini]
        GR --> NEG[(Sistemas de negocio<br/>cartera, preaprobados,<br/>restricciones)]
        GR --> HUM[Gestor humano]
    end

    D1 & D2 & D3 & D4 --> F
    GR -->|propensión y factores| API
    GR -.trazas.-> TR[(Trazabilidad<br/>BigQuery)]
```

La integración entre las dos partes es un único punto: el agente consume el endpoint `/explain`
de la API del modelo y recibe la probabilidad más los factores que la explican. No comparte base
de datos ni código de modelado, así que cada parte se despliega y versiona por separado.

---

## 2. Parte 1: ciclo de vida del modelo

```mermaid
flowchart TD
    A[CSV crudos<br/>5 fuentes] --> B[Construcción de variables<br/>src/features.py]
    B --> C{Corte temporal t-1<br/>ninguna variable del mes t}
    C --> D[156 variables<br/>133 base + 23 construidas]
    D --> S[Selección<br/>criterio, varianza, Spearman]
    S --> T[100 variables<br/>configs/variables_modelo.json]
    T --> V[Validación temporal<br/>entrena ≤ nov, mide dic]
    V --> U[Umbral que maximiza F1<br/>0,33]
    U --> R[Reentrena con los 5 meses]
    R --> P[Paquete versionado<br/>modelo.txt + modelo_info.json<br/>+ importancia SHAP]
    P --> G[(Cloud Storage<br/>gs://…/modelos/v4)]
    P --> K[resultado_prueba.csv]
    R -.experimentos.-> MLF[(MLflow)]
```

**Decisiones que definen la arquitectura** [implementado]

| Decisión | Motivo |
|---|---|
| Corte estricto en t-1 | El modelo predice el mes siguiente; usar el mes en curso es fuga y en producción esos datos no existen |
| Validación temporal, no aleatoria | Una obligación aparece en varios meses; la partición aleatoria inflaba el F1 en 0,06 |
| Umbral guardado en el paquete | La clase 0/1 es una decisión de negocio, no una salida del modelo; se ajusta sin reentrenar |
| Paquete autocontenido en el bucket | Cambiar de modelo es cambiar una variable de entorno; la imagen no se reconstruye |
| Un solo script de entrenamiento | `python src/entrenar.py --version vN` reproduce todo de punta a punta |

**Operación** [implementado]: API en Cloud Run con tres ambientes, autenticación por IAM más clave
de API, secretos en Secret Manager, despliegue continuo desde GitHub con Workload Identity
Federation y canario del 10 % en producción. Job mensual de monitoreo que calcula el índice de
estabilidad poblacional por variable, el desplazamiento de las predicciones y el desempeño real,
con umbrales de 0,10 para aviso y 0,25 para alarma, y regla de reentrenamiento si el F1 cae por
debajo de 0,68 dos meses seguidos.

**Evolución propuesta**: reentrenamiento programado mensual con aprobación humana, registro de
modelos en Vertex AI Model Registry, y realimentación de la aceptación real observada en las
conversaciones del agente como nueva fuente de etiquetas.

---

## 3. Parte 2: arquitectura del sistema agéntico

```mermaid
flowchart TD
    IN([Mensaje del cliente]) --> GE[guardrail_entrada<br/>reglas + clasificador]
    GE -->|normal o sensible| AGT[deep agent<br/>Gemini 2.5 Flash]
    GE -->|inyección, tercero,<br/>fuera de alcance| FIJO[respuesta fija]
    GE -->|hilo bloqueado| ESC[escalamiento]
    AGT --> GS[guardrail_salida<br/>reglas + juez]
    GS -->|cumple| OUT([Respuesta al cliente])
    GS -->|primera falla| AGT
    GS -->|segunda falla| ESC
    ESC --> OUT
    FIJO --> OUT

    AGT -.herramientas.-> H[identidad OTP · consultar deuda ·<br/>elegibilidad · modelo · registrar ·<br/>escalar · notas]
    AGT -.subagente.-> SUB[analista de cartera]
```

### Responsabilidad de cada componente

| Componente | Responsabilidad | Por qué está separado |
|---|---|---|
| Guardrail de entrada | Clasifica el mensaje: normal, inyección, tercero, sensible, manipulación, fuera de alcance | Los ataques se detienen antes de gastar tokens y antes de que el modelo de lenguaje los lea |
| Deep agent | Conduce la conversación, decide qué herramienta usar y redacta | Es lo único que necesita lenguaje natural |
| Subagente analista | Resume la situación de cartera en formato estructurado | Aísla el análisis técnico del tono comercial |
| Herramientas | Identidad, elegibilidad, modelo, registro, escalamiento | **Aquí viven las reglas de negocio, en código determinista** |
| Guardrail de salida | Verifica ofertas autorizadas, promesas prohibidas, fugas de datos | Última barrera antes de que el cliente lea algo |
| Escalamiento | Crea el caso con resumen y prioridad | Cierra el circuito con el humano |

### El principio de diseño central

El modelo de lenguaje **nunca decide qué se puede ofrecer**. La herramienta `evaluar_elegibilidad`
aplica las reglas en código y devuelve la lista cerrada de ofertas autorizadas; el agente solo
puede proponer lo que está en esa lista, y el guardrail de salida lo verifica. Si el modelo
alucina una oferta, la respuesta se bloquea.

Las reglas implementadas, derivadas del enunciado: máximo tres opciones preaprobadas por
obligación al mes; espera de tres a cuatro meses tras aplicar una opción; sin ofertas cuando hay
restricción activa; acuerdo de pago a cinco días solo si no hay opción en espera, acuerdo vigente
ni incumplimiento reciente; una opción aplicada por obligación al mes.

### Siguiente mejor acción

```mermaid
flowchart TD
    S{¿Restricción activa?} -->|sí| GH[GESTOR_HUMANO]
    S -->|no| E{¿Opción en periodo<br/>de espera?}
    E -->|sí| SO[SIN_OFERTA]
    E -->|no| T{¿Mora ≤ 30 días<br/>y acuerdo elegible?}
    T -->|sí| AC[ACUERDO_PAGO]
    T -->|no| O{¿Hay opciones<br/>elegibles?}
    O -->|sí| PR{¿Propensión ≥ umbral?}
    PR -->|sí| OF[OFRECER_OPCION]
    PR -->|no| AC2{¿Acuerdo elegible?}
    AC2 -->|sí| AC
    AC2 -->|no| OF
    O -->|no| AC3{¿Acuerdo elegible?}
    AC3 -->|sí| AC
    AC3 -->|no| GH
```

Medido sobre los 40 clientes simulados, la probabilidad del modelo cambia la acción elegida en el
35 % de los casos. En el resto mandan las reglas, que es el comportamiento deseado.

---

## 4. Vista de despliegue

```mermaid
flowchart LR
    subgraph GH["GitHub"]
        DEV[dev] --> STG[stage] --> MAIN[main]
    end
    subgraph GCP["Google Cloud · propension-opciones-pago"]
        subgraph CR["Cloud Run"]
            F[front-cobranza<br/>Streamlit]
            A[agente-cobranza<br/>FastAPI]
            AP[propension-api<br/>dev · stage · prod]
        end
        VX[Vertex AI<br/>Gemini]
        SM[(Secret Manager)]
        GS[(Cloud Storage<br/>paquetes del modelo)]
        AR[(Artifact Registry)]
    end
    DEV & STG & MAIN -->|Cloud Build| AR
    AR --> CR
    F -->|token IAM + clave| A
    A -->|token IAM + clave| AP
    A --> VX
    AP --> GS
    A & AP & F --> SM
```

**Autenticación en cadena** [implementado]: cada servicio tiene su cuenta de servicio y llama al
siguiente con un token de identidad de Google más una clave de API. Ningún servicio es público
salvo el front, que además exige contraseña. No hay llaves de modelos de lenguaje en ninguna
parte: Vertex AI autentica con la cuenta de servicio del contenedor.

**Compuertas de despliegue** [implementado]: pull request con lint, 126 pruebas y construcción de
imagen; `stage` añade prueba de humo; `main` exige aprobación manual y despliega con canario.
Los cambios que solo tocan el agente o su front no redespliegan la API del modelo.

**Entornos**

| Ambiente | API del modelo | Instancias mínimas | Disparo |
|---|---|---|---|
| dev | `propension-api-dev` | 0 | automático al mergear a `dev` |
| stage | `propension-api-stage` | 1 | automático, con prueba de humo |
| prod | `propension-api-prod` | 1 | aprobación manual, canario 10 % |

---

## 5. De prototipo a producción

Lo que cambia al salir del sandbox, sin tocar la lógica del agente:

| Componente | Hoy | En producción |
|---|---|---|
| Canal | WhatsApp y SMS simulados en base de datos | WhatsApp Business API con plantillas aprobadas; proveedor de SMS para el OTP |
| Datos del cliente | SQLite con 40 clientes simulados | Servicios del banco detrás de las mismas herramientas |
| Estado de la conversación | SQLite en la instancia | Cloud SQL o Firestore, compartido entre instancias |
| Identidad | OTP propio | Servicio de autenticación del banco |
| Trazabilidad | Tabla local y MLflow | BigQuery más LangSmith o Agent Engine |
| Front | Streamlit con contraseña | Consola del gestor en el CRM, tras el inicio de sesión corporativo |

Las herramientas son la frontera: cambian por dentro, su contrato no. Por eso el grafo, los
prompts y los guardrails pasan a producción sin modificarse.

El detalle de monitoreo, evaluación continua, versionado de prompts, costos y contingencia está
en [operacion_agente.md](operacion_agente.md).

---

## 6. Riesgos y cómo se mitigan

| Riesgo | Mitigación | Estado |
|---|---|---|
| El modelo de lenguaje ofrece algo no autorizado | Reglas en código, lista cerrada de ofertas, guardrail de salida, reintento y bloqueo | [implementado] |
| Inyección de instrucciones o suplantación | Guardrail de entrada antes del modelo, verificación por OTP, aislamiento por hilo | [implementado] |
| Fuga de datos antes de verificar identidad | Las herramientas de cartera exigen verificación; el guardrail revisa la respuesta | [implementado] |
| El modelo de propensión no responde | Respaldo al paquete local y luego a los scores del banco, registrando la fuente | [implementado] |
| Cuota de Vertex agotada | Reintento con espera y respuesta honesta | [implementado]; cuota reservada, pendiente |
| Deriva de los datos | Índice de estabilidad poblacional mensual y regla de reentrenamiento | [implementado] |
| Ambigüedad de la etiqueta | Documentada: el 49 % de los ceros son casos sin oferta registrada, techo del F1 | analizado |
| Estado en una sola instancia | Aceptado para la demostración | Cloud SQL en producción |

---

## 7. Qué datos adicionales mejorarían la solución

En orden de impacto esperado frente a costo de obtención:

1. **La oferta real por obligación y mes.** Hoy no se distingue "no aceptó" de "no se le ofreció";
   el 49 % de los ceros son ambiguos. Es el techo del F1 y el dato ya existe en los sistemas de
   gestión.
2. **El canal y el momento del contacto.** Permite aprender cuándo y por dónde contactar, no solo
   a quién.
3. **El resultado del acuerdo a cinco días.** Cierra el circuito entre lo que el agente promete y
   lo que el cliente cumple, y convierte la conversación en etiqueta.
4. **Ingresos actualizados o información de otras entidades.** Mejora la capacidad de pago
   estimada; costo alto y sujeto a autorización del cliente.
