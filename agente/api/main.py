"""API del sistema agéntico (FastAPI). Servicio separado de la API del modelo.

Endpoints (todos con X-API-Key salvo /health):
    POST /chat                       mensaje del cliente en un hilo (thread_id = cédula); devuelve la respuesta del agente
    POST /proactivo                  gestión proactiva de una cédula: modelo -> siguiente mejor acción -> plantilla de WhatsApp
    POST /proactivo/lote             lo mismo para una lista de cédulas (campaña del día)
    GET  /conversaciones/{thread_id} historial del hilo (WhatsApp y SMS simulados)
    GET  /trazas/{thread_id}         decisiones, herramientas, guardrails, tokens y latencia por turno
    GET  /escalamientos              casos abiertos para gestores humanos
    GET  /sandbox/clientes           perfiles simulados (sin datos personales reales)
    GET  /sandbox/otp/{cedula}       último SMS de OTP (solo en modo sandbox, simula mirar el teléfono)
    POST /sandbox/reiniciar          vuelve a crear la base del sandbox y borra los hilos (solo sandbox)
    GET  /health

Variables: AGENTE_API_KEY, SANDBOX_DB, AGENTE_CHECKPOINTS, MODELO_API_URL, MODELO_API_KEY, MODELO_MODO, LLM_MODELO, GCP_PROJECT_ID, LLM_REGION, SANDBOX_MODO (1 = endpoints de sandbox activos).
"""

from __future__ import annotations

import hmac
import os
import subprocess
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "agente"))
load_dotenv(ROOT / ".env")

from grafo.grafo import Conversador  # noqa: E402
from grafo.proactivo import gestionar_proactivo  # noqa: E402
from herramientas.cartera import consultar_deuda, evaluar_elegibilidad  # noqa: E402
from herramientas.estrategia import siguiente_mejor_accion  # noqa: E402
from herramientas.identidad import otp_vigente_sandbox  # noqa: E402
from sandbox.db import filas  # noqa: E402
from sandbox.whatsapp import bandeja  # noqa: E402


@asynccontextmanager
async def ciclo_de_vida(app: FastAPI):
    app.state.conv = Conversador()
    yield


app = FastAPI(title="Agente de cobranza (Parte 2)", description="Sistema agéntico para gestión proactiva y reactiva de clientes en mora.", version="1.0.0", lifespan=ciclo_de_vida)


def conv() -> Conversador:
    if not hasattr(app.state, "conv"):
        app.state.conv = Conversador()
    return app.state.conv


def verificar_api_key(x_api_key: str | None = Header(default=None, alias="X-API-Key")) -> None:
    esperada = os.environ.get("AGENTE_API_KEY")
    if not esperada:
        raise HTTPException(status_code=503, detail="AGENTE_API_KEY no configurada en el servidor")
    if x_api_key is None or not hmac.compare_digest(x_api_key, esperada):
        raise HTTPException(status_code=401, detail="clave de API inválida o ausente")


def solo_sandbox() -> None:
    if os.environ.get("SANDBOX_MODO", "1") != "1":
        raise HTTPException(status_code=404, detail="no disponible fuera del sandbox")


class PeticionChat(BaseModel):
    thread_id: str = Field(..., min_length=1, max_length=64, description="Identificador del hilo; en el canal es la cédula del cliente")
    mensaje: str = Field(..., min_length=1, max_length=4000)


class RespuestaChat(BaseModel):
    thread_id: str
    turno: int
    respuesta: str
    verificado: bool
    bloqueado: bool
    accion: str | None
    escalado: dict | None
    ruta: list[str]
    guardrail_entrada: str | None
    guardrail_salida: bool | None
    uso: dict | None
    latencia_ms: float


class PeticionProactivo(BaseModel):
    cedula: str = Field(..., min_length=5, max_length=20)
    id_obligacion: str | None = None


class PeticionLote(BaseModel):
    cedulas: list[str] = Field(..., min_length=1, max_length=200)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/chat", response_model=RespuestaChat, dependencies=[Depends(verificar_api_key)])
def chat(p: PeticionChat) -> Any:
    return conv().responder(p.thread_id, p.mensaje)


@app.post("/proactivo", dependencies=[Depends(verificar_api_key)])
def proactivo(p: PeticionProactivo) -> dict:
    r = gestionar_proactivo(conv(), p.cedula, p.id_obligacion)
    if r.get("accion") is None:
        raise HTTPException(status_code=404, detail=r.get("motivo", "cliente no encontrado"))
    return r


@app.post("/proactivo/lote", dependencies=[Depends(verificar_api_key)])
def proactivo_lote(p: PeticionLote) -> dict:
    res = [gestionar_proactivo(conv(), c) for c in p.cedulas]
    resumen: dict[str, int] = {}
    for r in res:
        resumen[str(r.get("accion"))] = resumen.get(str(r.get("accion")), 0) + 1
    return {"n": len(res), "enviados": sum(1 for r in res if r.get("enviado")), "por_accion": resumen, "resultados": res}


@app.get("/conversaciones/{thread_id}", dependencies=[Depends(verificar_api_key)])
def conversacion(thread_id: str) -> dict:
    est = conv().estado(thread_id)
    return {"thread_id": thread_id, "mensajes": bandeja(conv().con, thread_id), "verificado": bool(est.get("verificado")), "bloqueado": bool(est.get("bloqueado")),
            "origen": est.get("origen"), "accion": (est.get("nba") or {}).get("accion"), "escalado": est.get("escalado"), "turno": est.get("turno", 0)}


@app.get("/trazas/{thread_id}", dependencies=[Depends(verificar_api_key)])
def trazas(thread_id: str) -> dict:
    t = filas(conv().con, "SELECT turno, nodo, evento, detalle, latencia_ms, tokens_entrada, tokens_salida, creado FROM trazas WHERE thread_id = ? ORDER BY id", (thread_id,))
    return {"thread_id": thread_id, "n": len(t), "tokens_entrada": sum(x["tokens_entrada"] or 0 for x in t), "tokens_salida": sum(x["tokens_salida"] or 0 for x in t), "trazas": t}


@app.get("/escalamientos", dependencies=[Depends(verificar_api_key)])
def escalamientos() -> dict:
    e = filas(conv().con, "SELECT * FROM escalamientos ORDER BY id DESC LIMIT 200")
    return {"n": len(e), "casos": e}


@app.get("/sandbox/clientes", dependencies=[Depends(verificar_api_key), Depends(solo_sandbox)])
def clientes() -> dict:
    c = filas(conv().con, "SELECT c.cedula, c.nombre, c.telefono, c.escenario, c.descripcion_escenario, o.id_obligacion, o.producto, o.dias_mora, o.etapa_mora, o.saldo_capital, o.valor_cuota, o.valor_vencido "
                          "FROM clientes c JOIN obligaciones o ON o.cedula = c.cedula ORDER BY c.rowid")
    return {"n": len(c), "clientes": c}


@app.get("/sandbox/cliente/{cedula}", dependencies=[Depends(verificar_api_key), Depends(solo_sandbox)])
def ficha(cedula: str) -> dict:
    """Ficha completa para el probador: deuda, elegibilidad y siguiente mejor acción (lo que vería el gestor)."""
    c = conv().con
    d = consultar_deuda(c, cedula)
    if not d.get("encontrado"):
        raise HTTPException(status_code=404, detail="cliente no encontrado")
    perfil = filas(c, "SELECT cedula, nombre, telefono, escenario, descripcion_escenario FROM clientes WHERE cedula = ?", (cedula,))[0]
    obls = [{**o, "elegibilidad": evaluar_elegibilidad(c, o["id_obligacion"]), "preaprobadas": filas(c, "SELECT codigo, nombre, cuota_nueva, plazo_meses, meses_espera, vigente_hasta FROM opciones_preaprobadas WHERE id_obligacion = ?", (o["id_obligacion"],))}
            for o in d["obligaciones"]]
    return {"perfil": perfil, "deuda": {**d, "obligaciones": obls}, "siguiente_mejor_accion": siguiente_mejor_accion(c, cedula)}


@app.get("/sandbox/otp/{cedula}", dependencies=[Depends(verificar_api_key), Depends(solo_sandbox)])
def otp(cedula: str) -> dict:
    r = otp_vigente_sandbox(conv().con, cedula)
    return {"cedula": cedula, "sms": r}


@app.post("/sandbox/reiniciar", dependencies=[Depends(verificar_api_key), Depends(solo_sandbox)])
def reiniciar() -> dict:
    c = conv()
    c.con.close()
    c._con_ck.close()
    ck = Path(os.environ.get("AGENTE_CHECKPOINTS") or ROOT / "agente" / "sandbox" / "checkpoints.db")
    if ck.exists():
        ck.unlink()
    out = subprocess.run([sys.executable, str(ROOT / "agente" / "sandbox" / "crear_sandbox.py")], capture_output=True, text=True, cwd=str(ROOT))
    app.state.conv = Conversador()
    return {"reiniciado": out.returncode == 0, "detalle": (out.stdout or out.stderr)[-500:]}
