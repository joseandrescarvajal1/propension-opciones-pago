"""Registro de experimentos con MLflow: un solo experimento para todo el proyecto.

Estructura en MLflow:
    Experimento "opciones_pago"
      └─ run padre por modelo (p. ej. "04_xgboost")
           ├─ busqueda_01 ... busqueda_NN   (una combinación de hiperparámetros cada uno)
           └─ final                          (métricas en test, umbral, variables, figuras, modelo)

Backend: SQLite en <raíz>/mlflow.db. Artefactos en <raíz>/mlruns/. Sin servidor.

Uso desde un notebook:
    import sys; sys.path.insert(0, str(ROOT / "src"))
    from tracking import grupo, registrar_busqueda, registrar_final, registrar_kaggle, resumen

    with grupo("04_xgboost", notebook="04_xgboost_catboost", modelo="xgboost", validacion="aleatoria_80_10_10"):
        for i, params in enumerate(combinaciones):
            registrar_busqueda(i + 1, params, {"f1_val": ..., "auc_val": ...})
        run_id = registrar_final(params_best, metricas_test, umbral, FEATS, modelo=m, flavor="xgboost", figuras={"pr": fig})
    registrar_kaggle(run_id, 0.70694, submission_id=56152634)

Interfaz web:  python src/mlflow_ui.py   ->  http://127.0.0.1:5000
"""

from __future__ import annotations

import json
import os
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import mlflow
import pandas as pd
from mlflow.tracking import MlflowClient

os.environ.setdefault("MLFLOW_DISABLE_AGENT_HINT", "1")

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "mlflow.db"
MLRUNS = ROOT / "mlruns"
TRACKING_URI = f"sqlite:///{DB.as_posix()}"
EXPERIMENTO = "opciones_pago"


def _conectar() -> str:
    """Fija el backend y devuelve el id del experimento único del proyecto."""
    MLRUNS.mkdir(exist_ok=True)
    mlflow.set_tracking_uri(TRACKING_URI)
    exp = mlflow.get_experiment_by_name(EXPERIMENTO)
    if exp is None:
        return mlflow.create_experiment(EXPERIMENTO, artifact_location=MLRUNS.as_uri())
    mlflow.set_experiment(EXPERIMENTO)
    return exp.experiment_id


def _str(params: dict[str, Any]) -> dict[str, str]:
    return {k: str(v) for k, v in params.items()}


@contextmanager
def grupo(nombre: str, **tags: Any) -> Iterator[str]:
    """Run padre que agrupa la búsqueda y el final de un modelo. Los tags se heredan a los hijos."""
    _conectar()
    with mlflow.start_run(run_name=nombre) as padre:
        mlflow.set_tags({"tipo": "grupo", **_str(tags)})
        _CTX["padre"] = nombre
        _CTX["padre_id"] = padre.info.run_id
        _CTX["tags"] = _str(tags)
        try:
            yield padre.info.run_id
        finally:
            _CTX.clear()


_CTX: dict[str, Any] = {}


def registrar_busqueda(indice: int, params: dict[str, Any], metricas: dict[str, float]) -> str:
    """Una combinación de hiperparámetros evaluada en validación (run hijo)."""
    with mlflow.start_run(run_name=f"busqueda_{indice:02d}", nested=True) as run:
        mlflow.log_params(_str(params))
        mlflow.log_metrics({k: float(v) for k, v in metricas.items()})
        mlflow.set_tags({"tipo": "busqueda", "grupo": _CTX.get("padre", ""), **_CTX.get("tags", {})})
        _resumir_en_padre(busqueda=metricas)
        return run.info.run_id


def registrar_final(
    params: dict[str, Any],
    metricas: dict[str, float],
    umbral: float,
    features: list[str],
    modelo: Any | None = None,
    flavor: str | None = None,
    ruta_modelo: str | Path | None = None,
    figuras: dict[str, Any] | None = None,
    tags: dict[str, Any] | None = None,
) -> str:
    """Modelo final del grupo (run hijo): parámetros, métricas, umbral, variables, figuras y modelo."""
    with mlflow.start_run(run_name="final", nested=True) as run:
        mlflow.log_params(_str(params))
        mlflow.log_param("n_features", len(features))
        mlflow.log_metrics({k: float(v) for k, v in metricas.items()})
        mlflow.log_metric("umbral", float(umbral))
        mlflow.set_tags({"tipo": "final", "grupo": _CTX.get("padre", ""), **_CTX.get("tags", {}), **_str(tags or {})})
        _resumir_en_padre(final_params={**_str(params), "n_features": len(features)}, final_metricas={**metricas, "umbral": umbral})

        with tempfile.TemporaryDirectory() as tmp:
            info = Path(tmp) / "modelo_info.json"
            info.write_text(json.dumps({"umbral": float(umbral), "features": list(features), "flavor": flavor}, indent=2, ensure_ascii=False), encoding="utf-8")
            mlflow.log_artifact(str(info))
        for nombre_fig, fig in (figuras or {}).items():
            mlflow.log_figure(fig, f"figuras/{nombre_fig}.png")
        if ruta_modelo is not None:
            mlflow.log_artifact(str(ruta_modelo), artifact_path="modelo_archivo")
        if modelo is not None and flavor is not None:
            mod = {"lightgbm": mlflow.lightgbm, "xgboost": mlflow.xgboost, "catboost": mlflow.catboost, "sklearn": mlflow.sklearn}[flavor]
            try:
                mod.log_model(modelo, name="modelo")
            except TypeError:
                mod.log_model(modelo, artifact_path="modelo")
        return run.info.run_id


def _resumir_en_padre(busqueda: dict[str, float] | None = None, final_params: dict[str, str] | None = None, final_metricas: dict[str, float] | None = None) -> None:
    """Copia al run padre lo esencial de los hijos, para que la tabla de la interfaz sea legible sin desplegar."""
    pid = _CTX.get("padre_id")
    if not pid:
        return
    cli = MlflowClient()
    if busqueda and "f1_val" in busqueda:
        actual = cli.get_run(pid).data.metrics.get("mejor_f1_val", -1.0)
        if float(busqueda["f1_val"]) > actual:
            cli.log_metric(pid, "mejor_f1_val", float(busqueda["f1_val"]))
        cli.log_metric(pid, "n_busquedas", cli.get_run(pid).data.metrics.get("n_busquedas", 0) + 1)
    if final_params:
        for k, v in final_params.items():
            cli.log_param(pid, k, v)
    if final_metricas:
        for k, v in final_metricas.items():
            cli.log_metric(pid, k, float(v))


def registrar_kaggle(run_id: str, f1_publico: float, submission_id: str | int | None = None) -> None:
    """Agrega a un run existente el F1 público de Kaggle."""
    _conectar()
    cli = MlflowClient()
    ids = [run_id]
    padre = cli.get_run(run_id).data.tags.get("mlflow.parentRunId")
    if padre:
        ids.append(padre)
    for rid in ids:
        cli.log_metric(rid, "f1_kaggle_publico", float(f1_publico))
        if submission_id is not None:
            cli.set_tag(rid, "kaggle_submission_id", str(submission_id))


def anexar(run_id: str, metricas: dict[str, float] | None = None, tags: dict[str, Any] | None = None,
           figuras: dict[str, Any] | None = None, artefactos: dict[str, str | Path] | None = None) -> None:
    """Agrega a un run ya cerrado métricas, tags, figuras y archivos, sin abrirlo. Métricas y tags se copian al padre."""
    _conectar()
    cli = MlflowClient()
    padre = cli.get_run(run_id).data.tags.get("mlflow.parentRunId")
    for rid in [run_id] + ([padre] if padre else []):
        for k, v in (metricas or {}).items():
            cli.log_metric(rid, k, float(v))
        for k, v in _str(tags or {}).items():
            cli.set_tag(rid, k, v)
    for nombre, fig in (figuras or {}).items():
        cli.log_figure(run_id, fig, f"figuras/{nombre}.png")
    for carpeta, ruta in (artefactos or {}).items():
        cli.log_artifact(run_id, str(ruta), artifact_path=carpeta)


def resumen(tipo: str = "final") -> pd.DataFrame:
    """Tabla con todos los runs del proyecto de un tipo ("grupo", "busqueda", "final")."""
    exp_id = _conectar()
    df = mlflow.search_runs(experiment_ids=[exp_id], filter_string=f"tags.tipo = '{tipo}'")
    if df.empty:
        return df
    if tipo == "grupo":
        df["tags.grupo"] = df["tags.mlflow.runName"]
    cols = ["run_id", "tags.grupo", "tags.mlflow.runName"] + sorted(c for c in df.columns if c.startswith("metrics.")) + ["params.n_features", "start_time"]
    cols = [c for c in cols if c in df.columns]
    return df[cols].rename(columns=lambda c: c.replace("tags.", "").replace("metrics.", "").replace("params.", "").replace("mlflow.runName", "run")).sort_values(["grupo", "run"]).reset_index(drop=True)
