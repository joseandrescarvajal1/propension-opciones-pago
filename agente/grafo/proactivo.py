"""Gestión proactiva: dada una cédula, busca al cliente, llama al modelo, decide la siguiente mejor acción,
envía la plantilla de WhatsApp adecuada y abre el hilo (thread_id = cédula) para que el agente continúe.

Si la acción es GESTOR_HUMANO no se envía ninguna plantilla comercial: se crea el caso para el gestor.
"""

from __future__ import annotations

import time

from grafo.grafo import Conversador
from herramientas import contexto
from herramientas.cartera import escalar_a_humano
from herramientas.estrategia import siguiente_mejor_accion
from sandbox.db import fila, registrar_traza
from sandbox.whatsapp import enviar_plantilla


def gestionar_proactivo(conv: Conversador, cedula: str, id_obligacion: str | None = None) -> dict:
    t0 = time.perf_counter()
    con = conv.con
    thread_id = cedula
    contexto.fijar(thread_id, 0, con)
    c = fila(con, "SELECT cedula, nombre, telefono FROM clientes WHERE cedula = ?", (cedula,))
    if not c:
        return {"cedula": cedula, "accion": None, "enviado": False, "motivo": "cliente no encontrado"}
    nba = siguiente_mejor_accion(con, cedula, id_obligacion)
    registrar_traza(con, thread_id, 0, "proactivo", "siguiente_mejor_accion", {"accion": nba["accion"], "motivo": nba["motivo"], "prob": nba["propension"]["prob"], "fuente": nba["propension"]["fuente"],
                                                                                "plantilla": nba["plantilla"], "reglas": nba["reglas_aplicadas"]})
    salida = {"cedula": cedula, "thread_id": thread_id, "nombre": c["nombre"], "accion": nba["accion"], "motivo": nba["motivo"], "propension": nba["propension"]["prob"],
              "fuente_modelo": nba["propension"]["fuente"], "opcion_recomendada": (nba.get("opcion_recomendada") or {}).get("nombre"), "plantilla": nba["plantilla"]}
    if nba["accion"] == "GESTOR_HUMANO" or not nba["plantilla"]:
        r = escalar_a_humano(con, thread_id, cedula, nba["motivo"], f"Gestión proactiva: {nba['accion']}. {nba['motivo']}", "alta" if nba["requiere_gestor_humano"] else "media")
        salida.update({"enviado": False, "escalado": r, "motivo_no_envio": "sin contacto comercial; caso para gestor humano"})
    elif not c["telefono"]:
        r = escalar_a_humano(con, thread_id, cedula, "sin teléfono registrado", f"Gestión proactiva no enviada: {nba['accion']} ({nba['motivo']}). El cliente no tiene teléfono.", "media")
        salida.update({"enviado": False, "escalado": r, "motivo_no_envio": "el cliente no tiene teléfono registrado"})
    else:
        m = enviar_plantilla(con, thread_id, c["telefono"], nba["plantilla"], nombre=c["nombre"].split()[0], producto=nba["producto"].lower())
        conv.abrir_hilo_proactivo(thread_id, cedula, nba, m["texto"])
        salida.update({"enviado": True, "mensaje": m["texto"]})
    salida["latencia_ms"] = round((time.perf_counter() - t0) * 1000, 1)
    registrar_traza(con, thread_id, 0, "proactivo", "plantilla_enviada" if salida["enviado"] else "no_enviado", {k: salida.get(k) for k in ("accion", "plantilla", "motivo_no_envio")})
    return salida
