"""Crea la base del sandbox con 40 clientes simulados que cubren los siete escenarios del enunciado.

Las 100 variables del modelo se toman de obligaciones reales de enero de 2024 (test_fe.parquet, ya
enmascaradas); nombres, cédulas, teléfonos, fechas de nacimiento, saldos redondeados, opciones
preaprobadas, acuerdos y restricciones son ficticios y se asignan según el escenario.

Uso:
    python agente/sandbox/crear_sandbox.py            # crea agente/sandbox/sandbox.db y perfiles.json
    python agente/sandbox/crear_sandbox.py --salida otra.db
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "agente"))
from sandbox.db import HOY, conectar, crear_esquema, insertar  # noqa: E402

# Catálogo de opciones de pago (ejemplos del enunciado + las que aparecen en los datos)
CATALOGO = {
    "AMP": {"nombre": "Ampliación de plazo", "descripcion": "Se extiende el plazo de la deuda para reducir la cuota mensual.", "meses_espera": 3, "factor_cuota": 0.70, "plazo": 48},
    "RED": {"nombre": "Reducción de cuota", "descripcion": "Se reduce temporalmente la cuota durante 6 meses y luego se recalcula.", "meses_espera": 3, "factor_cuota": 0.60, "plazo": 36},
    "TASA": {"nombre": "Renegociación de tasa", "descripcion": "Se baja la tasa de interés y con ella la cuota, manteniendo el plazo.", "meses_espera": 3, "factor_cuota": 0.85, "plazo": None},
    "REEST": {"nombre": "Reestructuración de crédito", "descripcion": "Se unifica el saldo vencido con el capital y se define un nuevo plan de pagos.", "meses_espera": 4, "factor_cuota": 0.55, "plazo": 60},
    "PRORR": {"nombre": "Prórroga", "descripcion": "Periodo de gracia de 2 meses sin cuota; los intereses se difieren al final.", "meses_espera": 4, "factor_cuota": 0.0, "plazo": None},
    "CONSOL": {"nombre": "Consolidación de pasivos", "descripcion": "Se unen varias obligaciones en un solo crédito con una única cuota menor.", "meses_espera": 4, "factor_cuota": 0.65, "plazo": 60},
}

ESCENARIOS = {
    "E1_mora_temprana_alta_prob": "Mora temprana (1 a 30 días) y alta probabilidad; se propone acuerdo de pago a 5 días.",
    "E2_varias_opciones": "Elegible para 2 o 3 opciones de pago; el sistema elige y explica la más adecuada.",
    "E3_no_elegible": "No elegible: opción aplicada recientemente (en espera), sin opciones preaprobadas o con restricción; sin ofertas no autorizadas.",
    "E4_rechazo_incumplimiento": "Cliente con acuerdo previo incumplido o que rechaza y pide otra alternativa.",
    "E5_reactivo_consulta": "Cliente que contacta para consultar su deuda, negociar o manifestar dificultades.",
    "E6_info_incompleta": "Información incompleta o contradictoria en los sistemas; servicio del modelo indisponible.",
    "E7_sensible_humano": "Solicitudes sensibles, intentos de manipulación o transferencia a gestor humano.",
}

NOMBRES = ["Ana María", "Carlos", "Luisa", "Jorge", "Camila", "Andrés", "Valentina", "Santiago", "Mariana", "Juan Pablo", "Daniela", "Felipe", "Laura", "Mateo", "Sofía",
           "Diego", "Paula", "Nicolás", "Isabela", "Sebastián", "Gabriela", "Alejandro", "Natalia", "David", "Juliana", "Miguel", "Carolina", "Esteban", "Manuela", "Ricardo",
           "Adriana", "Julián", "Catalina", "Tomás", "Lucía", "Samuel", "Sara", "Emilio", "Verónica", "Óscar"]
APELLIDOS = ["Gómez", "Rodríguez", "Martínez", "López", "García", "Hernández", "Pérez", "Sánchez", "Ramírez", "Torres", "Flórez", "Díaz", "Vargas", "Castro", "Moreno",
             "Ortiz", "Jiménez", "Ruiz", "Álvarez", "Mendoza", "Rojas", "Cárdenas", "Guerrero", "Medina", "Restrepo", "Ospina", "Zapata", "Arango", "Betancur", "Cano",
             "Giraldo", "Montoya", "Quintero", "Salazar", "Valencia", "Vélez", "Agudelo", "Bedoya", "Echeverri", "Londoño"]


def etapa(dias: int) -> str:
    return "temprana" if dias <= 30 else "media" if dias <= 90 else "avanzada"


def fecha(delta_dias: int) -> str:
    return (date.fromisoformat(HOY) + timedelta(days=delta_dias)).isoformat()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--salida", default=None)
    args = ap.parse_args()
    rng = np.random.RandomState(2024)

    feats = json.loads((ROOT / "configs" / "variables_modelo.json").read_text(encoding="utf-8"))["modelo"]
    test = pd.read_parquet(ROOT / "data" / "processed" / "test_fe.parquet")
    prob = pd.read_csv(ROOT / "outputs" / "resultado_prueba.csv").set_index("ID").Prob_uno
    test["prob_v4"] = test.ID.map(prob)
    con_mora = test[test.lag_dias_mora_fin_ult.notna() & test.lag_saldo_capital_ult.gt(500_000) & test.lag_valor_cuota_mes_ult.gt(50_000)]

    def tomar(mask, n):
        cand = con_mora[mask]
        return cand.sample(n, random_state=int(rng.randint(1_000_000)))

    # Selección de obligaciones reales por escenario (la mora y la probabilidad guían la elección)
    partes = []
    partes.append(tomar((con_mora.lag_dias_mora_fin_ult.between(1, 30)) & (con_mora.prob_v4 >= 0.60) & (con_mora.prob_prob_auto_cura_t1 >= 0.5), 6).assign(escenario="E1_mora_temprana_alta_prob"))
    partes.append(tomar((con_mora.lag_dias_mora_fin_ult.between(31, 90)) & (con_mora.prob_v4 >= 0.45), 6).assign(escenario="E2_varias_opciones"))
    partes.append(tomar((con_mora.lag_dias_mora_fin_ult.between(15, 120)), 6).assign(escenario="E3_no_elegible"))
    partes.append(tomar((con_mora.lag_dias_mora_fin_ult.between(20, 90)) & (con_mora.prob_v4 >= 0.35), 5).assign(escenario="E4_rechazo_incumplimiento"))
    partes.append(tomar((con_mora.lag_dias_mora_fin_ult.between(1, 90)), 5).assign(escenario="E5_reactivo_consulta"))
    faltantes = test[feats].isna().sum(axis=1)
    partes.append(test.loc[faltantes.sort_values(ascending=False).index[:200]].sample(4, random_state=7).assign(escenario="E6_info_incompleta"))
    partes.append(tomar((con_mora.lag_dias_mora_fin_ult.between(1, 150)), 4).assign(escenario="E7_sensible_humano"))
    partes.append(tomar((con_mora.lag_dias_mora_fin_ult.between(1, 120)), 4).assign(escenario="E5_reactivo_consulta"))
    sel = pd.concat(partes).reset_index(drop=True)
    assert len(sel) == 40 and sel.ID.is_unique

    salida = Path(args.salida) if args.salida else ROOT / "agente" / "sandbox" / "sandbox.db"
    if salida.exists():
        salida.unlink()
    con = conectar(salida)
    crear_esquema(con)

    perfiles = []
    for i, r in sel.iterrows():
        esc = r.escenario
        sub = ""
        cedula = f"10{rng.randint(10_000_000, 99_999_999)}"
        nombre = f"{NOMBRES[i]} {APELLIDOS[i]}"
        telefono = f"+57 3{rng.randint(0, 3)}{rng.randint(1_000_000, 9_999_999):07d}"
        edad = int(r.cli_edad_cli) if pd.notna(r.cli_edad_cli) and 18 <= r.cli_edad_cli <= 90 else int(rng.randint(25, 65))
        nac = date(2024 - edad, int(rng.randint(1, 13)), int(rng.randint(1, 28))).isoformat()
        dias = int(r.lag_dias_mora_fin_ult) if pd.notna(r.lag_dias_mora_fin_ult) else int(rng.randint(5, 60))
        saldo = float(round(r.lag_saldo_capital_ult, -3)) if pd.notna(r.lag_saldo_capital_ult) else float(rng.randint(2_000, 30_000) * 1000)
        cuota = float(round(r.lag_valor_cuota_mes_ult, -3)) if pd.notna(r.lag_valor_cuota_mes_ult) else float(round(saldo / 36, -3))
        vencido = float(round(r.lag_vlr_vencido_ult, -3)) if pd.notna(r.lag_vlr_vencido_ult) and r.lag_vlr_vencido_ult > 0 else float(round(cuota * max(1, dias // 30 + 1), -3))
        producto = str(r.obl_producto) if pd.notna(r.obl_producto) else "LIBRE INVERSION"

        # Opciones preaprobadas, aplicadas, acuerdos y restricciones según el escenario
        opciones: list[str] = []
        aplicadas: list[tuple[str, int]] = []   # (codigo, hace_cuantos_dias)
        acuerdos: list[tuple[int, int, str]] = []  # (hace_dias, plazo_dias, estado)
        restricciones: list[tuple[str, str]] = []
        if esc == "E1_mora_temprana_alta_prob":
            dias = min(dias, 30)
            opciones = list(rng.choice(["AMP", "TASA"], size=int(rng.randint(0, 2)), replace=False))
        elif esc == "E2_varias_opciones":
            dias = max(dias, 31)
            opciones = list(rng.choice(list(CATALOGO), size=int(rng.randint(2, 4)), replace=False))
        elif esc == "E3_no_elegible":
            k = i % 3
            if k == 0:
                sub = "opcion_reciente"; opciones = list(rng.choice(["AMP", "RED"], size=2, replace=False)); aplicadas = [("REEST", int(rng.randint(20, 75)))]
            elif k == 1:
                sub = "sin_preaprobadas"; opciones = []; dias = max(dias, 95)
            else:
                sub = "restriccion"; opciones = ["AMP", "TASA"]; restricciones = [("juridica", "Obligación en cobro jurídico desde 2023-12-01")]
        elif esc == "E4_rechazo_incumplimiento":
            opciones = list(rng.choice(["AMP", "RED", "REEST"], size=2, replace=False))
            acuerdos = [(int(rng.randint(8, 25)), 5, "incumplido")]
            sub = "acuerdo_incumplido"
        elif esc == "E5_reactivo_consulta":
            opciones = list(rng.choice(list(CATALOGO), size=int(rng.randint(1, 3)), replace=False))
            if i % 2 == 0:
                aplicadas = [("AMP", int(rng.randint(150, 240)))]  # ya cumplió la espera
        elif esc == "E6_info_incompleta":
            k = i % 4
            if k == 0:
                sub = "variables_faltantes"; opciones = ["AMP"]
            elif k == 1:
                sub = "contradictoria"; opciones = ["AMP", "RED"]; dias = 0; vencido = cuota * 2  # 0 días de mora pero valor vencido > 0
            elif k == 2:
                sub = "sin_telefono"; telefono = ""; opciones = ["TASA"]
            else:
                sub = "servicio_modelo_caido"; opciones = ["AMP", "REEST"]
        elif esc == "E7_sensible_humano":
            k = i % 4
            if k == 0:
                sub = "fallecido"; restricciones = [("fallecido", "Reporte de fallecimiento en validación; contacto de un familiar")]
            elif k == 1:
                sub = "fraude"; restricciones = [("fraude", "Reclamación por transacciones no reconocidas en curso")]; opciones = ["AMP"]
            elif k == 2:
                sub = "manipulacion"; opciones = ["AMP", "TASA"]
            else:
                sub = "reclamacion"; restricciones = [("reclamacion", "Reclamación por cobro duplicado de cuota, radicado 2024-01-08")]; opciones = ["RED"]

        insertar(con, "clientes", {"cedula": cedula, "nit_enmascarado": int(r.nit_enmascarado), "nombre": nombre, "telefono": telefono, "fecha_nacimiento": nac,
                                   "segmento": None if pd.isna(r.obl_segmento) else str(r.obl_segmento), "escenario": esc, "descripcion_escenario": (sub + ": " if sub else "") + ESCENARIOS[esc]})
        variables = {f: (None if pd.isna(r[f]) else (str(r[f]) if isinstance(r[f], str) or str(test[f].dtype) == "category" else float(r[f]))) for f in feats}
        insertar(con, "obligaciones", {"id_obligacion": str(r.ID), "cedula": cedula, "producto": producto, "saldo_capital": saldo, "valor_cuota": cuota, "valor_vencido": vencido,
                                       "dias_mora": dias, "etapa_mora": etapa(dias), "variables_modelo": variables})
        for cod in opciones:
            c = CATALOGO[cod]
            insertar(con, "opciones_preaprobadas", {"id_obligacion": str(r.ID), "codigo": cod, "nombre": c["nombre"], "descripcion": c["descripcion"],
                                                    "cuota_nueva": round(cuota * c["factor_cuota"], -3), "plazo_meses": c["plazo"], "meses_espera": c["meses_espera"], "vigente_hasta": fecha(30)})
        for cod, hace in aplicadas:
            c = CATALOGO[cod]
            insertar(con, "opciones_aplicadas", {"id_obligacion": str(r.ID), "codigo": cod, "nombre": c["nombre"], "fecha_aplicacion": fecha(-hace), "meses_espera": c["meses_espera"]})
        for hace, plazo, estado in acuerdos:
            insertar(con, "acuerdos", {"id_obligacion": str(r.ID), "fecha_acuerdo": fecha(-hace), "fecha_compromiso": fecha(-hace + plazo), "valor": vencido, "estado": estado})
        for tipo, det in restricciones:
            insertar(con, "restricciones", {"cedula": cedula, "tipo": tipo, "detalle": det})
        perfiles.append({"cedula": cedula, "nombre": nombre, "telefono": telefono, "escenario": esc, "subcaso": sub or None, "id_obligacion": str(r.ID), "producto": producto,
                         "dias_mora": dias, "saldo_capital": saldo, "valor_cuota": cuota, "prob_v4": None if pd.isna(r.prob_v4) else round(float(r.prob_v4), 4),
                         "opciones_preaprobadas": opciones, "opciones_aplicadas": [c for c, _ in aplicadas], "acuerdos": [e for *_, e in acuerdos], "restricciones": [t for t, _ in restricciones]})

    (salida.parent / "perfiles.json").write_text(json.dumps({"hoy_sandbox": HOY, "escenarios": ESCENARIOS, "catalogo_opciones": CATALOGO, "clientes": perfiles}, indent=2, ensure_ascii=False), encoding="utf-8")
    n = {t: con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in ("clientes", "obligaciones", "opciones_preaprobadas", "opciones_aplicadas", "acuerdos", "restricciones")}
    print(f"sandbox creado en {salida} | hoy = {HOY} | {n}")
    print(pd.Series([p["escenario"] for p in perfiles]).value_counts().to_string())


if __name__ == "__main__":
    main()
