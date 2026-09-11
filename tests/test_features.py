"""Pruebas de las funciones de construcción de variables. La más importante es la de no fuga temporal:
ninguna ventana puede usar información del mes objetivo t ni de meses posteriores."""

import numpy as np
import pandas as pd

from features import last_valid_before, meses_desde, month_idx, pendiente, racha_final, racha_max, to_wide, ventana, window_sum_count


def _matriz():
    # 2 entidades x 13 meses; la entidad 0 tiene valores = índice del mes, la 1 solo tiene meses 3..5
    M = np.full((2, 13), np.nan)
    M[0, :] = np.arange(13, dtype=float)
    M[1, 3:6] = [10.0, 20.0, 30.0]
    return M


def test_month_idx():
    assert month_idx(202301) == 0 and month_idx(202312) == 11 and month_idx(202401) == 12
    assert list(month_idx(pd.Series([202308, 202401]))) == [7, 12]


def test_to_wide():
    M = to_wide(np.array([0, 0, 1]), np.array([2, 5, 7]), np.array([1.0, 2.0, 3.0]), 2)
    assert M.shape == (2, 13) and M[0, 2] == 1.0 and M[0, 5] == 2.0 and M[1, 7] == 3.0 and np.isnan(M[0, 0])


def test_ventana_no_usa_el_mes_objetivo_ni_posteriores():
    """No fuga temporal: la ventana de k meses para el mes t cubre exactamente t-k .. t-1."""
    M = _matriz()
    r = np.array([0, 0]); t = np.array([7, 12])
    W = ventana(M, r, t, 3)
    assert W[0].tolist() == [4.0, 5.0, 6.0]      # t=7 -> meses 4,5,6
    assert W[1].tolist() == [9.0, 10.0, 11.0]    # t=12 -> meses 9,10,11
    assert not np.any(W >= t[:, None])           # ningún valor viene de un mes >= t


def test_window_sum_count_respeta_el_corte():
    M = _matriz()
    s, c = window_sum_count(M, np.array([0, 1, 1]), np.array([7, 5, 3]), 12)
    assert s[0] == sum(range(7)) and c[0] == 7    # meses 0..6, nunca el 7
    assert s[1] == 30.0 and c[1] == 2             # entidad 1 en t=5 ve meses 3 y 4 (10 + 20), no el 5
    assert c[2] == 0                              # en t=3 no hay nada anterior


def test_window_sum_count_sin_fila():
    s, c = window_sum_count(_matriz(), np.array([-1]), np.array([7]), 3)
    assert np.isnan(s[0]) and np.isnan(c[0])


def test_last_valid_before():
    M = _matriz()
    val, when = last_valid_before(M, np.array([1, 1, 0]), np.array([7, 4, 12]))
    assert val[0] == 30.0 and when[0] == 5        # último valor antes de t=7 está en el mes 5
    assert val[1] == 10.0 and when[1] == 3        # en t=4 solo se ve el mes 3
    assert val[2] == 11.0 and when[2] == 11


def test_pendiente():
    creciente = np.array([[1.0, 2.0, 3.0, 4.0]]); constante = np.array([[5.0, 5.0, 5.0, 5.0]]); pocos = np.array([[1.0, np.nan, np.nan, 2.0]])
    assert np.isclose(pendiente(creciente)[0], 1.0)
    assert np.isclose(pendiente(constante)[0], 0.0)
    assert np.isnan(pendiente(pocos)[0])


def test_rachas():
    W = np.array([[1, 0, 0, 1, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0], [1, 1, 1, 1, 1, 1, 1], [0, 0, np.nan, 0, 0, 0, 0]], dtype=float)
    assert racha_final(W).tolist() == [3, 7, 0, 4]
    assert racha_max(W).tolist() == [3, 7, 0, 4]


def test_meses_desde():
    M = np.zeros((1, 13)); M[0, 4] = 1; M[0, 9] = 1
    out = meses_desde(M, np.array([0, 0, 0]), np.array([7, 10, 12]))
    assert out.tolist() == [3, 1, 3]             # t=7 ve el 4; t=10 ve el 9; t=12 ve el 9
    assert np.isnan(meses_desde(M, np.array([-1]), np.array([7]))[0])
