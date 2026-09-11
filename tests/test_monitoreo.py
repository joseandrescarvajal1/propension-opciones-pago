import numpy as np
import pandas as pd

from monitoreo import clasificar, decidir_reentreno, desempeno_real, psi, reporte_psi, resumen_prediccion


def test_psi_misma_distribucion_es_cero():
    x = pd.Series(np.random.RandomState(0).normal(size=5000))
    assert psi(x, x) < 1e-6


def test_psi_distribuciones_distintas_supera_alarma():
    rng = np.random.RandomState(0)
    a = pd.Series(rng.normal(0, 1, 5000)); b = pd.Series(rng.normal(2, 1, 5000))
    assert psi(a, b) > 0.25 and clasificar(psi(a, b)) == "alarma"


def test_psi_pequena_deriva_es_aviso_o_estable():
    rng = np.random.RandomState(1)
    a = pd.Series(rng.normal(0, 1, 20000)); b = pd.Series(rng.normal(0.1, 1, 20000))
    v = psi(a, b); assert 0 <= v < 0.25


def test_psi_sin_infinitos_con_tramo_vacio():
    a = pd.Series(np.r_[np.zeros(100), np.ones(100)]); b = pd.Series(np.ones(200))
    v = psi(a, b); assert np.isfinite(v) and v > 0


def test_psi_categorica():
    a = pd.Series(["x"] * 80 + ["y"] * 20); b = pd.Series(["x"] * 20 + ["y"] * 80)
    assert psi(a, b) > 0.25
    assert psi(a, a) < 1e-6


def test_psi_con_nulos_y_constante():
    a = pd.Series([1.0] * 50 + [np.nan] * 50); b = pd.Series([1.0] * 100)
    assert np.isfinite(psi(a, b))


def test_reporte_psi_ordenado():
    rng = np.random.RandomState(2)
    ref = pd.DataFrame({"estable": rng.normal(size=1000), "cambia": rng.normal(size=1000), "cat": rng.choice(["a", "b"], 1000)})
    act = pd.DataFrame({"estable": rng.normal(size=1000), "cambia": rng.normal(3, 1, size=1000), "cat": rng.choice(["a", "b"], 1000)})
    t = reporte_psi(ref, act, ["estable", "cambia", "cat"])
    assert list(t.columns) == ["variable", "psi", "estado", "nulos_ref", "nulos_act"]
    assert t.iloc[0].variable == "cambia" and t.iloc[0].estado == "alarma"


def test_resumen_prediccion():
    rng = np.random.RandomState(3)
    r = resumen_prediccion(rng.uniform(size=1000), rng.uniform(size=1000), umbral=0.5)
    assert set(r) >= {"psi_probabilidad", "estado", "pct_uno_ref", "pct_uno_act"} and 0.4 < r["pct_uno_act"] < 0.6


def test_desempeno_real():
    y = np.array([0, 0, 1, 1]); p = np.array([0.1, 0.4, 0.6, 0.9])
    d = desempeno_real(y, p, 0.5); assert d["f1"] == 1.0 and d["auc"] == 1.0


def test_decidir_reentreno():
    assert decidir_reentreno([0.70, 0.67, 0.66], umbral_f1=0.68) is True
    assert decidir_reentreno([0.67, 0.70], umbral_f1=0.68) is False
    assert decidir_reentreno([0.60], umbral_f1=0.68) is False
