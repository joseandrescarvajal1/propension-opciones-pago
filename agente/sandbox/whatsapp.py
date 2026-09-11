"""WhatsApp y SMS simulados.

En producción este módulo se reemplazaría por el cliente de WhatsApp Business API (plantillas
aprobadas para iniciar conversaciones) y por el proveedor de SMS para el OTP. Aquí todo se escribe
en la tabla `mensajes` del sandbox y el front lo muestra como un teléfono.
"""

from __future__ import annotations

import sqlite3

from sandbox.db import ahora, filas, insertar

# Plantillas de inicio de conversación (en WhatsApp Business deben estar preaprobadas por Meta)
PLANTILLAS = {
    "inicio_acuerdo": ("Hola {nombre}, te escribe Bancolombia. Vemos que tu {producto} tiene una cuota pendiente y queremos ayudarte a ponerte al día "
                       "con un acuerdo de pago sencillo. Para continuar con seguridad, respóndenos con tu número de cédula y te enviaremos un código de verificación."),
    "inicio_opcion": ("Hola {nombre}, te escribe Bancolombia. Tenemos una alternativa preaprobada para aliviar la cuota de tu {producto}. "
                      "Para contártela con seguridad, respóndenos con tu número de cédula y te enviaremos un código de verificación."),
    "inicio_informativo": ("Hola {nombre}, te escribe Bancolombia. Queremos revisar contigo el estado de tu {producto}. "
                           "Para continuar con seguridad, respóndenos con tu número de cédula y te enviaremos un código de verificación."),
    "recordatorio_acuerdo": "Hola {nombre}, te recordamos tu compromiso de pago de {valor} para el {fecha}. Si necesitas ayuda, respóndenos por este medio.",
    "otp": "Bancolombia: tu código de verificación es {codigo}. Vence en 5 minutos. No lo compartas con nadie.",
}


def enviar_plantilla(con: sqlite3.Connection, thread_id: str, telefono: str, plantilla: str, **params) -> dict:
    """Envía una plantilla saliente (inicio proactivo). Devuelve el mensaje registrado."""
    if plantilla not in PLANTILLAS:
        raise ValueError(f"plantilla desconocida: {plantilla}")
    if not telefono:
        raise ValueError("el cliente no tiene teléfono registrado")
    texto = PLANTILLAS[plantilla].format(**params)
    return _guardar(con, thread_id, telefono, "whatsapp", "saliente", "plantilla", texto, plantilla)


def enviar_mensaje(con: sqlite3.Connection, thread_id: str, telefono: str, texto: str, direccion: str = "saliente") -> dict:
    return _guardar(con, thread_id, telefono, "whatsapp", direccion, "texto", texto)


def enviar_sms_otp(con: sqlite3.Connection, thread_id: str, telefono: str, codigo: str) -> dict:
    if not telefono:
        raise ValueError("el cliente no tiene teléfono registrado")
    return _guardar(con, thread_id, telefono, "sms", "saliente", "otp", PLANTILLAS["otp"].format(codigo=codigo), "otp")


def bandeja(con: sqlite3.Connection, thread_id: str, canal: str | None = None) -> list[dict]:
    """Conversación completa de un hilo, en orden. `canal` filtra whatsapp o sms."""
    if canal:
        return filas(con, "SELECT * FROM mensajes WHERE thread_id = ? AND canal = ? ORDER BY id", (thread_id, canal))
    return filas(con, "SELECT * FROM mensajes WHERE thread_id = ? ORDER BY id", (thread_id,))


def _guardar(con, thread_id, telefono, canal, direccion, tipo, texto, plantilla=None) -> dict:
    datos = {"thread_id": thread_id, "telefono": telefono, "canal": canal, "direccion": direccion, "tipo": tipo, "plantilla": plantilla, "texto": texto, "creado": ahora()}
    datos["id"] = insertar(con, "mensajes", datos)
    return datos
