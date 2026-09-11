"""Seguridad de la verificación de identidad (OTP)."""

from datetime import datetime, timedelta, timezone

from conftest import leer_otp
from herramientas import identidad


def test_buscar_cliente_no_revela_datos(sandbox):
    con = sandbox["con"]
    r = identidad.buscar_cliente(con, "1000000001")
    assert r["encontrado"] and r["nombre_pila"] == "Cliente" and "****" in r["telefono_enmascarado"]
    assert not {"saldo_capital", "valor_vencido", "dias_mora"} & set(r)
    assert identidad.buscar_cliente(con, "9999999999")["encontrado"] is False
    assert identidad.buscar_cliente(con, "abc")["encontrado"] is False


def test_otp_correcto_verifica_y_se_consume(sandbox):
    con = sandbox["con"]
    assert identidad.enviar_otp(con, "1000000001", "h1")["enviado"]
    cod = leer_otp(con, "1000000001")
    assert identidad.validar_otp(con, "1000000001", "h1", "000000")["verificado"] is False
    assert identidad.validar_otp(con, "1000000001", "h1", cod)["verificado"] is True
    # el mismo código no sirve dos veces
    assert identidad.validar_otp(con, "1000000001", "h1", cod)["verificado"] is False


def test_otp_se_guarda_con_hash(sandbox):
    con = sandbox["con"]
    identidad.enviar_otp(con, "1000000001", "h1")
    cod = leer_otp(con, "1000000001")
    guardado = con.execute("SELECT codigo_hash FROM otp ORDER BY id DESC LIMIT 1").fetchone()[0]
    assert cod not in guardado and len(guardado) == 64


def test_otp_tres_intentos_bloquea_y_escala(sandbox):
    con = sandbox["con"]
    identidad.enviar_otp(con, "1000000002", "h2")
    r = [identidad.validar_otp(con, "1000000002", "h2", "111111") for _ in range(3)]
    assert r[0]["intentos_restantes"] == 2 and r[1]["intentos_restantes"] == 1
    assert r[2]["bloqueado"] and r[2]["escalar"]
    assert identidad.enviar_otp(con, "1000000002", "h2")["bloqueado"]  # no se puede pedir otro mientras dure el bloqueo


def test_otp_vencido(sandbox):
    con = sandbox["con"]
    identidad.enviar_otp(con, "1000000001", "h1")
    cod = leer_otp(con, "1000000001")
    vencido = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat(timespec="seconds")
    con.execute("UPDATE otp SET vence = ?", (vencido,)); con.commit()
    r = identidad.validar_otp(con, "1000000001", "h1", cod)
    assert r["verificado"] is False and r.get("vencido")


def test_otp_maximo_por_hora(sandbox):
    con = sandbox["con"]
    for _ in range(3):
        assert identidad.enviar_otp(con, "1000000001", "h1")["enviado"]
    r = identidad.enviar_otp(con, "1000000001", "h1")
    assert r["enviado"] is False and r["bloqueado"]


def test_sin_telefono_no_hay_otp(sandbox):
    r = identidad.enviar_otp(sandbox["con"], "1000000007", "h7")
    assert r["enviado"] is False and r["escalar"]
