"""Grafo de conversación (LangGraph): guardrail de entrada -> deep agent -> guardrail de salida -> (escalamiento).

Estado por hilo (thread_id = cédula del cliente en el canal) persistido con SqliteSaver. El deep agent se
construye por turno con el prompt versionado y el contexto del hilo; las herramientas exigen verificación
por OTP, así que aunque el LLM se confunda no puede acceder a datos ni registrar nada sin ella.
"""

from __future__ import annotations

import json
import os
import sqlite3
import time
from pathlib import Path
from typing import Annotated, Any, Literal, TypedDict

from grafo import guardrails
from grafo.llm import llm
from herramientas import contexto, tools
from herramientas.cartera import escalar_a_humano
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from sandbox.db import HOY, conectar, fila, registrar_traza
from sandbox.whatsapp import enviar_mensaje

ROOT = Path(__file__).resolve().parents[2]
PROMPTS = ROOT / "agente" / "prompts"
VERSION_PROMPT = "v1"

RESPUESTAS_FIJAS = {
    "vacio": "No recibí tu mensaje. Escríbeme en qué te puedo ayudar con tu obligación.",
    "inyeccion": "Solo puedo ayudarte con la gestión de tus obligaciones con Bancolombia. Si quieres, dame tu número de cédula para continuar.",
    "inyeccion_verificado": "Solo puedo gestionar lo que el sistema autoriza para tu obligación; no tengo facultad para aprobar nada distinto. Si quieres, continuamos con tu gestión o te comunico con un gestor.",
    "tercero": "Por seguridad solo puedo tratar información de la persona que se verifica en esta conversación. Si necesitas ayuda con otra persona, ella puede escribirnos o puedes comunicarte con un gestor.",
    "fuera_de_alcance": "Este canal es para la gestión de tus obligaciones con Bancolombia. Cuéntame si quieres revisar tu estado o ponerte al día.",
    "bloqueado": "Por seguridad no fue posible completar la verificación en este canal. Un gestor de Bancolombia se comunicará contigo en el siguiente día hábil.",
    "salida_invalida": "Disculpa, en este momento no puedo darte esa información por este medio. Un gestor de Bancolombia te contactará en el siguiente día hábil.",
    "escalado": "Entiendo. He dejado tu caso en manos de un gestor de Bancolombia, que se comunicará contigo en el siguiente día hábil.",
}


class Estado(TypedDict, total=False):
    messages: Annotated[list, add_messages]
    thread_id: str
    turno: int
    origen: str                     # reactivo | proactivo
    cedula: str | None
    cedula_candidata: str | None
    cedula_hilo: str | None          # cliente al que se dirigió la gestión proactiva
    cedula_hilo: str | None          # cliente al que se dirigió la gestión proactiva
    verificado: bool
    bloqueado: bool
    escalado: dict | None
    nba: dict | None
    ofertas_autorizadas: list[dict]
    guardrail_entrada: dict
    guardrail_salida: dict
    respuesta: str
    ruta: list[str]
    uso: dict
    reintentos: int
    retroalimentacion: str | None


def _texto(m) -> str:
    """Texto de un mensaje del LLM (Gemini devuelve bloques de contenido)."""
    c = m.content
    if isinstance(c, str):
        return c.strip()
    if isinstance(c, list):
        return chr(10).join(b.get("text", "") if isinstance(b, dict) else str(b) for b in c if not isinstance(b, dict) or b.get("type", "text") == "text").strip()
    return str(c or "").strip()


def _prompt(estado: Estado) -> str:
    ver = bool(estado.get("verificado"))
    ctx = {"origen": estado.get("origen", "reactivo"), "identidad_verificada": ver,
           "cliente_identificado_pendiente_de_codigo": bool(estado.get("cedula_candidata")) and not ver,
           "accion_sugerida_proactiva": (estado.get("nba") or {}).get("accion") if estado.get("origen") == "proactivo" else None}
    nba = estado.get("nba") or {}
    if ver and nba:
        ctx["gestion_en_curso"] = {"accion": nba.get("accion"), "motivo": nba.get("motivo"), "producto": nba.get("producto"), "dias_mora": nba.get("dias_mora"),
                                   "ofertas_autorizadas": estado.get("ofertas_autorizadas") or [], "opcion_recomendada": (nba.get("opcion_recomendada") or {}).get("nombre")}
    if estado.get("cedula_candidata") and not ver:
        ctx["indicacion"] = "el cliente ya fue encontrado y se le envió el código por SMS; si escribe un código de 6 dígitos, llama a validar_codigo_verificacion; no vuelvas a pedir la cédula"
    from datetime import date
    dias = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
    hoy = f"{dias[date.fromisoformat(HOY).weekday()]} {HOY}"
    return (PROMPTS / "agente_principal.md").read_text(encoding="utf-8").replace("{hoy}", hoy).replace("{contexto}", json.dumps(ctx, ensure_ascii=False))


def _sesion_desde_estado(estado: Estado) -> dict[str, Any]:
    return {"cedula": estado.get("cedula"), "cedula_candidata": estado.get("cedula_candidata"), "cedula_hilo": estado.get("cedula_hilo"), "verificado": bool(estado.get("verificado")), "bloqueado": bool(estado.get("bloqueado")),
            "escalado": estado.get("escalado"), "nba": estado.get("nba"), "ofertas_autorizadas": list(estado.get("ofertas_autorizadas") or [])}


def _registrar_perfil_gemini() -> None:
    """Quita del deep agent las herramientas de archivos y de shell (no aplican a un asistente de cobranza)."""
    from deepagents import GeneralPurposeSubagentProfile, HarnessProfile, register_harness_profile
    try:
        register_harness_profile("google_genai", HarnessProfile(excluded_tools=frozenset({"ls", "read_file", "write_file", "edit_file", "glob", "grep", "execute"}),
                                                                 general_purpose_subagent=GeneralPurposeSubagentProfile(enabled=False)))
    except Exception:  # noqa: BLE001 - ya registrado
        pass


_registrar_perfil_gemini()


def crear_agente(estado: Estado):
    from deepagents import create_deep_agent
    analista = {"name": "analista_cartera",
                "description": "Analiza la situación del cliente verificado: consulta la deuda, evalúa la siguiente mejor acción y devuelve un resumen estructurado con la acción, el motivo, las ofertas autorizadas y los factores en lenguaje de negocio.",
                "system_prompt": (PROMPTS / "subagente_analista.md").read_text(encoding="utf-8"),
                "tools": [tools.consultar_deuda, tools.evaluar_siguiente_accion]}
    return create_deep_agent(model=llm(0.2, pensamiento=1024), tools=tools.HERRAMIENTAS, system_prompt=_prompt(estado), subagents=[analista], name="agente_cobranza")


# ------------------------------------------------------------------ nodos
def nodo_guardrail_entrada(estado: Estado) -> dict:
    t0 = time.perf_counter()
    con = contexto.con()
    ultimo = _texto(estado["messages"][-1]) if estado.get("messages") else ""
    if estado.get("bloqueado") or (estado.get("escalado") and estado.get("escalado", {}).get("cerrado")):
        r = {"categoria": "bloqueado", "motivo": "hilo bloqueado o escalado", "requiere_humano": True, "fuente": "estado", "permitido": False}
    else:
        r = guardrails.revisar_entrada(ultimo, usar_llm=os.environ.get("GUARDRAIL_LLM", "1") == "1")
    registrar_traza(con, estado["thread_id"], estado["turno"], "guardrail_entrada", r["categoria"], r, latencia_ms=round((time.perf_counter() - t0) * 1000, 1))
    return {"guardrail_entrada": r, "ruta": estado.get("ruta", []) + ["guardrail_entrada"]}


def despues_de_entrada(estado: Estado) -> Literal["agente", "responder_fijo", "escalamiento"]:
    g = estado["guardrail_entrada"]
    if g["categoria"] == "bloqueado":
        return "escalamiento"
    if g["categoria"] == "sensible" and g.get("requiere_humano") and not estado.get("verificado"):
        return "escalamiento"
    return "agente" if g["permitido"] else "responder_fijo"


def nodo_responder_fijo(estado: Estado) -> dict:
    cat = estado["guardrail_entrada"]["categoria"]
    if cat == "inyeccion" and estado.get("verificado"):
        cat = "inyeccion_verificado"
    texto = RESPUESTAS_FIJAS.get(cat, RESPUESTAS_FIJAS["fuera_de_alcance"])
    return {"respuesta": texto, "messages": [AIMessage(content=texto)], "ruta": estado.get("ruta", []) + ["responder_fijo"]}


def nodo_agente(estado: Estado) -> dict:
    t0 = time.perf_counter()
    con = contexto.con()
    sesion = _sesion_desde_estado(estado)
    tools.iniciar_sesion(sesion)
    agente = crear_agente(estado)
    historial = [HumanMessage(content=_texto(m)) if isinstance(m, HumanMessage) else AIMessage(content=_texto(m)) for m in estado["messages"] if isinstance(m, (HumanMessage, AIMessage)) and _texto(m)][-30:]
    if estado.get("retroalimentacion"):
        historial.append(HumanMessage(content=f"[SUPERVISOR INTERNO, no es el cliente] Tu respuesta anterior fue rechazada por el guardrail de salida: {estado['retroalimentacion']}. "
                                              "Corrige y responde de nuevo al último mensaje del cliente cumpliendo las reglas; si te falta información, llama a la herramienta correspondiente."))
    uso = {"tokens_entrada": 0, "tokens_salida": 0, "llamadas_llm": 0, "herramientas": []}
    try:
        try:
            salida = agente.invoke({"messages": historial}, config={"recursion_limit": 40})
        except Exception as e:  # noqa: BLE001 - cuota de Vertex agotada: espera y reintenta una vez
            if "429" not in str(e) and "RESOURCE_EXHAUSTED" not in str(e):
                raise
            time.sleep(8)
            salida = agente.invoke({"messages": historial}, config={"recursion_limit": 40})
        nuevos = salida["messages"][len(historial):]
        for m in nuevos:
            if isinstance(m, AIMessage):
                u = m.usage_metadata or {}
                uso["tokens_entrada"] += int(u.get("input_tokens", 0)); uso["tokens_salida"] += int(u.get("output_tokens", 0)); uso["llamadas_llm"] += 1
                uso["herramientas"] += [tc["name"] for tc in (m.tool_calls or [])]
        texto = next((_texto(m) for m in reversed(nuevos) if isinstance(m, AIMessage) and _texto(m)), "")
        if not texto:
            texto = RESPUESTAS_FIJAS["salida_invalida"]
        error = None
    except Exception as e:  # noqa: BLE001 - indisponibilidad del LLM o del agente
        texto = "En este momento no puedo continuar la atención por este canal. Inténtalo de nuevo en unos minutos o comunícate con un gestor de Bancolombia."
        error = f"{type(e).__name__}: {str(e)[:200]}"
    ms = round((time.perf_counter() - t0) * 1000, 1)
    registrar_traza(con, estado["thread_id"], estado["turno"], "agente", "respuesta" if not error else "error", {"uso": uso, "error": error, "sesion": {k: v for k, v in sesion.items() if k != "nba"}},
                    latencia_ms=ms, tokens_entrada=uso["tokens_entrada"], tokens_salida=uso["tokens_salida"])
    uso_prev = estado.get("uso") or {}
    if estado.get("retroalimentacion"):  # segundo intento: acumula el uso del turno
        uso = {k: (uso_prev.get(k, 0) + uso[k]) if isinstance(uso[k], int) else uso_prev.get(k, []) + uso[k] for k in uso}
    return {"respuesta": texto, "cedula": sesion["cedula"], "cedula_candidata": sesion["cedula_candidata"], "verificado": sesion["verificado"], "bloqueado": sesion["bloqueado"],
            "escalado": sesion["escalado"], "nba": sesion["nba"], "ofertas_autorizadas": sesion["ofertas_autorizadas"], "uso": {**uso, "latencia_ms": ms + (uso_prev.get("latencia_ms", 0) if estado.get("retroalimentacion") else 0)},
            "ruta": estado.get("ruta", []) + ["agente"], "retroalimentacion": None}


def nodo_guardrail_salida(estado: Estado) -> dict:
    t0 = time.perf_counter()
    con = contexto.con()
    registros = con.execute("SELECT COUNT(*) FROM trazas WHERE thread_id = ? AND turno = ? AND nodo = 'herramienta' AND evento IN ('registrar_acuerdo_pago', 'aplicar_opcion_pago', 'registrar_nota', 'escalar_a_gestor_humano') AND (detalle LIKE '%\"registrado\": true%' OR detalle LIKE '%\"escalado\": true%')",
                            (estado["thread_id"], estado["turno"])).fetchone()[0]
    otp_enviado = con.execute("SELECT COUNT(*) FROM trazas WHERE thread_id = ? AND turno = ? AND nodo = 'herramienta' AND evento IN ('buscar_cliente', 'enviar_codigo_verificacion') AND (detalle LIKE '%\"codigo_enviado\": true%' OR detalle LIKE '%\"enviado\": true%')",
                              (estado["thread_id"], estado["turno"])).fetchone()[0]
    ultimo = next((_texto(m) for m in reversed(estado["messages"]) if isinstance(m, HumanMessage)), "")
    r = guardrails.revisar_salida(estado["respuesta"], bool(estado.get("verificado")), estado.get("ofertas_autorizadas") or [], estado.get("cedula"), usar_llm=os.environ.get("GUARDRAIL_LLM", "1") == "1",
                                  ultimo_mensaje=ultimo, registros_turno=int(registros), otp_enviado_turno=int(otp_enviado), codigo_pendiente=bool(estado.get("cedula_candidata")) and not estado.get("verificado"))
    reintentos = int(estado.get("reintentos") or 0)
    texto = estado["respuesta"]
    salida: dict = {"ruta": estado.get("ruta", []) + ["guardrail_salida"]}
    if r["cumple"]:
        evento = "cumple"
        salida.update({"respuesta": texto, "messages": [AIMessage(content=texto)], "retroalimentacion": None})
    elif reintentos < 1:
        evento = "reintento"
        r["respuesta_rechazada"] = texto
        salida.update({"reintentos": reintentos + 1, "retroalimentacion": "; ".join(r["violaciones"])})
    else:
        evento = "bloqueada"
        r["respuesta_bloqueada"] = texto
        texto = RESPUESTAS_FIJAS["salida_invalida"]
        salida.update({"respuesta": texto, "messages": [AIMessage(content=texto)], "retroalimentacion": None})
    registrar_traza(con, estado["thread_id"], estado["turno"], "guardrail_salida", evento, r, latencia_ms=round((time.perf_counter() - t0) * 1000, 1))
    salida["guardrail_salida"] = {**r, "evento": evento}
    return salida


def despues_de_salida(estado: Estado) -> Literal["agente", "escalamiento", "__end__"]:
    if estado["guardrail_salida"].get("evento") == "reintento":
        return "agente"
    if estado.get("bloqueado") or not estado["guardrail_salida"]["cumple"]:
        return "escalamiento"
    return END


def nodo_escalamiento(estado: Estado) -> dict:
    con = contexto.con()
    g = estado.get("guardrail_entrada", {})
    gs = estado.get("guardrail_salida", {})
    if estado.get("escalado") and estado["escalado"].get("id_caso") and not gs.get("respuesta_bloqueada"):
        motivo = estado["escalado"]["motivo"]; nuevo = False
    else:
        motivo = ("respuesta bloqueada por guardrail de salida: " + "; ".join(gs.get("violaciones", []))) if gs.get("respuesta_bloqueada") else \
                 ("verificación bloqueada" if estado.get("bloqueado") else f"guardrail de entrada: {g.get('categoria')} ({g.get('motivo')})")
        nuevo = True
    resumen = " | ".join(f"{'cliente' if isinstance(m, HumanMessage) else 'asistente'}: {_texto(m)[:160]}" for m in estado["messages"][-6:])
    if nuevo:
        r = escalar_a_humano(con, estado["thread_id"], estado.get("cedula") or estado.get("cedula_candidata"), motivo, resumen, "alta" if g.get("categoria") == "sensible" else "media")
        escalado = {"motivo": motivo, "prioridad": r["prioridad"], "id_caso": r["id_caso"]}
    else:
        escalado = estado["escalado"]
    registrar_traza(con, estado["thread_id"], estado["turno"], "escalamiento", "caso_creado" if nuevo else "caso_existente", escalado)
    salida = {"escalado": {**escalado, "cerrado": bool(estado.get("bloqueado"))}, "ruta": estado.get("ruta", []) + ["escalamiento"]}
    if "guardrail_salida" not in estado or not estado["guardrail_salida"]:
        texto = RESPUESTAS_FIJAS["bloqueado"] if estado.get("bloqueado") else RESPUESTAS_FIJAS["escalado"]
        salida.update({"respuesta": texto, "messages": [AIMessage(content=texto)]})
    return salida


def construir(checkpointer=None):
    g = StateGraph(Estado)
    g.add_node("guardrail_entrada", nodo_guardrail_entrada)
    g.add_node("responder_fijo", nodo_responder_fijo)
    g.add_node("agente", nodo_agente)
    g.add_node("guardrail_salida", nodo_guardrail_salida)
    g.add_node("escalamiento", nodo_escalamiento)
    g.add_edge(START, "guardrail_entrada")
    g.add_conditional_edges("guardrail_entrada", despues_de_entrada, {"agente": "agente", "responder_fijo": "responder_fijo", "escalamiento": "escalamiento"})
    g.add_edge("responder_fijo", END)
    g.add_edge("agente", "guardrail_salida")
    g.add_conditional_edges("guardrail_salida", despues_de_salida, {"agente": "agente", "escalamiento": "escalamiento", END: END})
    g.add_edge("escalamiento", END)
    return g.compile(checkpointer=checkpointer)


# ------------------------------------------------------------------ fachada
class Conversador:
    """Envuelve el grafo con persistencia por hilo y el canal simulado."""

    def __init__(self, ruta_checkpoints: str | Path | None = None, ruta_sandbox: str | Path | None = None):
        ruta = Path(ruta_checkpoints or os.environ.get("AGENTE_CHECKPOINTS") or ROOT / "agente" / "sandbox" / "checkpoints.db")
        self._con_ck = sqlite3.connect(str(ruta), check_same_thread=False)
        self.checkpointer = SqliteSaver(self._con_ck)
        self.grafo = construir(self.checkpointer)
        self.con = conectar(ruta_sandbox)

    def estado(self, thread_id: str) -> dict:
        s = self.grafo.get_state({"configurable": {"thread_id": thread_id}})
        return dict(s.values) if s and s.values else {}

    def responder(self, thread_id: str, mensaje: str, origen: str = "reactivo", telefono: str | None = None) -> dict:
        previo = self.estado(thread_id)
        turno = int(previo.get("turno", 0)) + 1
        contexto.fijar(thread_id, turno, self.con)
        tel = telefono or _telefono(self.con, previo.get("cedula") or thread_id)
        enviar_mensaje(self.con, thread_id, tel, mensaje, "entrante")
        entrada = {"messages": [HumanMessage(content=mensaje)], "thread_id": thread_id, "turno": turno, "origen": previo.get("origen") or origen, "ruta": [], "guardrail_salida": {}, "reintentos": 0, "retroalimentacion": None, "uso": {}}
        t0 = time.perf_counter()
        salida = self.grafo.invoke(entrada, config={"configurable": {"thread_id": thread_id}})
        enviar_mensaje(self.con, thread_id, tel, salida["respuesta"], "saliente")
        return {"thread_id": thread_id, "turno": turno, "respuesta": salida["respuesta"], "verificado": bool(salida.get("verificado")), "bloqueado": bool(salida.get("bloqueado")),
                "escalado": salida.get("escalado"), "accion": (salida.get("nba") or {}).get("accion"), "ruta": salida.get("ruta", []),
                "guardrail_entrada": salida.get("guardrail_entrada", {}).get("categoria"), "guardrail_salida": salida.get("guardrail_salida", {}).get("cumple"),
                "uso": salida.get("uso"), "latencia_ms": round((time.perf_counter() - t0) * 1000, 1)}

    def abrir_hilo_proactivo(self, thread_id: str, cedula: str, nba: dict, texto_plantilla: str) -> None:
        """Deja en el estado del hilo la acción decidida y la plantilla enviada, para que el agente continúe desde ahí."""
        contexto.fijar(thread_id, 0, self.con)
        self.grafo.update_state({"configurable": {"thread_id": thread_id}},
                                {"messages": [AIMessage(content=texto_plantilla)], "thread_id": thread_id, "turno": 0, "origen": "proactivo", "cedula_hilo": cedula, "cedula_candidata": None,
                                 "verificado": False, "nba": nba, "ofertas_autorizadas": [], "ruta": []})


def _telefono(con, cedula: str | None) -> str:
    c = fila(con, "SELECT telefono FROM clientes WHERE cedula = ?", (cedula,)) if cedula else None
    return (c or {}).get("telefono") or "desconocido"
