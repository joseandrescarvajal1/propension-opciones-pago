"""Verificación de identidad: búsqueda por cédula y OTP.

Reglas (deterministas, no las decide el LLM):
  - El OTP tiene 6 dígitos, vence a los 5 minutos y se guarda con hash (nunca en claro ni en el prompt).
  - Máximo 3 intentos por código; al tercero fallido el código queda bloqueado.
  - Máximo 3 códigos por cédula en una hora; al superarlo la cédula queda bloqueada y se escala.
  - El hilo solo queda verificado cuando el código coincide dentro de la vigencia.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone

from sandbox.db import ahora, fila, filas, insertar
from sandbox.whatsapp import enviar_sms_otp

OTP_VIGENCIA_MIN = 5
OTP_MAX_INTENTOS = 3
OTP_MAX_POR_HORA = 3


def _hash(codigo: str, cedula: str) -> str:
    sal = os.environ.get("OTP_SAL", "sandbox-otp")
    return hashlib.sha256(f"{sal}:{cedula}:{codigo}".encode()).hexdigest()


def _ocultar(cedula: str) -> str:
    return "*" * (len(cedula) - 3) + cedula[-3:]


def buscar_cliente(con: sqlite3.Connection, cedula: str) -> dict:
    """Busca al cliente por cédula. Devuelve solo lo necesario antes de verificar: si existe, nombre de pila
    y teléfono enmascarado. Nunca devuelve saldos ni ofertas en este paso."""
    cedula = "".join(ch for ch in str(cedula) if ch.isdigit())
    if not cedula:
        return {"encontrado": False, "motivo": "cédula vacía o sin dígitos"}
    c = fila(con, "SELECT cedula, nombre, telefono FROM clientes WHERE cedula = ?", (cedula,))
    if not c:
        return {"encontrado": False, "cedula": _ocultar(cedula), "motivo": "no existe un cliente con esa cédula"}
    tel = c["telefono"]
    return {"encontrado": True, "cedula": cedula, "nombre_pila": c["nombre"].split()[0], "telefono_enmascarado": (tel[:6] + "****" + tel[-3:]) if tel else None, "tiene_telefono": bool(tel)}


def enviar_otp(con: sqlite3.Connection, cedula: str, thread_id: str) -> dict:
    """Genera y envía un OTP por SMS al teléfono registrado. Devuelve el estado, nunca el código."""
    c = fila(con, "SELECT cedula, telefono FROM clientes WHERE cedula = ?", (cedula,))
    if not c:
        return {"enviado": False, "motivo": "cliente no encontrado"}
    if not c["telefono"]:
        return {"enviado": False, "motivo": "el cliente no tiene teléfono registrado; no es posible verificar por OTP", "escalar": True}
    hace_1h = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat(timespec="seconds")
    recientes = filas(con, "SELECT id, bloqueado FROM otp WHERE cedula = ? AND creado >= ?", (cedula, hace_1h))
    if len(recientes) >= OTP_MAX_POR_HORA or any(r["bloqueado"] for r in recientes):
        return {"enviado": False, "motivo": f"se alcanzó el máximo de {OTP_MAX_POR_HORA} códigos por hora o hay un bloqueo vigente", "bloqueado": True, "escalar": True}
    con.execute("UPDATE otp SET usado = 1 WHERE cedula = ? AND usado = 0", (cedula,))  # invalida códigos anteriores
    codigo = f"{secrets.randbelow(1_000_000):06d}"
    creado = datetime.now(timezone.utc)
    insertar(con, "otp", {"cedula": cedula, "thread_id": thread_id, "codigo_hash": _hash(codigo, cedula), "creado": creado.isoformat(timespec="seconds"),
                          "vence": (creado + timedelta(minutes=OTP_VIGENCIA_MIN)).isoformat(timespec="seconds")})
    enviar_sms_otp(con, thread_id, c["telefono"], codigo)
    return {"enviado": True, "canal": "sms", "vigencia_min": OTP_VIGENCIA_MIN, "intentos_permitidos": OTP_MAX_INTENTOS, "codigos_restantes_hora": OTP_MAX_POR_HORA - len(recientes) - 1}


def validar_otp(con: sqlite3.Connection, cedula: str, thread_id: str, codigo: str) -> dict:
    """Valida el código. Devuelve verificado True/False con el motivo y si procede escalar."""
    codigo = "".join(ch for ch in str(codigo) if ch.isdigit())
    o = fila(con, "SELECT * FROM otp WHERE cedula = ? AND usado = 0 ORDER BY id DESC LIMIT 1", (cedula,))
    if not o:
        return {"verificado": False, "motivo": "no hay un código vigente; hay que enviar uno nuevo"}
    if o["bloqueado"]:
        return {"verificado": False, "motivo": "código bloqueado por intentos fallidos", "bloqueado": True, "escalar": True}
    if ahora() > o["vence"]:
        con.execute("UPDATE otp SET usado = 1 WHERE id = ?", (o["id"],)); con.commit()
        return {"verificado": False, "motivo": "el código venció; hay que enviar uno nuevo", "vencido": True}
    if len(codigo) == 6 and hmac.compare_digest(_hash(codigo, cedula), o["codigo_hash"]):
        con.execute("UPDATE otp SET usado = 1, intentos = intentos + 1 WHERE id = ?", (o["id"],)); con.commit()
        return {"verificado": True, "motivo": "código correcto"}
    intentos = o["intentos"] + 1
    bloqueado = int(intentos >= OTP_MAX_INTENTOS)
    con.execute("UPDATE otp SET intentos = ?, bloqueado = ?, usado = ? WHERE id = ?", (intentos, bloqueado, bloqueado, o["id"])); con.commit()
    if bloqueado:
        return {"verificado": False, "motivo": f"código incorrecto; se agotaron los {OTP_MAX_INTENTOS} intentos y la verificación queda bloqueada", "bloqueado": True, "escalar": True}
    return {"verificado": False, "motivo": "código incorrecto", "intentos_restantes": OTP_MAX_INTENTOS - intentos}


def otp_vigente_sandbox(con: sqlite3.Connection, cedula: str) -> dict | None:
    """Solo para el front del sandbox: último SMS de OTP enviado a la cédula (simula mirar el teléfono)."""
    c = fila(con, "SELECT telefono FROM clientes WHERE cedula = ?", (cedula,))
    if not c or not c["telefono"]:
        return None
    return fila(con, "SELECT texto, creado FROM mensajes WHERE telefono = ? AND tipo = 'otp' ORDER BY id DESC LIMIT 1", (c["telefono"],))
