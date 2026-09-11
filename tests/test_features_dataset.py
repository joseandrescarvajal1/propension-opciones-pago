"""Prueba de extremo a extremo de la construcción del dataset con tablas sintéticas pequeñas.
Verifica el esquema (156 columnas), la ausencia de errores y la regla de no fuga temporal sobre
las variables rezagadas de trtest."""

import numpy as np
import pandas as pd
import pytest

from features import CLI_CAT, CLI_NUM, ID_COLS, LAG_CAT, LAG_NUM, TARGET, construir_desde_crudos

MESES_TR = [202308, 202309, 202310, 202311, 202312]


@pytest.fixture(scope="module")
def crudos():
    rng = np.random.RandomState(7)
    n_obl, n_cli = 40, 25
    obl = np.arange(1000, 1000 + n_obl)
    nit = rng.randint(1, n_cli + 1, size=n_obl)
    orig = obl + 5000
    # trtest: cada obligación aparece en 2 a 5 meses
    filas = []
    for i, o in enumerate(obl):
        for m in rng.choice(MESES_TR, size=rng.randint(2, 6), replace=False):
            f = {"nit_enmascarado": nit[i], "num_oblig_orig_enmascarado": orig[i], "num_oblig_enmascarado": o, "fecha_var_rpta_alt": int(m), TARGET: int(rng.rand() < 0.5)}
            for c in LAG_NUM:
                if c != TARGET:
                    f[c] = float(rng.randint(0, 100))
            for c in LAG_CAT:
                f[c] = rng.choice(["A", "B", "C"])
            f["marca_alt_apli"] = rng.choice(["SI", "NO"])
            filas.append(f)
    tr_raw = pd.DataFrame(filas)
    oot_raw = pd.DataFrame({"nit_enmascarado": nit, "num_oblig_orig_enmascarado": orig, "num_oblig_enmascarado": obl, "fecha_var_rpta_alt": 202401})
    # probabilidades y pagos: 12 meses de 2023 para todas las obligaciones
    meses = [202300 + m for m in range(1, 13)]
    prob = pd.DataFrame([{"nit_enmascarado": nit[i], "num_oblig_enmascarado": o, "fecha_corte": m, "lote": rng.randint(1, 4), "prob_propension": rng.rand(), "prob_alrt_temprana": rng.rand(), "prob_auto_cura": rng.rand()}
                         for i, o in enumerate(obl) for m in meses])
    pag = pd.DataFrame([{"nit_enmascarado": nit[i], "num_oblig_enmascarado": o, "fecha_corte": m * 100 + 28, "producto": rng.choice(["TDC", "LI"]),
                          "aplicativo": rng.choice(["L", "M"]), "segmento": rng.choice(["Personal", "Pymes"]),
                          "valor_cuota_mes": float(rng.randint(100, 1000)), "pago_total": float(rng.choice([0, 200, 900])), "porc_pago": float(rng.choice([0, 50, 100, 200])),
                          "marca_pago": rng.choice(["PAGO_MAS", "NO_PAGO", "IGUAL"]), "ajustes_banco": rng.choice(["NO", "NO", "REDIFERIDOS"])}
                         for i, o in enumerate(obl) for m in meses])
    # customer: 2 cortes por cliente
    cli = pd.DataFrame([{"nit_enmascarado": c, "year": 2023, "month": mm, "f_vinc": 20150101, **{k: float(rng.randint(0, 1000)) for k in CLI_NUM}, **{k: rng.choice(["x", "y"]) for k in CLI_CAT}}
                        for c in range(1, n_cli + 1) for mm in (9, 12)])
    cli["edad_cli"] = rng.randint(20, 70, size=len(cli)).astype(float)
    # preparación que hace cargar_crudos
    prob["t"] = (prob.fecha_corte // 100 - 2023) * 12 + prob.fecha_corte % 100 - 1
    pag["t"] = (pag.fecha_corte // 100 // 100 - 2023) * 12 + (pag.fecha_corte // 100) % 100 - 1
    pag["pago_flag"] = (pag.pago_total > 0).astype(float); pag["no_pago"] = (pag.marca_pago == "NO_PAGO").astype(float); pag["pago_mas"] = (pag.marca_pago == "PAGO_MAS").astype(float)
    pag["cancelado"] = 0.0; pag["rediferido"] = (pag.ajustes_banco == "REDIFERIDOS").astype(float); pag["ajuste"] = (pag.ajustes_banco != "NO").astype(float); pag["pago_completo"] = (pag.porc_pago >= 100).astype(float)
    cli["t"] = (cli.year - 2023) * 12 + cli.month - 1
    return {"tr_raw": tr_raw, "oot_raw": oot_raw, "prob": prob, "pag": pag, "cli": cli}


def test_dataset_esquema(crudos):
    train, test, cols = construir_desde_crudos(crudos)
    assert len(cols) == 156
    assert len(train) == len(crudos["tr_raw"]) and len(test) == len(crudos["oot_raw"])
    assert TARGET in train.columns and TARGET not in test.columns
    assert all(c in train.columns for c in cols) and all(c in test.columns for c in cols)
    assert set(train.fecha_var_rpta_alt.unique()) == set(MESES_TR) and set(test.fecha_var_rpta_alt.unique()) == {202401}


def test_dataset_no_fuga_en_rezagos(crudos):
    """El rezago del target de una obligación en t debe ser su target del mes t-1 (nunca el de t)."""
    train, _, _ = construir_desde_crudos(crudos)
    tr = crudos["tr_raw"].set_index(["num_oblig_enmascarado", "fecha_var_rpta_alt"])[TARGET]
    prev = {202309: 202308, 202310: 202309, 202311: 202310, 202312: 202311}
    comprobadas = 0
    for _, fila in train.iterrows():
        m = fila.fecha_var_rpta_alt
        if m == 202308:
            assert fila.lag_n_meses_vistos == 0 and np.isnan(fila.lag_acepto_t1)
            continue
        clave = (fila.num_oblig_enmascarado, prev[m])
        if clave in tr.index:
            assert fila.lag_acepto_t1 == tr.loc[clave]; comprobadas += 1
        else:
            assert np.isnan(fila.lag_acepto_t1)
    assert comprobadas > 0


def test_dataset_test_usa_solo_2023(crudos):
    """Para enero de 2024 el historial de pagos cubre los 12 meses de 2023 y la tasa histórica por producto
    es la tasa de aceptación de train (5 meses) para los productos con al menos 50 filas; nulo en los demás."""
    _, test, _ = construir_desde_crudos(crudos)
    assert (test.pag_meses_historial == 12).all()
    tasas = crudos["tr_raw"].groupby("producto")[TARGET].agg(["mean", "size"])
    for prod, fila in test.groupby("obl_producto", observed=True):
        if prod in tasas.index and tasas.loc[prod, "size"] >= 50:
            assert np.allclose(fila.fe_tasa_hist_producto, tasas.loc[prod, "mean"])
        else:
            assert fila.fe_tasa_hist_producto.isna().all()


def test_dataset_sin_columnas_identificadoras_en_variables(crudos):
    _, _, cols = construir_desde_crudos(crudos)
    assert not set(cols) & set(ID_COLS)
