# Imagen de la API de propensión a opciones de pago.
# Se construye desde la raíz del repositorio:  docker build -f deploy/Dockerfile -t propension-api .
# El modelo NO va dentro de la imagen: se lee de MODELO_RUTA (carpeta montada o gs://...) al arrancar.

FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8080

# libgomp es necesaria para LightGBM
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY api/requirements.txt api/requirements.txt
RUN pip install --no-cache-dir -r api/requirements.txt

COPY src/inferencia.py src/inferencia.py
COPY api/ api/

# Usuario sin privilegios
RUN useradd --create-home --uid 1001 app && chown -R app:app /app
USER app

EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8080/health').status==200 else 1)"

CMD ["sh", "-c", "uvicorn api.main:app --host 0.0.0.0 --port ${PORT} --workers 2"]
