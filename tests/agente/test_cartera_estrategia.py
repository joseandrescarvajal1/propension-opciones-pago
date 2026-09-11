"""Reglas de negocio (elegibilidad, registros) y siguiente mejor acción."""

import pytest
from herramientas import cartera, estrategia


def _pred(prob):
    def f(con, oid, k=5):
        return {"disponible": True, "prob_uno": prob, "var_rpta_alt": int(prob >= 0.33), "umbral": 0.33, "factores": [], "version_modelo": "prueba", "fuente": "prueba", "scores_banco": {}}
    return f


# ------------------------------------------------------------ elegibilidad
def test_r1_maximo_tres_opciones(sandbox):
    e = cartera.evaluar_elegibilidad(sandbox["con"], sandbox["clientes"]["varias"])
    assert len(e["opciones_elegibles"]) == 3 and any("R1" in x["motivo"] for x in e["opciones_no_elegibles"])


def test_r2_espera_tras_opcion_aplicada(sandbox):
    e = cartera.evaluar_elegibilidad(sandbox["con"], sandbox["clientes"]["espera"])
    assert e["en_espera"] and e["en_espera"]["espera_hasta"] > "2024-01-15"
    assert e["opciones_elegibles"] == [] and all("R2" in x["motivo"] for x in e["opciones_no_elegibles"])
    assert e["acuerdo"]["elegible"] is False and "R4" in e["acuerdo"]["motivo"]


def test_r3_restriccion_sin_ofertas(sandbox):
    e = cartera.evaluar_elegibilidad(sandbox["con"], sandbox["clientes"]["restriccion"])
    assert e["requiere_gestor_humano"] and e["opciones_elegibles"] == [] and e["acuerdo"]["elegible"] is False


def test_r4_acuerdo_elegible_en_mora_temprana(sandbox):
    e = cartera.evaluar_elegibilidad(sandbox["con"], sandbox["clientes"]["temprana"])
    a = e["acuerdo"]
    assert a["elegible"] and a["plazo_dias"] == 5 and a["fecha_limite"] == "2024-01-20" and a["valor_sugerido"] == 500_000.0


def test_r5_incumplido_reciente_y_vigente(sandbox):
    e = cartera.evaluar_elegibilidad(sandbox["con"], sandbox["clientes"]["incumplido"])
    assert e["acuerdo"]["elegible"] is False and e["acuerdo"].get("reincidente") and len(e["opciones_elegibles"]) == 2
    e2 = cartera.evaluar_elegibilidad(sandbox["con"], sandbox["clientes"]["acuerdo_vigente"])
    assert e2["acuerdo"]["elegible"] is False and "vigente" in e2["acuerdo"]["motivo"]


def test_obligacion_inexistente(sandbox):
    e = cartera.evaluar_elegibilidad(sandbox["con"], "no#existe#0")
    assert e["encontrado"] is False and e["opciones_elegibles"] == []


# ---------------------------------------------------------------- registros
def test_registrar_acuerdo_valida_fecha_y_valor(sandbox):
    con, oid = sandbox["con"], sandbox["clientes"]["temprana"]
    assert cartera.registrar_acuerdo(con, oid, 500_000, "h", "2024-01-25")["registrado"] is False   # más de 5 días
    assert cartera.registrar_acuerdo(con, oid, 500_000, "h", "2024-01-15")["registrado"] is False   # hoy no vale
    assert cartera.registrar_acuerdo(con, oid, 100_000, "h")["registrado"] is False                 # menor que el mínimo
    r = cartera.registrar_acuerdo(con, oid, 500_000, "h", "2024-01-19")
    assert r["registrado"] and r["fecha_compromiso"] == "2024-01-19"
    # R6/R5: ya hay un acuerdo vigente, no se registra otro
    assert cartera.registrar_acuerdo(con, oid, 500_000, "h")["registrado"] is False


def test_registrar_acuerdo_no_elegible(sandbox):
    assert cartera.registrar_acuerdo(sandbox["con"], sandbox["clientes"]["restriccion"], 500_000, "h")["registrado"] is False


def test_registrar_opcion_solo_elegible(sandbox):
    con = sandbox["con"]
    assert cartera.registrar_opcion(con, sandbox["clientes"]["espera"], "AMP", "h")["registrado"] is False
    assert cartera.registrar_opcion(con, sandbox["clientes"]["varias"], "PRORR", "h")["registrado"] is False   # no preaprobada
    r = cartera.registrar_opcion(con, sandbox["clientes"]["varias"], "AMP", "h")
    assert r["registrado"] and r["espera_hasta"] == "2024-04-15"
    # después de aplicar, la obligación queda en espera y no admite otra
    assert cartera.registrar_opcion(con, sandbox["clientes"]["varias"], "RED", "h")["registrado"] is False


def test_consultar_deuda_inconsistencias(sandbox):
    con = sandbox["con"]
    con.execute("UPDATE obligaciones SET dias_mora = 0 WHERE cedula = '1000000001'"); con.commit()
    d = cartera.consultar_deuda(con, "1000000001")
    assert d["encontrado"] and d["obligaciones"][0]["inconsistencias"]
    assert cartera.consultar_deuda(con, "0")["encontrado"] is False


# ------------------------------------------------------- siguiente mejor acción
@pytest.mark.parametrize("cliente,prob,accion,regla", [
    ("restriccion", 0.9, "GESTOR_HUMANO", "regla 1"),
    ("espera", 0.9, "SIN_OFERTA", "regla 2"),
    ("temprana", 0.9, "ACUERDO_PAGO", "regla 3"),
    ("varias", 0.9, "OFRECER_OPCION", "regla 4"),
    ("varias", 0.1, "ACUERDO_PAGO", "regla 5"),
    ("incumplido", 0.1, "OFRECER_OPCION", "regla 5"),
    ("sin_nada", 0.9, "GESTOR_HUMANO", "regla 7"),
    ("acuerdo_vigente", 0.9, "SIN_OFERTA", "regla 7"),
])
def test_siguiente_mejor_accion(sandbox, monkeypatch, cliente, prob, accion, regla):
    monkeypatch.setattr(estrategia, "predecir_propension", _pred(prob))
    ced = sandbox["con"].execute("SELECT cedula FROM obligaciones WHERE id_obligacion = ?", (sandbox["clientes"][cliente],)).fetchone()[0]
    r = estrategia.siguiente_mejor_accion(sandbox["con"], ced)
    assert r["accion"] == accion and regla in r["motivo"]
    if accion == "OFRECER_OPCION":
        assert r["opcion_recomendada"]["codigo"] in {o["codigo"] for o in r["opciones_elegibles"]}
    if accion in ("GESTOR_HUMANO",) and cliente == "restriccion":
        assert r["plantilla"] is None


def test_mejor_opcion_por_etapa():
    ops = [{"codigo": "TASA", "nombre": "t", "cuota_nueva": 85, "meses_espera": 3, "alivio_cuota_pct": 15.0}, {"codigo": "REEST", "nombre": "r", "cuota_nueva": 55, "meses_espera": 4, "alivio_cuota_pct": 45.0}]
    assert estrategia.mejor_opcion(ops, "temprana")["codigo"] == "TASA"
    assert estrategia.mejor_opcion(ops, "avanzada")["codigo"] == "REEST"
    assert estrategia.mejor_opcion([], "media") is None


def test_modelo_no_disponible_usa_score_del_banco(sandbox, monkeypatch):
    monkeypatch.setenv("MODELO_MODO", "caido")
    r = estrategia.siguiente_mejor_accion(sandbox["con"], "1000000002")
    assert r["propension"]["disponible"] is False and r["propension"]["fuente"] == "score_banco" and r["propension"]["prob"] == 0.7
    assert r["accion"] == "OFRECER_OPCION"
