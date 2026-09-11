# Plan de MLOps (acordado 2026-09-11)

## Arquitectura objetivo

```
GitHub (dev -> stage -> main)
   | GitHub Actions: pruebas -> imagen -> despliegue por rama
   v
Artifact Registry (imagen etiquetada por commit)
   |
   v
Cloud Run  api-dev / api-stage / api-prod        <- Secret Manager (clave API)
   | carga al arrancar                            <- cuenta de servicio minima
   v
Cloud Storage  gs://<bucket>/modelos/<version>/   modelo + umbral + variables
   ^
   | registro y promocion
MLflow (experimentos, versiones, runs de monitoreo)

Batch mensual: tablas historicas -> src/features.py (corte t-1) -> prediccion -> BigQuery
Monitoreo mensual: PSI de variables y de prediccion; F1 real cuando llega la etiqueta
```

## Estructura del repositorio

```
api/            main.py (FastAPI), esquemas Pydantic, seguridad
src/            features.py, inferencia.py, monitoreo.py, tracking.py, download_data.py
tests/          test_features.py, test_inferencia.py, test_api.py, test_monitoreo.py
deploy/         Dockerfile, service.yaml (Cloud Run), cloudbuild.yaml
.github/workflows/  ci.yml, deploy.yml
notebooks/      00 a 09 (experimentacion)
docs/           bitacora, arquitectura, diccionarios, plan
models/, outputs/, data/, mlruns/, mlflow.db   (excluidos de git)
```

## Los ocho puntos

1. **Codigo reutilizable en src/**: `features.py` (variables de los notebooks 01, 06 y 09 con corte en t-1, mismo codigo en entrenamiento e inferencia batch) e `inferencia.py` (carga modelo + umbral + variables desde ruta local o Cloud Storage, valida columnas, predice).
2. **Modelo en Cloud Storage, registro en MLflow**: `gs://<bucket>/modelos/vN/` con modelo, `modelo_info.json` y metadata. Cloud Run lee la version indicada por variable de entorno y la mantiene en memoria. El modelo nunca va dentro de la imagen.
3. **API FastAPI**: `GET /health`, `GET /version`, `POST /predict` (una o varias obligaciones). Pydantic valida nombres y tipos (422 si faltan o sobran). Salida: ID, probabilidad, clase, version. Recibe variables ya calculadas; el calculo t-1 es batch mensual.
4. **Pruebas unitarias (pytest)**: variables (incluida no fuga temporal), inferencia (carga, rango, determinismo, rechazo), API (endpoints, lote, 422, 401), monitoreo (PSI cero, alarma, sin infinitos). Datos sinteticos; cobertura minima 80 % en src/ y api/; bloquean el pipeline si fallan.
5. **Docker y Cloud Run**: imagen ligera (Python, LightGBM, FastAPI, Uvicorn). `service.yaml`: 1 a 10 instancias, concurrencia 80, 2 CPU / 2 GB, timeout 60 s.
6. **Seguridad y secretos**: servicio sin acceso publico (token de identidad de Google); clave de API por cabecera guardada en Secret Manager y montada como variable de entorno; cuenta de servicio con permisos minimos (bucket + secretos). En local, `.env`. Nada en el repositorio ni en la imagen.
7. **CI/CD en GitHub, tres ramas**:
   - `dev`: lint, pruebas, construccion de imagen -> Cloud Run `api-dev` (min 0).
   - `stage`: lo anterior + prueba de humo contra la API desplegada -> `api-stage`.
   - `main`: lo anterior + aprobacion manual (GitHub environment) -> `api-prod` con trafico 10 % y luego 100 %.
   Una imagen por commit (etiqueta = hash); stage y main despliegan la misma imagen probada. Workload Identity Federation (sin llaves JSON). `main` protegida: solo por pull request desde `stage`.
8. **Monitoreo**: `monitoreo.py` con PSI por variable (0.1 aviso, 0.25 alarma) sobre las 20 mas importantes del 08; PSI de la distribucion de probabilidades y % de unos vs esperado; F1/precision/recall reales al llegar la etiqueta; reentreno si F1 cae bajo umbral dos meses seguidos. Cada corrida es un run en MLflow; en GCP, job de Cloud Run + Cloud Scheduler -> BigQuery -> Cloud Monitoring. Demostracion con diciembre vs enero.

## Que se implementa y que se documenta

Implementado y probado en local: 1, 3, 4, 5, 8 y los YAML de 6 y 7. Despliegue real en GCP solo si hay proyecto con facturacion; si no, configuracion lista y documentada.

## Entregable 5 de la prueba

Documento de arquitectura con el ciclo completo (datos, variables batch, entrenamiento, registro, promocion por ramas, despliegue, inferencia, monitoreo, reentreno), justificacion de cada eleccion y evoluciones no implementadas (Vertex AI Model Registry, tres proyectos de GCP, feature store).

## Pendiente del usuario

Repositorio en GitHub con ramas `dev`, `stage`, `main`; confirmar proyecto de GCP con facturacion.
