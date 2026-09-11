"""Integración con el modelo de la Parte 1.

Llama a la API desplegada (/explain devuelve probabilidad y factores SHAP). Si la API no responde,
usa el paquete local models/v4 con la misma clase Modelo. Si tampoco está disponible, lo informa y la
estrategia decide sin el modelo (con los scores del banco como respaldo).

Variables de entorno:
    MODELO_API_URL   URL de la API (Cloud Run o local). Vacía = solo local.
    MODELO_API_KEY   clave X-API-Key (si falta, usa API_KEY).
    MODELO_MODO      api (por defecto: API con reserva local) | local | caido (simula indisponibilidad, para pruebas)
"""

from __future__ import annotations

import json
import os
import sqlite3
import sys
import time
from pathlib import Path

import httpx
from herramientas.glosario import describir
from sandbox.db import fila

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

_modelo_local = None


def _local():
    global _modelo_local
    if _modelo_local is None:
        from inferencia import Modelo
        _modelo_local = Modelo.cargar(os.environ.get("MODELO_RUTA") or ROOT / "models" / "v4")
    return _modelo_local


def _por_api(id_obligacion: str, variables: dict, k: int) -> dict:
    url = (os.environ.get("MODELO_API_URL") or "").rstrip("/")
    if not url:
        raise RuntimeError("MODELO_API_URL no configurada")
    cab = {"X-API-Key": os.environ.get("MODELO_API_KEY") or os.environ.get("API_KEY", "")}
    tok = os.environ.get("MODELO_API_ID_TOKEN")  # Cloud Run con IAM: token de identidad
    if tok:
        cab["Authorization"] = f"Bearer {tok}"
    r = httpx.post(f"{url}/explain", params={"k": k}, json={"obligaciones": [{"ID": id_obligacion, "variables": variables}]}, headers=cab, timeout=8.0)
    r.raise_for_status()
    d = r.json()
    e = d["explicaciones"][0]
    return {"prob_uno": e["prob_uno"], "var_rpta_alt": e["var_rpta_alt"], "umbral": d["umbral"], "factores": e["factores"], "version_modelo": d["version_modelo"], "fuente": "api"}


def _por_local(id_obligacion: str, variables: dict, k: int) -> dict:
    import pandas as pd
    m = _local()
    e = m.explicar(pd.DataFrame([variables]).reindex(columns=m.features), k=k)[0]
    return {"prob_uno": e["prob_uno"], "var_rpta_alt": int(e["prob_uno"] >= m.umbral), "umbral": m.umbral, "factores": e["factores"], "version_modelo": m.version, "fuente": "local"}


def predecir_propension(con: sqlite3.Connection, id_obligacion: str, k: int = 5) -> dict:
    """Probabilidad de aceptar una opción de pago el mes siguiente y los k factores que más pesan, en lenguaje de negocio."""
    o = fila(con, "SELECT variables_modelo FROM obligaciones WHERE id_obligacion = ?", (id_obligacion,))
    if not o:
        return {"disponible": False, "motivo": "obligación no encontrada"}
    variables = json.loads(o["variables_modelo"])
    faltantes = sum(v is None for v in variables.values())
    modo = os.environ.get("MODELO_MODO", "api")
    t0 = time.perf_counter()
    errores = []
    res = None
    if modo == "caido":
        errores.append("servicio del modelo indisponible (simulado)")
    else:
        intentos = [_por_api, _por_local] if modo == "api" else [_por_local]
        for f in intentos:
            try:
                res = f(id_obligacion, variables, k)
                break
            except Exception as e:  # noqa: BLE001 - cualquier fallo pasa a la siguiente fuente
                errores.append(f"{f.__name__}: {type(e).__name__}: {str(e)[:120]}")
    ms = round((time.perf_counter() - t0) * 1000, 1)
    respaldo = {"prob_propension_banco_t1": variables.get("prob_prob_propension_t1"), "prob_auto_cura_banco_t1": variables.get("prob_prob_auto_cura_t1"),
                "prob_alerta_temprana_banco_t1": variables.get("prob_prob_alrt_temprana_t1")}
    if res is None:
        return {"disponible": False, "motivo": "; ".join(errores), "latencia_ms": ms, "variables_faltantes": faltantes, "scores_banco": respaldo}
    for f in res["factores"]:
        f["descripcion"] = describir(f["variable"], f["valor"], f["sentido"])
    return {"disponible": True, **res, "latencia_ms": ms, "variables_faltantes": faltantes, "calidad_datos": "baja" if faltantes > 30 else "normal", "scores_banco": respaldo, "errores": errores}
