"""Siguiente mejor acción (NBA) por obligación. Combina elegibilidad (reglas), etapa de mora y la
probabilidad del modelo de la Parte 1.

Acciones posibles:
    GESTOR_HUMANO   restricción activa o caso que el agente no debe gestionar
    SIN_OFERTA      no hay nada elegible (informar, escuchar, registrar; sin ofertas no autorizadas)
    ACUERDO_PAGO    compromiso de pago en máximo 5 días (gestión temprana o cuando es la mejor salida)
    OFRECER_OPCION  ofrecer la mejor opción de pago elegible y explicarla

Estrategia definida por el candidato (documentada en docs/plan_agentes.md):
    1. Restricción activa -> GESTOR_HUMANO, sin contacto comercial.
    2. Opción en periodo de espera -> SIN_OFERTA (recordar la nueva cuota).
    3. Mora temprana (<= 30 días) con acuerdo elegible -> ACUERDO_PAGO; la mejor opción queda como alternativa
       si el modelo indica propensión alta (prob >= umbral).
    4. Opciones elegibles y prob >= umbral -> OFRECER_OPCION (la mejor); acuerdo como alternativa si es elegible.
    5. Opciones elegibles y prob < umbral -> ACUERDO_PAGO si es elegible (menor costo), si no OFRECER_OPCION.
    6. Sin opciones y acuerdo elegible -> ACUERDO_PAGO.
    7. Nada elegible -> GESTOR_HUMANO si reincidió o la mora es avanzada; si no, SIN_OFERTA.
"""

from __future__ import annotations

import sqlite3

from herramientas.cartera import evaluar_elegibilidad
from herramientas.modelo import predecir_propension
from sandbox.db import filas

MORA_TEMPRANA_MAX = 30
# Preferencia de opción por etapa de mora (mayor = más adecuada); se combina con el alivio de cuota
PREFERENCIA = {"temprana": {"TASA": 3, "AMP": 2, "RED": 2, "PRORR": 1, "REEST": 0, "CONSOL": 1},
               "media": {"AMP": 3, "RED": 3, "TASA": 1, "PRORR": 2, "REEST": 1, "CONSOL": 2},
               "avanzada": {"REEST": 3, "CONSOL": 3, "AMP": 2, "RED": 1, "PRORR": 1, "TASA": 0}}


def mejor_opcion(opciones: list[dict], etapa: str) -> dict | None:
    if not opciones:
        return None
    pref = PREFERENCIA.get(etapa, PREFERENCIA["media"])

    def puntaje(o):
        alivio = (o.get("alivio_cuota_pct") or 0) / 100
        return pref.get(o["codigo"], 1) + alivio - 0.1 * (o["meses_espera"] - 3)
    orden = sorted(opciones, key=puntaje, reverse=True)
    m = dict(orden[0])
    m["motivo_eleccion"] = f"la más adecuada para mora {etapa}: alivio de cuota {m.get('alivio_cuota_pct')} % y periodo de espera de {m['meses_espera']} meses"
    m["alternativas"] = [{"codigo": o["codigo"], "nombre": o["nombre"], "cuota_nueva": o["cuota_nueva"]} for o in orden[1:]]
    return m


def siguiente_mejor_accion(con: sqlite3.Connection, cedula: str, id_obligacion: str | None = None) -> dict:
    """Decide la acción para la obligación (o para la de mayor mora del cliente)."""
    obls = filas(con, "SELECT id_obligacion, dias_mora FROM obligaciones WHERE cedula = ? ORDER BY dias_mora DESC", (cedula,))
    if not obls:
        return {"accion": "GESTOR_HUMANO", "motivo": "cliente sin obligaciones registradas", "id_obligacion": None}
    oid = id_obligacion or obls[0]["id_obligacion"]
    e = evaluar_elegibilidad(con, oid)
    pred = predecir_propension(con, oid)
    if pred.get("disponible"):
        prob, umbral, fuente = pred["prob_uno"], pred["umbral"], pred["fuente"]
    else:  # respaldo: score de propensión del banco; si tampoco hay, se asume baja
        sb = pred.get("scores_banco", {}).get("prob_propension_banco_t1")
        prob, umbral, fuente = (sb, 0.5, "score_banco") if sb is not None else (None, 0.5, "sin_modelo")
    alta = prob is not None and prob >= umbral
    ac, ops = e["acuerdo"], e["opciones_elegibles"]
    mejor = mejor_opcion(ops, e["etapa_mora"])
    plantilla = "inicio_informativo"
    if e["requiere_gestor_humano"]:
        accion, motivo, plantilla = "GESTOR_HUMANO", f"restricción activa: {', '.join(e['restricciones'])}; sin contacto comercial (regla 1)", None
    elif e["en_espera"]:
        accion, motivo = "SIN_OFERTA", f"opción {e['en_espera']['opcion']} en periodo de espera hasta {e['en_espera']['espera_hasta']} (regla 2)"
    elif e["dias_mora"] <= MORA_TEMPRANA_MAX and ac["elegible"]:
        accion, motivo, plantilla = "ACUERDO_PAGO", f"mora temprana ({e['dias_mora']} días) y acuerdo elegible; compromiso de pago en {ac['plazo_dias']} días (regla 3)", "inicio_acuerdo"
    elif ops and alta:
        accion, motivo, plantilla = "OFRECER_OPCION", f"propensión {prob:.2f} >= umbral {umbral:.2f} y {len(ops)} opción(es) elegible(s); se ofrece {mejor['nombre']} (regla 4)", "inicio_opcion"
    elif ops and ac["elegible"]:
        accion, motivo, plantilla = "ACUERDO_PAGO", f"propensión {'sin dato' if prob is None else f'{prob:.2f}'} bajo el umbral; se prioriza el acuerdo de pago y la opción queda como alternativa (regla 5)", "inicio_acuerdo"
    elif ops:
        accion, motivo, plantilla = "OFRECER_OPCION", f"propensión {'sin dato' if prob is None else f'{prob:.2f}'} bajo el umbral y sin acuerdo elegible; se ofrece {mejor['nombre']} (regla 5)", "inicio_opcion"
    elif ac["elegible"]:
        accion, motivo, plantilla = "ACUERDO_PAGO", f"sin opciones elegibles; acuerdo de pago en {ac['plazo_dias']} días (regla 6)", "inicio_acuerdo"
    elif ac.get("reincidente") or e["etapa_mora"] == "avanzada":
        accion, motivo, plantilla = "GESTOR_HUMANO", f"nada elegible y {'acuerdo incumplido reciente' if ac.get('reincidente') else 'mora avanzada'}; requiere gestor (regla 7)", "inicio_informativo"
    else:
        accion, motivo = "SIN_OFERTA", f"nada elegible: {ac['motivo']} (regla 7)"
    return {"accion": accion, "motivo": motivo, "id_obligacion": oid, "producto": e["producto"], "dias_mora": e["dias_mora"], "etapa_mora": e["etapa_mora"],
            "plantilla": plantilla, "propension": {"prob": prob, "umbral": umbral, "fuente": fuente, "alta": alta, "factores": pred.get("factores", []), "disponible": pred.get("disponible", False),
                                                    "motivo_no_disponible": pred.get("motivo")},
            "acuerdo": ac if ac["elegible"] else None, "opcion_recomendada": mejor if accion == "OFRECER_OPCION" or (mejor and alta) else None,
            "opciones_elegibles": ops, "opciones_no_elegibles": e["opciones_no_elegibles"], "reglas_aplicadas": e["reglas_aplicadas"], "requiere_gestor_humano": accion == "GESTOR_HUMANO"}
