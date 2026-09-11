"""Sandbox sintético y pequeño para las pruebas del sistema agéntico (sin datos reales ni LLM)."""

from __future__ import annotations

import json
import os
import sys
from datetime import date, timedelta
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "agente"))
sys.path.insert(0, str(ROOT / "src"))

os.environ.setdefault("SANDBOX_HOY", "2024-01-15")
os.environ["MODELO_MODO"] = "local"
os.environ["GUARDRAIL_LLM"] = "0"
os.environ.setdefault("AGENTE_API_KEY", "clave-pruebas")

from sandbox.db import HOY, conectar, crear_esquema, insertar  # noqa: E402

CATALOGO = {"AMP": ("Ampliación de plazo", 3, 0.7), "RED": ("Reducción de cuota", 3, 0.6), "TASA": ("Renegociación de tasa", 3, 0.85), "REEST": ("Reestructuración de crédito", 4, 0.55)}


def _fecha(delta: int) -> str:
    return (date.fromisoformat(HOY) + timedelta(days=delta)).isoformat()


def variables_modelo() -> dict:
    """Las 100 variables del modelo con valores plausibles (las categóricas con niveles del paquete)."""
    from inferencia import Modelo
    m = Modelo.cargar(os.environ.get("MODELO_RUTA") or ROOT / "models" / "v4")
    v = {}
    for f in m.features:
        if f in m.categoricas:
            niveles = m.info.get("niveles_categoricas", {}).get(f) or []
            v[f] = niveles[0] if niveles else None
        else:
            v[f] = 1.0
    v["prob_prob_propension_t1"] = 0.7
    v["prob_prob_auto_cura_t1"] = 0.6
    return v


def agregar_cliente(con, cedula: str, *, dias_mora=20, opciones=("AMP", "RED"), aplicadas=(), acuerdos=(), restricciones=(), telefono="+57 3001234567", vencido=500_000.0, cuota=300_000.0, escenario="prueba"):
    insertar(con, "clientes", {"cedula": cedula, "nit_enmascarado": int(cedula[-6:]), "nombre": f"Cliente {cedula[-3:]}", "telefono": telefono, "fecha_nacimiento": "1990-01-01", "segmento": "PERSONAL",
                               "escenario": escenario, "descripcion_escenario": escenario})
    oid = f"{cedula[-6:]}#1#{cedula[-4:]}"
    etapa = "temprana" if dias_mora <= 30 else "media" if dias_mora <= 90 else "avanzada"
    insertar(con, "obligaciones", {"id_obligacion": oid, "cedula": cedula, "producto": "LIBRE INVERSION", "saldo_capital": 10_000_000.0, "valor_cuota": cuota, "valor_vencido": vencido,
                                   "dias_mora": dias_mora, "etapa_mora": etapa, "variables_modelo": variables_modelo()})
    for cod in opciones:
        nombre, espera, factor = CATALOGO[cod]
        insertar(con, "opciones_preaprobadas", {"id_obligacion": oid, "codigo": cod, "nombre": nombre, "descripcion": nombre, "cuota_nueva": cuota * factor, "plazo_meses": 48, "meses_espera": espera, "vigente_hasta": _fecha(30)})
    for cod, hace in aplicadas:
        nombre, espera, _ = CATALOGO[cod]
        insertar(con, "opciones_aplicadas", {"id_obligacion": oid, "codigo": cod, "nombre": nombre, "fecha_aplicacion": _fecha(-hace), "meses_espera": espera})
    for hace, plazo, estado in acuerdos:
        insertar(con, "acuerdos", {"id_obligacion": oid, "fecha_acuerdo": _fecha(-hace), "fecha_compromiso": _fecha(-hace + plazo), "valor": vencido, "estado": estado})
    for tipo in restricciones:
        insertar(con, "restricciones", {"cedula": cedula, "tipo": tipo, "detalle": tipo})
    return oid


@pytest.fixture
def sandbox(tmp_path, monkeypatch):
    ruta = tmp_path / "sandbox.db"
    monkeypatch.setenv("SANDBOX_DB", str(ruta))
    monkeypatch.setenv("AGENTE_CHECKPOINTS", str(tmp_path / "ck.db"))
    con = conectar(ruta)
    crear_esquema(con)
    clientes = {
        "temprana": agregar_cliente(con, "1000000001", dias_mora=20, opciones=("AMP",)),
        "varias": agregar_cliente(con, "1000000002", dias_mora=60, opciones=("AMP", "RED", "TASA", "REEST")),
        "espera": agregar_cliente(con, "1000000003", dias_mora=50, opciones=("AMP", "RED"), aplicadas=(("REEST", 40),)),
        "restriccion": agregar_cliente(con, "1000000004", dias_mora=50, opciones=("AMP",), restricciones=("juridica",)),
        "incumplido": agregar_cliente(con, "1000000005", dias_mora=40, opciones=("AMP", "RED"), acuerdos=((10, 5, "incumplido"),)),
        "sin_nada": agregar_cliente(con, "1000000006", dias_mora=120, opciones=(), acuerdos=((10, 5, "incumplido"),)),
        "sin_telefono": agregar_cliente(con, "1000000007", dias_mora=30, opciones=("AMP",), telefono=""),
        "acuerdo_vigente": agregar_cliente(con, "1000000008", dias_mora=15, opciones=(), acuerdos=((2, 5, "vigente"),)),
    }
    # herramientas y grafo toman la conexión del contexto
    from herramientas import contexto
    contexto.fijar("pruebas", 0, con)
    yield {"con": con, "ruta": ruta, "clientes": clientes}
    con.close()


def leer_otp(con, cedula: str) -> str:
    import re

    from herramientas.identidad import otp_vigente_sandbox
    sms = otp_vigente_sandbox(con, cedula)
    return re.search(r"\b(\d{6})\b", sms["texto"]).group(1)


def trazas(con, thread_id: str):
    return [dict(r) for r in con.execute("SELECT * FROM trazas WHERE thread_id = ? ORDER BY id", (thread_id,)).fetchall()]


def detalle(t: dict) -> dict:
    return json.loads(t["detalle"]) if t["detalle"] and t["detalle"].startswith("{") else {}
