# Propensión a opciones de pago

Modelo que estima, con un mes de anticipación, la probabilidad de que una obligación en mora acepte una opción de pago, y su puesta en producción: API en FastAPI, contenedor, despliegue en Cloud Run y monitoreo. Desarrollado para la Prueba Analítica: Modelo Opciones de Pago (season 3).

## Estructura

| Carpeta | Contenido |
|---|---|
| `notebooks/` | Exploración (02), construcción del dataset (01), modelos (03 a 09), explicabilidad SHAP (10). Cada notebook registra sus experimentos en MLflow. |
| `src/` | `download_data.py` (descarga), `features.py` (variables con corte t-1), `entrenar.py` (entrenamiento reproducible), `inferencia.py` (predicción), `monitoreo.py` y `monitoreo_mensual.py` (PSI y desempeño), `tracking.py` (MLflow), `mlflow_ui.py`. |
| `api/` | API FastAPI: `/health`, `/version`, `/predict`, `/explain` (valores SHAP por obligación). |
| `tests/` | 49 pruebas unitarias con pytest (variables y no fuga temporal, inferencia, API, monitoreo). |
| `deploy/` | `Dockerfile`, `service.yaml` (Cloud Run), `cloudbuild.yaml`, `job_monitoreo.yaml` (job mensual). |
| `.github/workflows/` | `ci.yml` (lint, pruebas, imagen) y `deploy.yml` (despliegue por rama). |
| `docs/` | Bitácora del proyecto, texto de la competencia, diccionarios, plan de MLOps. |

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

## Flujo de ramas y despliegue

| Rama | Pipeline | Cloud Run |
|---|---|---|
| `dev` | lint, pruebas, construcción de imagen | `propension-api-dev` (mínimo 0 instancias) |
| `stage` | lo anterior + prueba de humo | `propension-api-stage` |
| `main` | lo anterior + aprobación manual | `propension-api-prod`, tráfico gradual |

Autenticación de GitHub con GCP por Workload Identity Federation; la clave de la API vive en Secret Manager; el modelo en Cloud Storage. Detalle en `docs/plan_mlops.md`.
