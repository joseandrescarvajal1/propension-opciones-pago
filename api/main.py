"""API de propensión a aceptar una opción de pago.

Endpoints:
    GET  /health    -> estado del servicio (sin autenticación, lo usa Cloud Run)
    GET  /version   -> versión del modelo, umbral y número de variables
    POST /predict   -> probabilidad y clase para una o varias obligaciones

Seguridad: cabecera X-API-Key comparada con la variable de entorno API_KEY
(en Cloud Run viene de Secret Manager; en local del archivo .env).

Configuración por variables de entorno:
    MODELO_RUTA   carpeta local o gs://bucket/ruta con modelo.txt y modelo_info.json (por defecto models/v4)
    API_KEY       clave requerida en X-API-Key (obligatoria; si falta, /predict responde 503)
    MAX_FILAS     máximo de obligaciones por petición (por defecto 1000)
"""

from __future__ import annotations

import hmac
import os
import sys
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import pandas as pd
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException, Request
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
load_dotenv(ROOT / ".env")

from inferencia import EntradaInvalida, Modelo

MAX_FILAS = int(os.environ.get("MAX_FILAS", "1000"))

@asynccontextmanager
async def ciclo_de_vida(app: FastAPI):
    """Carga el modelo una sola vez al arrancar y lo mantiene en memoria."""
    app.state.modelo = Modelo.cargar()
    yield


app = FastAPI(
    title="Propensión a opciones de pago",
    description="Probabilidad de que una obligación en mora acepte una opción de pago en el mes siguiente.",
    version="1.0.0",
    lifespan=ciclo_de_vida,
)


# ------------------------------------------------------------------ modelo
def obtener_modelo() -> Modelo:
    if not hasattr(app.state, "modelo"):
        app.state.modelo = Modelo.cargar()
    return app.state.modelo


# --------------------------------------------------------------- seguridad
def verificar_api_key(x_api_key: str | None = Header(default=None, alias="X-API-Key")) -> None:
    esperada = os.environ.get("API_KEY")
    if not esperada:
        raise HTTPException(status_code=503, detail="API_KEY no configurada en el servidor")
    if x_api_key is None or not hmac.compare_digest(x_api_key, esperada):
        raise HTTPException(status_code=401, detail="clave de API inválida o ausente")


# ---------------------------------------------------------------- esquemas
class Obligacion(BaseModel):
    ID: str = Field(..., description="nit#num_oblig_orig#num_oblig", examples=["243031#516680#563662"])
    variables: dict[str, Any] = Field(..., description="Las variables del modelo con corte en t-1; nulos permitidos")


class PeticionPrediccion(BaseModel):
    obligaciones: list[Obligacion] = Field(..., min_length=1)
    umbral: float | None = Field(default=None, ge=0.0, le=1.0, description="Umbral opcional; por defecto el del modelo")


class Prediccion(BaseModel):
    ID: str
    prob_uno: float
    var_rpta_alt: int


class RespuestaPrediccion(BaseModel):
    version_modelo: str
    umbral: float
    n: int
    ms: float
    predicciones: list[Prediccion]


# --------------------------------------------------------------- endpoints
@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/version", dependencies=[Depends(verificar_api_key)])
def version(modelo: Modelo = Depends(obtener_modelo)) -> dict[str, Any]:
    return {"version_modelo": modelo.version, "umbral": modelo.umbral, "n_features": len(modelo.features),
            "ruta": modelo.ruta, "metricas": modelo.info.get("metricas", {})}


@app.post("/predict", response_model=RespuestaPrediccion, dependencies=[Depends(verificar_api_key)])
def predict(peticion: PeticionPrediccion, modelo: Modelo = Depends(obtener_modelo)) -> RespuestaPrediccion:
    if len(peticion.obligaciones) > MAX_FILAS:
        raise HTTPException(status_code=413, detail=f"máximo {MAX_FILAS} obligaciones por petición")
    t0 = time.perf_counter()
    df = pd.DataFrame([o.variables for o in peticion.obligaciones])
    try:
        res = modelo.predecir(df.reindex(columns=modelo.features) if set(modelo.features) <= set(df.columns) else df, umbral=peticion.umbral)
    except EntradaInvalida as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    preds = [Prediccion(ID=o.ID, prob_uno=round(float(p), 6), var_rpta_alt=int(c)) for o, p, c in zip(peticion.obligaciones, res.prob_uno, res.var_rpta_alt)]
    return RespuestaPrediccion(version_modelo=modelo.version, umbral=modelo.umbral if peticion.umbral is None else peticion.umbral,
                               n=len(preds), ms=round((time.perf_counter() - t0) * 1000, 1), predicciones=preds)


class Factor(BaseModel):
    variable: str
    valor: Any
    contribucion: float
    sentido: str


class Explicacion(BaseModel):
    ID: str
    prob_uno: float
    var_rpta_alt: int
    base: float
    factores: list[Factor]


class RespuestaExplicacion(BaseModel):
    version_modelo: str
    umbral: float
    n: int
    k: int
    explicaciones: list[Explicacion]


@app.post("/explain", response_model=RespuestaExplicacion, dependencies=[Depends(verificar_api_key)])
def explain(peticion: PeticionPrediccion, k: int = 5, modelo: Modelo = Depends(obtener_modelo)) -> RespuestaExplicacion:
    """Probabilidad y las k variables que más la empujan (valores SHAP del modelo cargado, escala logit)."""
    if len(peticion.obligaciones) > MAX_FILAS:
        raise HTTPException(status_code=413, detail=f"máximo {MAX_FILAS} obligaciones por petición")
    k = max(1, min(int(k), len(modelo.features)))
    umbral = modelo.umbral if peticion.umbral is None else peticion.umbral
    df = pd.DataFrame([o.variables for o in peticion.obligaciones])
    try:
        exp = modelo.explicar(df.reindex(columns=modelo.features) if set(modelo.features) <= set(df.columns) else df, k=k)
    except EntradaInvalida as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    return RespuestaExplicacion(version_modelo=modelo.version, umbral=umbral, n=len(exp), k=k,
                                explicaciones=[Explicacion(ID=o.ID, prob_uno=e["prob_uno"], var_rpta_alt=int(e["prob_uno"] >= umbral), base=e["base"], factores=e["factores"]) for o, e in zip(peticion.obligaciones, exp)])


@app.middleware("http")
async def cabeceras_seguridad(request: Request, call_next):
    respuesta = await call_next(request)
    respuesta.headers["X-Content-Type-Options"] = "nosniff"
    respuesta.headers["Cache-Control"] = "no-store"
    return respuesta
