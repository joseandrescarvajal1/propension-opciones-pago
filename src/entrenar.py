"""Entrenamiento reproducible de extremo a extremo.

Pasos:
  1. Construye el dataset desde los CSV crudos (src/features.py) o reutiliza data/processed/*_fe.parquet.
  2. Validación temporal: entrena con 2023-08..2023-11 y mide en 2023-12 (F1, AUC, precisión, recall); fija el umbral que maximiza F1.
  3. Reentrena con los cinco meses con el mismo número de árboles.
  4. Empaqueta el modelo en models/<version>/ (modelo.txt + modelo_info.json) y escribe outputs/resultado_prueba.csv y submission.csv.
  5. Registra todo en MLflow (grupo entrenar_<version>).

Uso:
    python src/entrenar.py --version v5                 # reutiliza los parquet si existen
    python src/entrenar.py --version v5 --reconstruir   # vuelve a construir el dataset desde los CSV
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import date
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.metrics import f1_score, precision_score, recall_score, roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from features import TARGET, construir_dataset  # noqa: E402
from tracking import anexar, grupo, registrar_final  # noqa: E402

# Hiperparámetros del LightGBM ganador (notebook 07, elegido con validación temporal de 3 cortes)
PARAMS = {"objective": "binary", "learning_rate": 0.021138128828094058, "num_leaves": 105, "min_child_samples": 108, "subsample": 0.8650089137415928, "subsample_freq": 1,
          "colsample_bytree": 0.5870266456536466, "reg_lambda": 3.4052591913244687, "reg_alpha": 2.7335513967163982, "random_state": 42, "verbose": -1, "n_jobs": 8}


def mejor_umbral(y, p):
    grid = np.arange(0.20, 0.81, 0.01)
    f1s = [f1_score(y, p >= u) for u in grid]
    return float(grid[int(np.argmax(f1s))]), float(max(f1s))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--version", required=True, help="nombre del paquete, por ejemplo v5")
    ap.add_argument("--reconstruir", action="store_true", help="construir el dataset desde los CSV crudos aunque existan los parquet")
    ap.add_argument("--variables", default=str(ROOT / "configs" / "variables_modelo.json"), help="JSON con la lista de variables del modelo")
    ap.add_argument("--n-max", type=int, default=3000)
    args = ap.parse_args()

    proc = ROOT / "data" / "processed"
    out = ROOT / "outputs"
    out.mkdir(exist_ok=True)
    t0 = time.time()

    # 1. dataset
    if args.reconstruir or not (proc / "train_fe.parquet").exists():
        print("Construyendo el dataset desde los CSV crudos...")
        train, test, _ = construir_dataset(ROOT / "data", proc)
    else:
        train, test = pd.read_parquet(proc / "train_fe.parquet"), pd.read_parquet(proc / "test_fe.parquet")
    feats = json.loads(Path(args.variables).read_text(encoding="utf-8"))["modelo"]
    cat = [c for c in feats if str(train[c].dtype) == "category"]
    for c in cat:
        cats = pd.api.types.union_categoricals([train[c], test[c]]).categories
        train[c] = pd.Categorical(train[c], categories=cats)
        test[c] = pd.Categorical(test[c], categories=cats)
    y = train[TARGET]
    mes = train.fecha_var_rpta_alt
    print(f"dataset: train {len(train):,} | test {len(test):,} | variables {len(feats)} ({len(cat)} categóricas) | {time.time()-t0:.0f} s")

    # 2. validación temporal
    m_tr, m_va = mes <= 202311, mes == 202312
    val = lgb.LGBMClassifier(**PARAMS, n_estimators=args.n_max)
    val.fit(train.loc[m_tr, feats], y[m_tr], eval_set=[(train.loc[m_va, feats], y[m_va])], categorical_feature=cat, callbacks=[lgb.early_stopping(80, verbose=False)])
    p_dic = val.predict_proba(train.loc[m_va, feats])[:, 1]
    umbral, f1 = mejor_umbral(y[m_va], p_dic)
    pred = p_dic >= umbral
    met = {"f1_dic": f1, "auc_dic": float(roc_auc_score(y[m_va], p_dic)), "precision_dic": float(precision_score(y[m_va], pred)), "recall_dic": float(recall_score(y[m_va], pred)),
           "pct_pred_1_dic": float(pred.mean()), "n_arboles": int(val.best_iteration_)}
    print(f"diciembre: F1 {f1:.4f} | AUC {met['auc_dic']:.4f} | precisión {met['precision_dic']:.4f} | recall {met['recall_dic']:.4f} | umbral {umbral:.2f} | {met['n_arboles']} árboles")

    # 3. modelo final
    final = lgb.LGBMClassifier(**PARAMS, n_estimators=met["n_arboles"])
    final.fit(train[feats], y, categorical_feature=cat)
    p_oot = final.predict_proba(test[feats])[:, 1]

    # 4. paquete y archivos
    carpeta = ROOT / "models" / args.version
    carpeta.mkdir(parents=True, exist_ok=True)
    final.booster_.save_model(str(carpeta / "modelo.txt"))
    niveles = final.booster_.pandas_categorical or []
    info = {"version": args.version, "modelo": "lightgbm", "umbral": umbral, "n_features": len(feats), "features": feats, "categoricas": cat,
            "niveles_categoricas": {c: [str(x) for x in lv] for c, lv in zip(cat, niveles)}, "metricas": {k: round(v, 4) if isinstance(v, float) else v for k, v in met.items()},
            "hiperparametros": {k: v for k, v in PARAMS.items() if k not in ("verbose", "n_jobs")},
            "entrenamiento": {"script": "src/entrenar.py", "datos": "2023-08..2023-12", "validacion": "temporal: train <= 2023-11, umbral y métricas en 2023-12", "fecha": date.today().isoformat()}}
    (carpeta / "modelo_info.json").write_text(json.dumps(info, indent=2, ensure_ascii=False), encoding="utf-8")
    ss = pd.read_csv(ROOT / "data" / "sample_submission.csv", usecols=["ID"])
    res = ss.merge(pd.DataFrame({"ID": test.ID.astype(str), "Prob_uno": p_oot}), on="ID", how="left")
    res["var_rpta_alt"] = (res.Prob_uno >= umbral).astype(int)
    assert res.Prob_uno.notna().all() and len(res) == len(ss)
    res[["ID", "var_rpta_alt", "Prob_uno"]].round({"Prob_uno": 5}).to_csv(out / "resultado_prueba.csv", index=False, encoding="utf-8")
    res[["ID", "var_rpta_alt"]].to_csv(out / f"submission_{args.version}.csv", index=False)
    print(f"paquete {carpeta} | outputs/resultado_prueba.csv ({res.var_rpta_alt.mean():.1%} de unos) | {time.time()-t0:.0f} s")

    # 5. MLflow
    with grupo(f"entrenar_{args.version}", modelo="lightgbm", notebook="src/entrenar.py", validacion="temporal_dic2023", particion="train 2023-08..11 / val 2023-12"):
        rid = registrar_final(info["hiperparametros"], {**met, "pct_pred_1_oot": float(res.var_rpta_alt.mean())}, umbral, feats, modelo=final, flavor="lightgbm", ruta_modelo=carpeta / "modelo.txt",
                              tags={"paquete": str(carpeta)})
    anexar(rid, artefactos={"paquete": carpeta / "modelo_info.json", "kaggle": out / f"submission_{args.version}.csv"})
    print("MLflow run:", rid)


if __name__ == "__main__":
    main()
