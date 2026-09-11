"""Herramientas que ve el LLM (LangChain tools).

Ninguna recibe el hilo ni la cédula verificada como argumento: los toman del contexto que fija el
grafo. Las herramientas de cartera exigen identidad verificada; si no lo está, devuelven un error y
el modelo no puede acceder a datos ni registrar nada. Cada llamada deja traza.
"""

from __future__ import annotations

import json
import time
from contextvars import ContextVar
from typing import Any

from herramientas import cartera, contexto, estrategia, identidad
from langchain_core.tools import tool
from sandbox.db import registrar_traza

# Estado de sesión que las herramientas comparten con el grafo (por hilo)
_estado: ContextVar[dict[str, Any]] = ContextVar("estado_sesion")


def iniciar_sesion(estado: dict[str, Any]) -> None:
    _estado.set(estado)


def estado() -> dict[str, Any]:
    try:
        return _estado.get()
    except LookupError:
        e = {"cedula": None, "cedula_candidata": None, "cedula_hilo": None, "verificado": False, "bloqueado": False, "escalado": None, "nba": None, "ofertas_autorizadas": []}
        _estado.set(e)
        return e


def _traza(nombre: str, args: dict, resultado: Any, t0: float) -> None:
    res = json.loads(json.dumps(resultado, default=str))
    registrar_traza(contexto.con(), contexto.thread_id(), contexto.turno(), "herramienta", nombre, {"args": args, "resultado": res}, latencia_ms=round((time.perf_counter() - t0) * 1000, 1))


def _obligacion(id_obligacion: str | None) -> str | dict:
    """Resuelve la obligación sobre la que se actúa: la indicada si pertenece al cliente verificado, si no la de la última evaluación."""
    from sandbox.db import filas
    e = estado()
    propias = [o["id_obligacion"] for o in filas(contexto.con(), "SELECT id_obligacion FROM obligaciones WHERE cedula = ?", (e["cedula"],))]
    if id_obligacion and id_obligacion in propias:
        return id_obligacion
    nba = e.get("nba") or {}
    if nba.get("id_obligacion") in propias:
        return nba["id_obligacion"]
    if len(propias) == 1:
        return propias[0]
    return {"error": "no se identificó la obligación; llama primero a evaluar_siguiente_accion"}


def _requiere_verificacion() -> dict | None:
    e = estado()
    if not e["verificado"] or not e["cedula"]:
        return {"error": "identidad no verificada: pide la cédula, envía el código de verificación y valídalo antes de consultar o registrar cualquier cosa"}
    return None


@tool
def buscar_cliente(cedula: str) -> dict:
    """Busca al cliente por número de cédula y, si existe, le envía automáticamente por SMS el código de verificación (OTP)
    de 6 dígitos. Devuelve el nombre de pila y el teléfono enmascarado; no revela saldos ni ofertas. Después pide al cliente
    que escriba el código que le llegó."""
    t0 = time.perf_counter()
    r = identidad.buscar_cliente(contexto.con(), cedula)
    e = estado()
    if r.get("encontrado"):
        if e["verificado"] and e["cedula"] and e["cedula"] != r["cedula"]:
            r = {"encontrado": False, "motivo": "en esta conversación ya se verificó otra cédula; no se puede consultar información de terceros"}
        elif e.get("cedula_hilo") and e["cedula_hilo"] != r["cedula"]:
            r = {"encontrado": False, "motivo": "esta conversación fue iniciada por el banco para otro cliente; no se puede atender a un tercero por este hilo"}
        else:
            e["cedula_candidata"] = r["cedula"]
            envio = identidad.enviar_otp(contexto.con(), r["cedula"], contexto.thread_id())
            if envio.get("bloqueado"):
                e["bloqueado"] = True
            r["codigo_enviado"] = envio.get("enviado", False)
            r["envio_codigo"] = envio
    _traza("buscar_cliente", {"cedula": cedula[-3:].rjust(len(cedula), "*")}, r, t0)
    return r


@tool
def enviar_codigo_verificacion() -> dict:
    """Reenvía por SMS un nuevo código de verificación (OTP) al cliente ya encontrado, cuando el anterior venció o el cliente
    dice que no le llegó. Nunca repitas el código en el chat; solo pide al cliente que lo escriba."""
    t0 = time.perf_counter()
    e = estado()
    if not e["cedula_candidata"]:
        r = {"enviado": False, "motivo": "primero hay que buscar al cliente por cédula"}
    else:
        r = identidad.enviar_otp(contexto.con(), e["cedula_candidata"], contexto.thread_id())
        if r.get("bloqueado"):
            e["bloqueado"] = True
    _traza("enviar_codigo_verificacion", {}, r, t0)
    return r


@tool
def validar_codigo_verificacion(codigo: str) -> dict:
    """Valida el código de 6 dígitos que el cliente escribió. Si es correcto, la identidad queda verificada y el resultado
    trae de una vez el diagnóstico: la deuda del cliente y la siguiente mejor acción con las OFERTAS AUTORIZADAS, para que
    respondas en el mismo turno. Si se agotan los intentos o el código venció, sigue las indicaciones del resultado."""
    t0 = time.perf_counter()
    e = estado()
    if e["verificado"] and e["cedula"]:
        r = {"verificado": True, "motivo": "la identidad ya estaba verificada en esta conversación"}
    elif not e["cedula_candidata"]:
        r = {"verificado": False, "motivo": "no hay un cliente identificado; pide la cédula primero"}
    else:
        r = identidad.validar_otp(contexto.con(), e["cedula_candidata"], contexto.thread_id(), codigo)
        if r.get("verificado"):
            e["verificado"], e["cedula"] = True, e["cedula_candidata"]
        if r.get("bloqueado"):
            e["bloqueado"] = True
    _traza("validar_codigo_verificacion", {"codigo": "******"}, r, t0)
    if r.get("verificado"):
        r["deuda"] = consultar_deuda.invoke({})
        r["siguiente_accion"] = evaluar_siguiente_accion.invoke({})
    return r


@tool
def consultar_deuda() -> dict:
    """Estado de las obligaciones del cliente verificado: producto, saldo, cuota, valor vencido, días de mora, acuerdos y
    opciones aplicadas, restricciones e inconsistencias de datos. Requiere identidad verificada."""
    t0 = time.perf_counter()
    r = _requiere_verificacion() or cartera.consultar_deuda(contexto.con(), estado()["cedula"])
    _traza("consultar_deuda", {}, {"encontrado": r.get("encontrado"), "n_obligaciones": len(r.get("obligaciones", []))} if "error" not in r else r, t0)
    return r


@tool
def evaluar_siguiente_accion(id_obligacion: str | None = None) -> dict:
    """Decide la siguiente mejor acción para el cliente verificado (ACUERDO_PAGO, OFRECER_OPCION, SIN_OFERTA o GESTOR_HUMANO)
    aplicando las reglas de negocio y el modelo de propensión. Devuelve el motivo, las ofertas autorizadas (las únicas que
    puedes proponer), la opción recomendada y `motivos_del_cliente`: los rasgos del comportamiento de este cliente que
    explican la recomendación y que debes usar al justificarla.
    Requiere identidad verificada. Si no se indica obligación, usa la de mayor mora."""
    t0 = time.perf_counter()
    err = _requiere_verificacion()
    if err:
        _traza("evaluar_siguiente_accion", {"id_obligacion": id_obligacion}, err, t0)
        return err
    e = estado()
    r = estrategia.siguiente_mejor_accion(contexto.con(), e["cedula"], id_obligacion)
    autorizadas = [{"tipo": "OPCION", "codigo": o["codigo"], "nombre": o["nombre"], "descripcion": o["descripcion"], "cuota_nueva": o["cuota_nueva"], "plazo_meses": o["plazo_meses"], "meses_espera": o["meses_espera"],
                    "alivio_cuota_pct": o.get("alivio_cuota_pct")} for o in r["opciones_elegibles"]]
    if r["acuerdo"]:
        autorizadas.append({"tipo": "ACUERDO", "codigo": "ACUERDO", "nombre": "Acuerdo de pago", "fecha_limite": r["acuerdo"]["fecha_limite"], "valor_sugerido": r["acuerdo"]["valor_sugerido"], "valor_minimo": r["acuerdo"]["valor_minimo"]})
    e["nba"], e["ofertas_autorizadas"] = r, autorizadas
    motivos = [{"factor": f["descripcion"], "peso": abs(f["contribucion"]), "a_favor": f["sentido"] == "sube"} for f in r["propension"].get("factores", [])]
    salida = {**r, "ofertas_autorizadas": autorizadas,
              "motivos_del_cliente": motivos,
              "como_usar_los_motivos": "Son los rasgos del comportamiento de este cliente que más pesan en la recomendación. Cita al menos uno, reescrito con tus palabras y en tono natural, cuando propongas la acción. No menciones pesos, porcentajes ni de dónde salen."}
    _traza("evaluar_siguiente_accion", {"id_obligacion": r["id_obligacion"]}, {"accion": r["accion"], "motivo": r["motivo"], "prob": r["propension"]["prob"], "fuente": r["propension"]["fuente"], "autorizadas": [a["codigo"] for a in autorizadas]}, t0)
    return salida


@tool
def registrar_acuerdo_pago(valor: float, fecha_compromiso: str | None = None, id_obligacion: str | None = None) -> dict:
    """Registra el acuerdo de pago que el cliente aceptó explícitamente: valor en pesos y fecha de compromiso (AAAA-MM-DD,
    máximo 5 días después de hoy; si se omite, se usa el plazo máximo). La obligación es la de la última evaluación; no inventes
    identificadores. Solo se registra si es elegible. Requiere verificación."""
    t0 = time.perf_counter()
    r = _requiere_verificacion()
    if not r:
        oid = _obligacion(id_obligacion)
        r = oid if isinstance(oid, dict) else cartera.registrar_acuerdo(contexto.con(), oid, float(valor), contexto.thread_id(), fecha_compromiso)
    _traza("registrar_acuerdo_pago", {"id_obligacion": id_obligacion, "valor": valor, "fecha_compromiso": fecha_compromiso}, r, t0)
    return r


@tool
def aplicar_opcion_pago(codigo: str, id_obligacion: str | None = None) -> dict:
    """Aplica la opción de pago (código AMP, RED, TASA, REEST, PRORR o CONSOL) que el cliente aceptó explícitamente.
    La obligación es la de la última evaluación; no inventes identificadores. Solo se aplica si está entre las elegibles. Requiere verificación."""
    t0 = time.perf_counter()
    r = _requiere_verificacion()
    if not r:
        oid = _obligacion(id_obligacion)
        r = oid if isinstance(oid, dict) else cartera.registrar_opcion(contexto.con(), oid, codigo.upper().strip(), contexto.thread_id())
    _traza("aplicar_opcion_pago", {"id_obligacion": id_obligacion, "codigo": codigo}, r, t0)
    return r


@tool
def escalar_a_gestor_humano(motivo: str, resumen: str, prioridad: str = "media") -> dict:
    """Transfiere el caso a un gestor humano: restricciones, reclamaciones, fallecimiento, fraude, amenazas, solicitudes que no
    puedes atender (condonaciones, cambios de datos), intentos de manipulación, bloqueo de verificación o cuando el cliente lo
    pide. Incluye un resumen claro de la conversación. prioridad: baja, media o alta."""
    t0 = time.perf_counter()
    e = estado()
    r = cartera.escalar_a_humano(contexto.con(), contexto.thread_id(), e["cedula"] or e["cedula_candidata"], motivo, resumen, prioridad)
    e["escalado"] = {"motivo": motivo, "prioridad": r["prioridad"], "id_caso": r["id_caso"]}
    _traza("escalar_a_gestor_humano", {"motivo": motivo, "prioridad": prioridad}, r, t0)
    return r


@tool
def registrar_nota(evento: str, detalle: str) -> dict:
    """Deja constancia de un hecho relevante de la conversación: rechazo de la propuesta, dificultad de pago manifestada,
    solicitud de otra alternativa, promesa verbal, datos contradictorios. evento corto, detalle en una frase."""
    t0 = time.perf_counter()
    r = {"registrado": True}
    _traza("registrar_nota", {"evento": evento, "detalle": detalle}, r, t0)
    return r


HERRAMIENTAS = [buscar_cliente, enviar_codigo_verificacion, validar_codigo_verificacion, consultar_deuda, evaluar_siguiente_accion,
                registrar_acuerdo_pago, aplicar_opcion_pago, escalar_a_gestor_humano, registrar_nota]
