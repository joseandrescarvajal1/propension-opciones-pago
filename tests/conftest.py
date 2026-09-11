"""Fixtures compartidas. Los datos son sintéticos: se generan a partir de la lista de variables
del paquete de modelo, sin tocar data/."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

os.environ.setdefault("API_KEY", "clave-de-prueba")
os.environ.setdefault("MODELO_RUTA", str(ROOT / "models" / "v4"))


@pytest.fixture(scope="session")
def modelo():
    from inferencia import Modelo

    return Modelo.cargar(os.environ["MODELO_RUTA"])


def filas_sinteticas(modelo, n: int = 8, semilla: int = 0) -> pd.DataFrame:
    """DataFrame con las variables del modelo: numéricas aleatorias (con algunos nulos) y categóricas con niveles válidos."""
    rng = np.random.RandomState(semilla)
    niveles = modelo.info.get("niveles_categoricas", {})
    datos = {}
    for c in modelo.features:
        if c in modelo.categoricas:
            opciones = niveles.get(c) or ["A", "B"]
            datos[c] = rng.choice(opciones, size=n).astype(object)
        else:
            v = rng.uniform(0, 1, size=n) if c.startswith("prob_") else rng.gamma(2.0, 100.0, size=n)
            v[rng.rand(n) < 0.15] = np.nan
            datos[c] = v
    return pd.DataFrame(datos)


@pytest.fixture
def filas(modelo):
    return filas_sinteticas(modelo)


@pytest.fixture
def cliente():
    from fastapi.testclient import TestClient

    from api.main import app

    with TestClient(app) as c:
        yield c


@pytest.fixture
def cabecera():
    return {"X-API-Key": os.environ["API_KEY"]}
