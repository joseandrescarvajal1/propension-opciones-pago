"""Reentrena CatBoost con los mejores hiperparámetros del notebook 04 sobre todo el train
y califica el oot (enero 2024). Escribe outputs/submission_v2_catboost.csv y
outputs/resultado_prueba_v2_catboost.csv, y guarda models/catboost_v2.cbm.

Uso: python src/catboost_v2_oot.py
"""

from pathlib import Path

import pandas as pd
from catboost import CatBoostClassifier, Pool

ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / "data" / "processed"
OUT = ROOT / "outputs"
P_CAT = dict(depth=6, learning_rate=0.06, l2_leaf_reg=1, random_strength=0.5)  # mejor combinación del notebook 04
N_ARB, UMBRAL, SEED = 1500, 0.38, 42  # árboles y umbral fijados en X_val del notebook 04

train = pd.read_parquet(PROC / "train.parquet")
oot = pd.read_parquet(PROC / "test.parquet")
FEATS = pd.read_csv(PROC / "features_seleccionadas.csv").feature.tolist()
CAT = [c for c in FEATS if str(train[c].dtype) == "category"]


def para_cat(df):
    d = df[FEATS].copy()
    for c in CAT:
        d[c] = d[c].astype(str).replace("nan", "NA")
    return d


modelo = CatBoostClassifier(**P_CAT, iterations=N_ARB, loss_function="Logloss", random_seed=SEED, verbose=200, thread_count=8)
modelo.fit(Pool(para_cat(train), train["var_rpta_alt"], cat_features=CAT))
modelo.save_model(str(ROOT / "models" / "catboost_v2.cbm"))

p = modelo.predict_proba(Pool(para_cat(oot), cat_features=CAT))[:, 1]
ss = pd.read_csv(ROOT / "data" / "sample_submission.csv", usecols=["ID"])
res = ss.merge(pd.DataFrame({"ID": oot.ID.astype(str), "Prob_uno": p}), on="ID", how="left")
res["var_rpta_alt"] = (res.Prob_uno >= UMBRAL).astype(int)
assert res.Prob_uno.notna().all() and len(res) == len(ss)
res[["ID", "var_rpta_alt"]].to_csv(OUT / "submission_v2_catboost.csv", index=False)
res[["ID", "var_rpta_alt", "Prob_uno"]].round({"Prob_uno": 5}).to_csv(OUT / "resultado_prueba_v2_catboost.csv", index=False, encoding="utf-8")
print(f"listo | % predicho 1: {res.var_rpta_alt.mean():.3f} | prob media: {res.Prob_uno.mean():.3f}")
