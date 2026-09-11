"""Carga del modelo empaquetado y predicción.

Un paquete de modelo es una carpeta con dos archivos:
    modelo.txt          -> booster de LightGBM
    modelo_info.json    -> versión, umbral, lista de variables, categóricas y sus niveles, métricas

La carpeta puede ser local (models/v4) o de Cloud Storage (gs://bucket/modelos/v4).

Uso:
    from inferencia import Modelo
    modelo = Modelo.cargar("models/v4")
    resultado = modelo.predecir(df)      # df con las columnas de modelo.features
"""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import lightgbm as lgb
import numpy as np
import pandas as pd


class EntradaInvalida(ValueError):
    """La entrada no tiene las columnas que el modelo espera."""


def _descargar_gcs(uri: str) -> Path:
    """Descarga modelo.txt y modelo_info.json de gs://bucket/ruta a una carpeta temporal."""
    from google.cloud import storage  # importación tardía: solo se necesita en GCP

    bucket_name, _, prefijo = uri[len("gs://"):].partition("/")
    destino = Path(tempfile.mkdtemp(prefix="modelo_"))
    bucket = storage.Client().bucket(bucket_name)
    for nombre in ("modelo.txt", "modelo_info.json"):
        bucket.blob(f"{prefijo.rstrip('/')}/{nombre}").download_to_filename(str(destino / nombre))
    return destino


@dataclass
class Modelo:
    booster: lgb.Booster
    info: dict[str, Any]
    ruta: str
    features: list[str] = field(init=False)
    categoricas: list[str] = field(init=False)
    umbral: float = field(init=False)

    def __post_init__(self) -> None:
        self.features = list(self.info["features"])
        self.categoricas = list(self.info.get("categoricas", []))
        self.umbral = float(self.info["umbral"])
        if self.booster.feature_name() != self.features:
            raise ValueError("Las variables de modelo.txt no coinciden con modelo_info.json")

    # ------------------------------------------------------------------ carga
    @classmethod
    def cargar(cls, ruta: str | Path | None = None) -> Modelo:
        """Carga el paquete desde una carpeta local o gs://. Si no se indica, usa MODELO_RUTA o models/v4."""
        ruta = str(ruta or os.environ.get("MODELO_RUTA") or Path(__file__).resolve().parents[1] / "models" / "v4")
        carpeta = _descargar_gcs(ruta) if ruta.startswith("gs://") else Path(ruta)
        info = json.loads((carpeta / "modelo_info.json").read_text(encoding="utf-8"))
        booster = lgb.Booster(model_file=str(carpeta / "modelo.txt"))
        return cls(booster=booster, info=info, ruta=ruta)

    # ------------------------------------------------------------ validación
    def validar(self, df: pd.DataFrame) -> None:
        faltan = [c for c in self.features if c not in df.columns]
        sobran = [c for c in df.columns if c not in self.features]
        if faltan or sobran:
            raise EntradaInvalida(f"faltan {len(faltan)} columnas {faltan[:5]}{'...' if len(faltan) > 5 else ''}; sobran {len(sobran)} {sobran[:5]}{'...' if len(sobran) > 5 else ''}")
        if len(df) == 0:
            raise EntradaInvalida("la entrada no tiene filas")

    def preparar(self, df: pd.DataFrame) -> pd.DataFrame:
        """Ordena las columnas, convierte numéricas y fija las categóricas con los niveles del entrenamiento."""
        self.validar(df)
        X = df[self.features].copy()
        niveles = self.info.get("niveles_categoricas", {})
        for c in self.features:
            if c in self.categoricas:
                X[c] = pd.Categorical(X[c].astype(object).where(X[c].notna(), None), categories=niveles.get(c))
            else:
                X[c] = pd.to_numeric(X[c], errors="coerce").astype(float)
        return X

    # ------------------------------------------------------------ predicción
    def probabilidad(self, df: pd.DataFrame) -> np.ndarray:
        return self.booster.predict(self.preparar(df))

    def predecir(self, df: pd.DataFrame, umbral: float | None = None) -> pd.DataFrame:
        """Devuelve un DataFrame con prob_uno y var_rpta_alt (0/1) por fila, en el mismo orden."""
        u = self.umbral if umbral is None else float(umbral)
        p = self.probabilidad(df)
        return pd.DataFrame({"prob_uno": p, "var_rpta_alt": (p >= u).astype(int)}, index=df.index)

    # --------------------------------------------------------- explicabilidad
    def contribuciones(self, df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
        """Valores SHAP (TreeSHAP nativo de LightGBM) en escala logit: matriz (n, n_features) y valor base (n,).
        La probabilidad es sigmoide(base + suma de contribuciones)."""
        C = self.booster.predict(self.preparar(df), pred_contrib=True)
        return C[:, :-1], C[:, -1]

    def explicar(self, df: pd.DataFrame, k: int = 5) -> list[dict[str, Any]]:
        """Para cada fila: probabilidad, valor base y las k variables con mayor contribución absoluta,
        cada una con su valor, su contribución (logit) y el sentido (sube o baja la probabilidad)."""
        C, base = self.contribuciones(df)
        X = df[self.features]
        p = 1 / (1 + np.exp(-(base + C.sum(axis=1))))
        salida = []
        for i in range(len(df)):
            orden = np.argsort(-np.abs(C[i]))[:k]
            factores = []
            for j in orden:
                v = X.iloc[i, j]
                factores.append({"variable": self.features[j], "valor": None if (isinstance(v, float) and np.isnan(v)) or v is None else (v.item() if hasattr(v, "item") else v),
                                 "contribucion": round(float(C[i, j]), 4), "sentido": "sube" if C[i, j] > 0 else "baja"})
            salida.append({"prob_uno": round(float(p[i]), 6), "base": round(float(base[i]), 4), "factores": factores})
        return salida

    @property
    def version(self) -> str:
        return str(self.info.get("version", "desconocida"))
