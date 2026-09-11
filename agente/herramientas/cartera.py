"""Consulta de cartera y reglas de negocio de elegibilidad (deterministas).

Reglas mínimas del enunciado, más las definidas por el candidato:
  R1  Máximo 3 opciones de pago preaprobadas por obligación al mes; solo se ofrecen las vigentes.
  R2  Tras aplicar una opción, la obligación espera 3 o 4 meses (según la opción) antes de otra.
  R3  Con una restricción activa (jurídica, fraude, fallecido, reclamación, no contactar) no se
      ofrece nada y el caso pasa a un gestor humano.
  R4  El acuerdo de pago (compromiso de pagar en máximo 5 días) se puede ofrecer en cualquier etapa
      siempre que no haya una opción aceptada en periodo de espera ni restricción.
  R5  No se ofrece un nuevo acuerdo si hay uno vigente, ni si el cliente incumplió uno en los
      últimos 30 días (en ese caso se evalúan opciones o se escala).
  R6  Solo se aplica una opción por obligación al mes.
"""

from __future__ import annotations

import sqlite3
from datetime import date, timedelta

from sandbox.db import HOY, ahora, fila, filas, insertar

ACUERDO_PLAZO_DIAS = 5
MAX_OPCIONES_MES = 3
DIAS_REINCIDENCIA_ACUERDO = 30
RESTRICCIONES_HUMANO = {"juridica", "fraude", "fallecido", "reclamacion", "no_contactar"}


def _hoy() -> date:
    return date.fromisoformat(HOY)


def _sumar_meses(d: date, meses: int) -> date:
    m = d.month - 1 + meses
    return date(d.year + m // 12, m % 12 + 1, min(d.day, 28))


def consultar_deuda(con: sqlite3.Connection, cedula: str) -> dict:
    """Estado de las obligaciones del cliente (solo tras verificar identidad)."""
    c = fila(con, "SELECT cedula, nombre, segmento FROM clientes WHERE cedula = ?", (cedula,))
    if not c:
        return {"encontrado": False}
    obls = filas(con, "SELECT id_obligacion, producto, saldo_capital, valor_cuota, valor_vencido, dias_mora, etapa_mora FROM obligaciones WHERE cedula = ?", (cedula,))
    for o in obls:
        o["acuerdos"] = filas(con, "SELECT fecha_acuerdo, fecha_compromiso, valor, estado FROM acuerdos WHERE id_obligacion = ? ORDER BY id DESC LIMIT 3", (o["id_obligacion"],))
        o["opciones_aplicadas"] = filas(con, "SELECT codigo, nombre, fecha_aplicacion, meses_espera FROM opciones_aplicadas WHERE id_obligacion = ? ORDER BY id DESC LIMIT 3", (o["id_obligacion"],))
        o["inconsistencias"] = _inconsistencias(o)
    return {"encontrado": True, "nombre": c["nombre"], "segmento": c["segmento"], "fecha_consulta": HOY, "obligaciones": obls,
            "restricciones": filas(con, "SELECT tipo, detalle FROM restricciones WHERE cedula = ? AND activa = 1", (cedula,))}


def _inconsistencias(o: dict) -> list[str]:
    out = []
    if o["dias_mora"] == 0 and o["valor_vencido"] > 0:
        out.append("0 días de mora pero valor vencido mayor que cero")
    if o["dias_mora"] > 0 and o["valor_vencido"] == 0:
        out.append("días de mora sin valor vencido")
    if o["valor_cuota"] <= 0 or o["saldo_capital"] <= 0:
        out.append("cuota o saldo no positivos")
    return out


def evaluar_elegibilidad(con: sqlite3.Connection, id_obligacion: str) -> dict:
    """Aplica R1 a R6 y devuelve qué se puede ofrecer y por qué. Es la única fuente de ofertas autorizadas."""
    o = fila(con, "SELECT * FROM obligaciones WHERE id_obligacion = ?", (id_obligacion,))
    if not o:
        return {"encontrado": False, "id_obligacion": id_obligacion, "opciones_elegibles": [], "acuerdo": {"elegible": False, "motivo": "obligación no encontrada"}, "reglas_aplicadas": []}
    hoy = _hoy()
    reglas: list[str] = []
    restr = [r["tipo"] for r in filas(con, "SELECT tipo FROM restricciones WHERE cedula = ? AND activa = 1", (o["cedula"],))]
    bloqueo_humano = [r for r in restr if r in RESTRICCIONES_HUMANO]

    # R2: periodo de espera por opción aplicada
    en_espera = None
    for a in filas(con, "SELECT codigo, nombre, fecha_aplicacion, meses_espera FROM opciones_aplicadas WHERE id_obligacion = ? ORDER BY fecha_aplicacion DESC", (id_obligacion,)):
        hasta = _sumar_meses(date.fromisoformat(a["fecha_aplicacion"]), a["meses_espera"])
        if hasta > hoy:
            en_espera = {"opcion": a["nombre"], "codigo": a["codigo"], "fecha_aplicacion": a["fecha_aplicacion"], "espera_hasta": hasta.isoformat()}
            break
    aplicadas_mes = filas(con, "SELECT 1 FROM opciones_aplicadas WHERE id_obligacion = ? AND substr(fecha_aplicacion, 1, 7) = ?", (id_obligacion, HOY[:7]))

    # R1: opciones preaprobadas vigentes (máximo 3)
    pre = filas(con, "SELECT codigo, nombre, descripcion, cuota_nueva, plazo_meses, meses_espera, vigente_hasta FROM opciones_preaprobadas WHERE id_obligacion = ? ORDER BY id", (id_obligacion,))
    elegibles, no_elegibles = [], []
    for p in pre:
        if p["vigente_hasta"] < HOY:
            no_elegibles.append({"codigo": p["codigo"], "nombre": p["nombre"], "motivo": "preaprobación vencida"}); continue
        if bloqueo_humano:
            no_elegibles.append({"codigo": p["codigo"], "nombre": p["nombre"], "motivo": f"restricción activa: {', '.join(bloqueo_humano)} (R3)"}); continue
        if en_espera:
            no_elegibles.append({"codigo": p["codigo"], "nombre": p["nombre"], "motivo": f"opción {en_espera['opcion']} aplicada el {en_espera['fecha_aplicacion']}; espera hasta {en_espera['espera_hasta']} (R2)"}); continue
        if aplicadas_mes:
            no_elegibles.append({"codigo": p["codigo"], "nombre": p["nombre"], "motivo": "ya se aplicó una opción este mes (R6)"}); continue
        if len(elegibles) >= MAX_OPCIONES_MES:
            no_elegibles.append({"codigo": p["codigo"], "nombre": p["nombre"], "motivo": "supera el máximo de 3 opciones por mes (R1)"}); continue
        elegibles.append({**p, "alivio_cuota_pct": None if p["cuota_nueva"] is None else round(100 * (1 - p["cuota_nueva"] / o["valor_cuota"]), 1)})
    reglas.append(f"R1: {len(pre)} preaprobadas, {len(elegibles)} elegibles")
    if en_espera:
        reglas.append(f"R2: en espera hasta {en_espera['espera_hasta']}")
    if bloqueo_humano:
        reglas.append(f"R3: restricción {', '.join(bloqueo_humano)}; sin ofertas, gestor humano")

    # R4 y R5: acuerdo de pago
    acuerdos = filas(con, "SELECT fecha_acuerdo, fecha_compromiso, estado FROM acuerdos WHERE id_obligacion = ? ORDER BY id DESC", (id_obligacion,))
    vigente = [a for a in acuerdos if a["estado"] == "vigente" and a["fecha_compromiso"] >= HOY]
    incumplido_reciente = [a for a in acuerdos if a["estado"] == "incumplido" and date.fromisoformat(a["fecha_compromiso"]) >= hoy - timedelta(days=DIAS_REINCIDENCIA_ACUERDO)]
    if bloqueo_humano:
        acuerdo = {"elegible": False, "motivo": "restricción activa (R3)"}
    elif en_espera:
        acuerdo = {"elegible": False, "motivo": "tiene una opción de pago aceptada en periodo de espera (R4)"}
    elif vigente:
        acuerdo = {"elegible": False, "motivo": f"ya tiene un acuerdo vigente con compromiso el {vigente[0]['fecha_compromiso']} (R5)"}
    elif incumplido_reciente:
        acuerdo = {"elegible": False, "motivo": f"incumplió el acuerdo del {incumplido_reciente[0]['fecha_acuerdo']} hace menos de {DIAS_REINCIDENCIA_ACUERDO} días (R5)", "reincidente": True}
    elif o["valor_vencido"] <= 0:
        acuerdo = {"elegible": False, "motivo": "no hay valor vencido que acordar"}
    else:
        acuerdo = {"elegible": True, "motivo": "sin opción en espera, sin acuerdo vigente ni incumplido reciente, sin restricción (R4)", "plazo_dias": ACUERDO_PLAZO_DIAS,
                   "fecha_limite": (hoy + timedelta(days=ACUERDO_PLAZO_DIAS)).isoformat(), "valor_sugerido": o["valor_vencido"], "valor_minimo": round(o["valor_cuota"], -3)}
    reglas.append(f"R4/R5: acuerdo {'elegible' if acuerdo['elegible'] else 'no elegible: ' + acuerdo['motivo']}")
    return {"encontrado": True, "id_obligacion": id_obligacion, "producto": o["producto"], "dias_mora": o["dias_mora"], "etapa_mora": o["etapa_mora"], "valor_vencido": o["valor_vencido"],
            "valor_cuota": o["valor_cuota"], "restricciones": restr, "requiere_gestor_humano": bool(bloqueo_humano), "en_espera": en_espera,
            "opciones_elegibles": elegibles, "opciones_no_elegibles": no_elegibles, "acuerdo": acuerdo, "reglas_aplicadas": reglas}


def registrar_acuerdo(con: sqlite3.Connection, id_obligacion: str, valor: float, thread_id: str, fecha_compromiso: str | None = None) -> dict:
    """Registra un acuerdo de pago solo si la elegibilidad lo permite y el valor y la fecha cumplen las reglas."""
    e = evaluar_elegibilidad(con, id_obligacion)
    if not e["acuerdo"]["elegible"]:
        return {"registrado": False, "motivo": e["acuerdo"]["motivo"]}
    hoy = _hoy()
    fecha_c = date.fromisoformat(fecha_compromiso) if fecha_compromiso else hoy + timedelta(days=ACUERDO_PLAZO_DIAS)
    if not (hoy < fecha_c <= hoy + timedelta(days=ACUERDO_PLAZO_DIAS)):
        return {"registrado": False, "motivo": f"la fecha de compromiso debe estar entre mañana y {ACUERDO_PLAZO_DIAS} días después de hoy ({HOY})"}
    if valor < e["acuerdo"]["valor_minimo"]:
        return {"registrado": False, "motivo": f"el valor mínimo del acuerdo es {e['acuerdo']['valor_minimo']:,.0f}"}
    rid = insertar(con, "acuerdos", {"id_obligacion": id_obligacion, "fecha_acuerdo": HOY, "fecha_compromiso": fecha_c.isoformat(), "valor": float(valor), "estado": "vigente", "canal": "agente", "thread_id": thread_id})
    return {"registrado": True, "id_acuerdo": rid, "fecha_compromiso": fecha_c.isoformat(), "valor": float(valor), "registrado_en": ahora()}


def registrar_opcion(con: sqlite3.Connection, id_obligacion: str, codigo: str, thread_id: str) -> dict:
    """Aplica una opción de pago solo si está entre las elegibles en este momento."""
    e = evaluar_elegibilidad(con, id_obligacion)
    op = next((p for p in e["opciones_elegibles"] if p["codigo"] == codigo), None)
    if not op:
        motivo = next((p["motivo"] for p in e["opciones_no_elegibles"] if p["codigo"] == codigo), "la opción no está preaprobada para esta obligación")
        return {"registrado": False, "motivo": motivo}
    rid = insertar(con, "opciones_aplicadas", {"id_obligacion": id_obligacion, "codigo": codigo, "nombre": op["nombre"], "fecha_aplicacion": HOY, "meses_espera": op["meses_espera"], "canal": "agente", "thread_id": thread_id})
    return {"registrado": True, "id_aplicacion": rid, "opcion": op["nombre"], "cuota_nueva": op["cuota_nueva"], "espera_hasta": _sumar_meses(_hoy(), op["meses_espera"]).isoformat(), "registrado_en": ahora()}


def escalar_a_humano(con: sqlite3.Connection, thread_id: str, cedula: str | None, motivo: str, resumen: str, prioridad: str = "media") -> dict:
    """Crea el caso para el gestor humano con el resumen de la conversación."""
    prioridad = prioridad if prioridad in ("baja", "media", "alta") else "media"
    rid = insertar(con, "escalamientos", {"thread_id": thread_id, "cedula": cedula, "motivo": motivo, "resumen": resumen, "prioridad": prioridad, "creado": ahora()})
    return {"escalado": True, "id_caso": rid, "prioridad": prioridad, "mensaje_cliente": "Un gestor de Bancolombia se comunicará contigo en el siguiente día hábil."}
