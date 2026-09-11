"""Crea un paquete de modelo mínimo (LightGBM entrenado con datos sintéticos) para correr las
pruebas donde no hay acceso al modelo real, por ejemplo en CI sin credenciales.

Uso: python tests/crear_modelo_minimo.py models/v4
"""

import json
import sys
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd

destino = Path(sys.argv[1] if len(sys.argv) > 1 else "models/v4"); destino.mkdir(parents=True, exist_ok=True)
rng = np.random.RandomState(0); n = 2000
num = [f"prob_x{i}" if i < 3 else f"num_x{i}" for i in range(97)]
cat = ["obl_producto", "cli_segm", "pag_marca_pago_t1"]
X = pd.DataFrame({c: (rng.uniform(size=n) if c.startswith("prob_") else rng.gamma(2, 100, n)) for c in num})
niveles = {"obl_producto": ["TARJETA", "LIBRE"], "cli_segm": ["PERSONAL", "PLUS"], "pag_marca_pago_t1": ["PAGO_MAS", "NO_PAGO"]}
for c in cat: X[c] = pd.Categorical(rng.choice(niveles[c], n), categories=niveles[c])
y = (X["prob_x0"] + rng.normal(0, 0.3, n) > 0.5).astype(int)
m = lgb.LGBMClassifier(n_estimators=20, num_leaves=7, verbose=-1).fit(X, y, categorical_feature=cat)
m.booster_.save_model(str(destino / "modelo.txt"))
info = {"version": "v4", "modelo": "lightgbm", "umbral": 0.5, "n_features": 100, "features": list(X.columns), "categoricas": cat,
        "niveles_categoricas": niveles, "metricas": {}, "entrenamiento": {"nota": "modelo mínimo sintético para pruebas"}}
(destino / "modelo_info.json").write_text(json.dumps(info, indent=2), encoding="utf-8")
print("paquete mínimo en", destino)
