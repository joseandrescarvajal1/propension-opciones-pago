# Propensión a opciones de pago

Modelo que estima, con un mes de anticipación, la probabilidad de que una obligación en mora acepte una opción de pago, y su puesta en producción: API en FastAPI, contenedor, despliegue en Cloud Run y monitoreo (Parte 1). Sobre ese modelo, un sistema agéntico de cobranza por WhatsApp (Parte 2): deep agent con guardrails en LangGraph, Gemini en Vertex AI, verificación por OTP, reglas de negocio en código y un sandbox con clientes simulados. Desarrollado para la Prueba Analítica: Modelo Opciones de Pago (season 3).

## Estructura

| Carpeta | Contenido |
|---|---|
| `notebooks/` | Exploración (02), construcción del dataset (01), modelos (03 a 09), explicabilidad SHAP (10). Cada notebook registra sus experimentos en MLflow. |
| `src/presentacion/` | Genera la presentación ejecutiva: figuras desde los datos, captura de una conversación real y armado del `.pptx` con notas del orador. |
| `src/` | `download_data.py` (descarga), `features.py` (variables con corte t-1), `entrenar.py` (entrenamiento reproducible), `inferencia.py` (predicción), `monitoreo.py` y `monitoreo_mensual.py` (PSI y desempeño), `tracking.py` (MLflow), `mlflow_ui.py`. |
| `api/` | API FastAPI: `/health`, `/version`, `/predict`, `/explain` (valores SHAP por obligación). |
| `agente/` | Parte 2: `sandbox/` (base SQLite con 40 clientes simulados y WhatsApp/SMS simulados), `herramientas/` (OTP, elegibilidad, modelo, siguiente mejor acción), `grafo/` (LangGraph: guardrails, deep agent, escalamiento, proactivo), `prompts/`, `api/` (FastAPI del agente), `front/` (Streamlit), `pruebas/` (escenarios con LLM real). |
| `tests/` | 121 pruebas con pytest: 49 de la Parte 1 (variables y no fuga temporal, inferencia, API, monitoreo) y 72 de la Parte 2 sin LLM (OTP, reglas, estrategia, guardrails, herramientas, grafo, API). |
| `deploy/` | `Dockerfile`, `service.yaml` (Cloud Run), `cloudbuild.yaml`, `job_monitoreo.yaml` (job mensual); `Dockerfile.agente`, `service_agente.yaml` y `cloudbuild_agente.yaml` (API del agente); `Dockerfile.front`, `service_front.yaml` y `cloudbuild_front.yaml` (front del sandbox). |
| `.github/workflows/` | `ci.yml` (lint, pruebas, imagen) y `deploy.yml` (despliegue por rama). |
| `docs/` | `documento_tecnico.md` (entregable 1), `arquitectura.md` (diseño y operación de las dos partes, con diagramas), `operacion_agente.md` (LLMOps), `plan_mlops.md`, `plan_agentes.md`, bitácora del proyecto, texto de la competencia y diccionarios. |

Los datos (`data/`), los modelos entrenados (`models/`), las salidas (`outputs/`) y la base de MLflow no se versionan.

## Uso local

```bash
pip install -r requirements.txt
cp .env.example .env            # completar KAGGLE_API_TOKEN y API_KEY
python src/download_data.py     # datos de la competencia en data/
python src/mlflow_ui.py         # interfaz de experimentos en http://127.0.0.1:5000
```

Los notebooks se ejecutan en orden: 01 (dataset) y 02 (EDA) primero; 03 a 09 después.

### Entrenamiento reproducible y monitoreo

```bash
python src/entrenar.py --version v5              # valida en diciembre, reentrena, empaqueta models/v5 y escribe outputs/resultado_prueba.csv
python src/entrenar.py --version v5 --reconstruir  # además reconstruye el dataset desde los CSV con src/features.py
python src/monitoreo_mensual.py --mes 202401     # PSI por variable y deriva de la predicción (entrenamiento vs enero), run en MLflow
```

`src/features.py` contiene la construcción de variables con corte en t-1 (misma lógica que los notebooks 01 y 06; verificada columna a columna). La lista de variables del modelo está en `configs/variables_modelo.json`.

### API

El paquete de modelo es una carpeta con `modelo.txt` y `modelo_info.json` (umbral, variables, niveles de las categóricas, métricas). Se indica con `MODELO_RUTA`, local o `gs://bucket/modelos/v4`.

```bash
API_KEY=mi-clave MODELO_RUTA=models/v4 uvicorn api.main:app --port 8080
curl -H "X-API-Key: mi-clave" http://127.0.0.1:8080/version
```

`POST /predict` recibe `{"obligaciones": [{"ID": "...", "variables": {...}}], "umbral": null}` y devuelve probabilidad y clase por obligación. `POST /explain?k=5` recibe lo mismo y devuelve, además, las k variables que más empujan cada probabilidad (valores SHAP del modelo cargado, calculados por LightGBM sin librerías adicionales).

### Pruebas y contenedor

```bash
pytest tests -q --cov
docker build -f deploy/Dockerfile -t propension-api .
docker run -p 8080:8080 -e API_KEY=mi-clave -e MODELO_RUTA=/modelo -v $PWD/models/v4:/modelo propension-api
```

En Git Bash de Windows, anteponer `MSYS_NO_PATHCONV=1` al `docker run` para que no convierta la ruta `/modelo`.

### Sistema agéntico (Parte 2)

```bash
pip install -r agente/requirements.txt
python agente/sandbox/crear_sandbox.py --base            # 40 clientes simulados; --base genera además la copia que viaja en la imagen
uvicorn agente.api.main:app --port 8001                  # API del agente (X-API-Key = AGENTE_API_KEY)
streamlit run agente/front/app.py                        # front del sandbox en http://localhost:8501
python agente/pruebas/escenarios.py                      # escenarios con el LLM real; resultados en outputs/pruebas_agente*.csv y MLflow
```

Requiere el proyecto de GCP con Vertex AI habilitado y credenciales de aplicación (`gcloud auth application-default login`); no hay llaves de LLM. El agente llama a la API del modelo (`MODELO_API_URL`) y, si no responde, al paquete local `models/v4`. Variables en `.env.example`.

Todo el sistema agéntico está además desplegado en Cloud Run, así que la demostración no necesita nada local:

| Servicio | URL | Acceso |
|---|---|---|
| Front del sandbox (Streamlit) | `front-cobranza-demo` | público, con contraseña (`front-password` en Secret Manager) |
| API del agente | `agente-cobranza-demo` | token de identidad IAM (`run.invoker`) + `X-API-Key` |
| API del modelo | `propension-api-prod` | token de identidad IAM + `X-API-Key` |

El front obtiene el token de su cuenta de servicio (`front-cobranza-sa`) por el servidor de metadata; en local lo obtiene con `gcloud`. Para construir y desplegar:

```bash
gcloud builds submit --config deploy/cloudbuild_agente.yaml --substitutions=_ENV=demo,_SHORT_SHA=$(git rev-parse --short HEAD)
gcloud builds submit --config deploy/cloudbuild_front.yaml  --substitutions=_ENV=demo,_SHORT_SHA=$(git rev-parse --short HEAD)
```

El front local puede apuntar a cualquiera de los dos entornos con `AGENTE_API_URL`.

## Flujo de ramas y despliegue

| Rama | Pipeline | Cloud Run |
|---|---|---|
| `dev` | lint, pruebas, construcción de imagen | `propension-api-dev` (mínimo 0 instancias) |
| `stage` | lo anterior + prueba de humo | `propension-api-stage` |
| `main` | lo anterior + aprobación manual | `propension-api-prod`, tráfico gradual |

Autenticación de GitHub con GCP por Workload Identity Federation; la clave de la API vive en Secret Manager; el modelo en Cloud Storage. Detalle en `docs/plan_mlops.md`.
