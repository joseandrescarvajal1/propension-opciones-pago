import numpy as np
import pytest

from inferencia import EntradaInvalida
from tests.conftest import filas_sinteticas


def test_carga_paquete(modelo):
    assert modelo.version == "v4"
    assert 0 < modelo.umbral < 1
    assert len(modelo.features) == modelo.info["n_features"] == 100
    assert modelo.booster.feature_name() == modelo.features


def test_probabilidad_en_rango(modelo, filas):
    p = modelo.probabilidad(filas)
    assert p.shape == (len(filas),)
    assert np.all((p >= 0) & (p <= 1))


def test_clase_respeta_umbral(modelo, filas):
    res = modelo.predecir(filas)
    assert list(res.columns) == ["prob_uno", "var_rpta_alt"]
    assert set(res.var_rpta_alt.unique()) <= {0, 1}
    assert ((res.prob_uno >= modelo.umbral).astype(int) == res.var_rpta_alt).all()
    res2 = modelo.predecir(filas, umbral=0.99)
    assert res2.var_rpta_alt.sum() <= res.var_rpta_alt.sum()


def test_determinismo(modelo, filas):
    a = modelo.probabilidad(filas); b = modelo.probabilidad(filas.copy())
    assert np.allclose(a, b)


def test_orden_de_columnas_no_importa(modelo, filas):
    p1 = modelo.probabilidad(filas)
    p2 = modelo.probabilidad(filas[list(reversed(filas.columns))])
    assert np.allclose(p1, p2)


def test_rechaza_columnas_faltantes(modelo, filas):
    with pytest.raises(EntradaInvalida, match="faltan"):
        modelo.probabilidad(filas.drop(columns=[modelo.features[0]]))


def test_rechaza_columnas_sobrantes(modelo, filas):
    with pytest.raises(EntradaInvalida, match="sobran"):
        modelo.probabilidad(filas.assign(extra=1))


def test_rechaza_vacio(modelo, filas):
    with pytest.raises(EntradaInvalida):
        modelo.probabilidad(filas.iloc[0:0])


def test_categoria_desconocida_no_rompe(modelo, filas):
    if not modelo.categoricas:
        pytest.skip("el modelo no tiene categóricas")
    f = filas.copy(); f[modelo.categoricas[0]] = "VALOR_INEXISTENTE"
    p = modelo.probabilidad(f)
    assert np.all((p >= 0) & (p <= 1))


def test_nulos_permitidos(modelo):
    f = filas_sinteticas(modelo, n=3)
    f.iloc[0, :] = None
    p = modelo.probabilidad(f)
    assert np.isfinite(p).all()
