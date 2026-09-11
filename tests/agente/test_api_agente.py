"""API del agente: seguridad, validación y contratos, con el conversador simulado."""

import importlib.util
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
# Se carga por ruta con un nombre propio para no chocar con api/main.py (la API del modelo) en la misma sesión de pytest
_spec = importlib.util.spec_from_file_location("agente_api_main", ROOT / "agente" / "api" / "main.py")
api_main = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(api_main)

CAB = {"X-API-Key": "clave-pruebas"}


class ConvFalso:
    def __init__(self, con):
        self.con = con
        self._con_ck = con

    def responder(self, thread_id, mensaje, origen="reactivo", telefono=None):
        return {"thread_id": thread_id, "turno": 1, "respuesta": f"eco: {mensaje}", "verificado": False, "bloqueado": False, "escalado": None, "accion": None,
                "ruta": ["guardrail_entrada", "agente", "guardrail_salida"], "guardrail_entrada": "normal", "guardrail_salida": True, "uso": {"llamadas_llm": 1}, "latencia_ms": 1.0}

    def estado(self, thread_id):
        return {"turno": 1, "verificado": False}

    def abrir_hilo_proactivo(self, *a, **k):
        pass


@pytest.fixture
def cliente(sandbox, monkeypatch):
    monkeypatch.setenv("AGENTE_API_KEY", "clave-pruebas")
    monkeypatch.setenv("SANDBOX_MODO", "1")
    monkeypatch.setattr(api_main, "Conversador", lambda: ConvFalso(sandbox["con"]))  # el arranque no debe crear el conversador real
    with TestClient(api_main.app) as c:
        api_main.app.state.conv = ConvFalso(sandbox["con"])
        yield c


def test_health_y_seguridad(cliente, monkeypatch):
    assert cliente.get("/health").json() == {"status": "ok"}
    assert cliente.post("/chat", json={"thread_id": "x", "mensaje": "hola"}).status_code == 401
    assert cliente.post("/chat", headers={"X-API-Key": "mala"}, json={"thread_id": "x", "mensaje": "hola"}).status_code == 401
    monkeypatch.delenv("AGENTE_API_KEY")
    assert cliente.post("/chat", headers=CAB, json={"thread_id": "x", "mensaje": "hola"}).status_code == 503


def test_chat_validacion_y_respuesta(cliente):
    assert cliente.post("/chat", headers=CAB, json={"thread_id": "x"}).status_code == 422
    assert cliente.post("/chat", headers=CAB, json={"thread_id": "x", "mensaje": ""}).status_code == 422
    r = cliente.post("/chat", headers=CAB, json={"thread_id": "1000000001", "mensaje": "hola"})
    assert r.status_code == 200 and r.json()["respuesta"] == "eco: hola" and r.json()["ruta"][0] == "guardrail_entrada"


def test_proactivo_y_lote(cliente):
    r = cliente.post("/proactivo", headers=CAB, json={"cedula": "1000000001"})
    assert r.status_code == 200 and r.json()["accion"] == "ACUERDO_PAGO" and r.json()["enviado"]
    assert cliente.post("/proactivo", headers=CAB, json={"cedula": "99999"}).status_code == 404
    r = cliente.post("/proactivo/lote", headers=CAB, json={"cedulas": ["1000000002", "1000000004", "1000000007"]})
    d = r.json()
    assert d["n"] == 3 and d["enviados"] == 1 and d["por_accion"]["GESTOR_HUMANO"] == 1


def test_consultas(cliente):
    cliente.post("/proactivo", headers=CAB, json={"cedula": "1000000001"})
    c = cliente.get("/conversaciones/1000000001", headers=CAB).json()
    assert c["mensajes"][0]["tipo"] == "plantilla"
    t = cliente.get("/trazas/1000000001", headers=CAB).json()
    assert t["n"] >= 2 and any(x["nodo"] == "proactivo" for x in t["trazas"])
    assert cliente.get("/escalamientos", headers=CAB).json()["n"] >= 0
    cl = cliente.get("/sandbox/clientes", headers=CAB).json()
    assert cl["n"] == 8
    f = cliente.get("/sandbox/cliente/1000000002", headers=CAB).json()
    assert f["siguiente_mejor_accion"]["accion"] in ("OFRECER_OPCION", "ACUERDO_PAGO") and len(f["deuda"]["obligaciones"][0]["preaprobadas"]) == 4
    assert cliente.get("/sandbox/cliente/0", headers=CAB).status_code == 404
    assert cliente.get("/sandbox/otp/1000000001", headers=CAB).json()["sms"] is None


def test_sandbox_desactivado(cliente, monkeypatch):
    monkeypatch.setenv("SANDBOX_MODO", "0")
    assert cliente.get("/sandbox/clientes", headers=CAB).status_code == 404
