"""Monitoreo del modelo en producción: deriva de variables y de predicción, y desempeño real.

Medida principal: PSI (Population Stability Index) entre una distribución de referencia
(datos de entrenamiento) y una actual (mes calificado). Umbrales usuales en banca:
    PSI < 0.10  estable
    0.10-0.25   aviso: revisar
    > 0.25      alarma: la variable cambió de distribución

PSI = sum_i (p_act_i - p_ref_i) * ln(p_act_i / p_ref_i), con tramos definidos por los
cuantiles de la referencia (numéricas) o por categoría (categóricas). Se suaviza con
epsilon para que un tramo vacío no produzca infinito.

Uso:
    from monitoreo import psi, reporte_psi, resumen_prediccion
    tabla = reporte_psi(df_ref, df_act, columnas)
"""

from __future__ import annotations

from collections.abc import Iterable

import numpy as np
import pandas as pd

EPS = 1e-6
UMBRAL_AVISO, UMBRAL_ALARMA = 0.10, 0.25


def _proporciones_numericas(ref: pd.Series, act: pd.Series, bins: int) -> tuple[np.ndarray, np.ndarray]:
    ref = pd.to_numeric(ref, errors="coerce"); act = pd.to_numeric(act, errors="coerce")
    r, a = ref.dropna().to_numpy(), act.dropna().to_numpy()
    if len(r) == 0 or len(a) == 0:
        return np.array([1.0]), np.array([1.0])
    cortes = np.unique(np.quantile(r, np.linspace(0, 1, bins + 1)))
    if len(cortes) < 2:  # variable constante en la referencia
        cortes = np.array([cortes[0] - 0.5, cortes[0] + 0.5])
    cortes[0], cortes[-1] = -np.inf, np.inf
    p_ref = np.histogram(r, bins=cortes)[0] / len(r)
    p_act = np.histogram(a, bins=cortes)[0] / len(a)
    # los nulos se tratan como un tramo adicional
    n_ref, n_act = ref.isna().mean(), act.isna().mean()
    p_ref = np.append(p_ref * (1 - n_ref), n_ref); p_act = np.append(p_act * (1 - n_act), n_act)
    return p_ref, p_act


def _proporciones_categoricas(ref: pd.Series, act: pd.Series) -> tuple[np.ndarray, np.ndarray]:
    r = ref.astype(object).where(ref.notna(), "(nulo)"); a = act.astype(object).where(act.notna(), "(nulo)")
    niveles = pd.Index(r.unique()).union(pd.Index(a.unique()))
    p_ref = r.value_counts(normalize=True).reindex(niveles, fill_value=0).to_numpy()
    p_act = a.value_counts(normalize=True).reindex(niveles, fill_value=0).to_numpy()
    return p_ref, p_act


def psi(ref: pd.Series, act: pd.Series, bins: int = 10) -> float:
    """PSI entre la distribución de referencia y la actual de una variable (numérica o categórica)."""
    es_cat = ref.dtype == object or str(ref.dtype) == "category" or act.dtype == object or str(act.dtype) == "category"
    p_ref, p_act = _proporciones_categoricas(ref, act) if es_cat else _proporciones_numericas(ref, act, bins)
    p_ref = np.clip(p_ref, EPS, None); p_act = np.clip(p_act, EPS, None)
    return float(np.sum((p_act - p_ref) * np.log(p_act / p_ref)))


def clasificar(valor: float) -> str:
    return "alarma" if valor > UMBRAL_ALARMA else ("aviso" if valor > UMBRAL_AVISO else "estable")


def reporte_psi(df_ref: pd.DataFrame, df_act: pd.DataFrame, columnas: Iterable[str], bins: int = 10) -> pd.DataFrame:
    """Tabla con PSI, estado y porcentaje de nulos por variable, ordenada de mayor a menor PSI."""
    filas = []
    for c in columnas:
        v = psi(df_ref[c], df_act[c], bins)
        filas.append({"variable": c, "psi": round(v, 4), "estado": clasificar(v), "nulos_ref": round(float(df_ref[c].isna().mean()), 4), "nulos_act": round(float(df_act[c].isna().mean()), 4)})
    return pd.DataFrame(filas).sort_values("psi", ascending=False).reset_index(drop=True)


def resumen_prediccion(p_ref: np.ndarray, p_act: np.ndarray, umbral: float, bins: int = 10) -> dict[str, float | str]:
    """Deriva de la predicción: PSI de las probabilidades y cambio en el porcentaje de unos."""
    v = psi(pd.Series(p_ref), pd.Series(p_act), bins)
    pct_ref, pct_act = float((p_ref >= umbral).mean()), float((p_act >= umbral).mean())
    return {"psi_probabilidad": round(v, 4), "estado": clasificar(v), "pct_uno_ref": round(pct_ref, 4), "pct_uno_act": round(pct_act, 4),
            "prob_media_ref": round(float(np.mean(p_ref)), 4), "prob_media_act": round(float(np.mean(p_act)), 4)}


def desempeno_real(y_true: np.ndarray, p: np.ndarray, umbral: float) -> dict[str, float]:
    """Métricas cuando llega la etiqueta real del mes calificado."""
    from sklearn.metrics import f1_score, precision_score, recall_score, roc_auc_score

    pred = (p >= umbral).astype(int)
    return {"f1": round(float(f1_score(y_true, pred)), 4), "precision": round(float(precision_score(y_true, pred)), 4),
            "recall": round(float(recall_score(y_true, pred)), 4), "auc": round(float(roc_auc_score(y_true, p)), 4), "pct_uno": round(float(pred.mean()), 4)}


def decidir_reentreno(historial_f1: list[float], umbral_f1: float = 0.68, meses_consecutivos: int = 2) -> bool:
    """Regla: reentrenar si el F1 real queda por debajo del umbral durante N meses seguidos."""
    if len(historial_f1) < meses_consecutivos:
        return False
    return all(f < umbral_f1 for f in historial_f1[-meses_consecutivos:])
