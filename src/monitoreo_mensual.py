"""Monitoreo mensual del modelo: deriva de variables (PSI), deriva de la predicción y, si hay etiqueta, desempeño real.

Referencia = datos de entrenamiento (train_fe.parquet). Actual = mes calificado (por defecto test_fe.parquet, enero 2024).
Resultados: outputs/monitoreo_<mes>.csv, una figura y un run en MLflow (grupo monitoreo_<mes>).

Uso:
    python src/monitoreo_mensual.py                      # enero 2024 con el paquete models/v4
    python src/monitoreo_mensual.py --mes 202401 --modelo models/v4 --top 30
    python src/monitoreo_mensual.py --etiquetas outputs/etiquetas_202401.csv   # cuando llegue la etiqueta real (columnas ID, var_rpta_alt)

En producción corre como job de Cloud Run programado (deploy/job_monitoreo.yaml) leyendo referencia y actual del bucket.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import matplotlib
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from inferencia import Modelo  # noqa: E402
from monitoreo import UMBRAL_ALARMA, UMBRAL_AVISO, clasificar, decidir_reentreno, desempeno_real, reporte_psi, resumen_prediccion  # noqa: E402
from tracking import anexar, grupo, registrar_final  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--mes", default="202401")
    ap.add_argument("--modelo", default=str(ROOT / "models" / "v4"))
    ap.add_argument("--referencia", default=str(ROOT / "data" / "processed" / "train_fe.parquet"))
    ap.add_argument("--actual", default=str(ROOT / "data" / "processed" / "test_fe.parquet"))
    ap.add_argument("--etiquetas", default=None, help="CSV con ID y var_rpta_alt del mes calificado, si ya existe")
    ap.add_argument("--top", type=int, default=25, help="variables que se muestran en la figura")
    args = ap.parse_args()

    modelo = Modelo.cargar(args.modelo)
    ref = pd.read_parquet(args.referencia)
    act = pd.read_parquet(args.actual)
    feats = modelo.features
    out = ROOT / "outputs"
    out.mkdir(exist_ok=True)

    # 1. deriva de variables
    tabla = reporte_psi(ref[feats], act[feats], feats)
    tabla.to_csv(out / f"monitoreo_{args.mes}.csv", index=False)
    n_alarma, n_aviso = int((tabla.estado == "alarma").sum()), int((tabla.estado == "aviso").sum())

    # 2. deriva de la predicción
    p_ref = modelo.probabilidad(ref[feats])
    p_act = modelo.probabilidad(act[feats])
    pred = resumen_prediccion(p_ref, p_act, modelo.umbral)

    # 3. desempeño real, si hay etiqueta
    real = None
    if args.etiquetas:
        et = pd.read_csv(args.etiquetas)
        m = act[["ID"]].merge(et, on="ID", how="left")
        ok = m.var_rpta_alt.notna().to_numpy()
        real = desempeno_real(m.var_rpta_alt.to_numpy()[ok].astype(int), p_act[ok], modelo.umbral)

    # figura
    d = tabla.head(args.top).iloc[::-1]
    fig, ax = plt.subplots(figsize=(12, 0.32 * len(d) + 1.5))
    ax.barh(d.variable, d.psi, color=["#e34948" if e == "alarma" else ("#eda100" if e == "aviso" else "#2a78d6") for e in d.estado], height=0.6)
    ax.axvline(UMBRAL_AVISO, color="#eda100", ls="--", lw=1)
    ax.axvline(UMBRAL_ALARMA, color="#e34948", ls="--", lw=1)
    for y_, v in zip(d.variable, d.psi):
        ax.text(v + 0.005, y_, f"{v:.3f}", va="center", fontsize=8)
    ax.set_title(f"PSI entrenamiento vs {args.mes} ({args.top} mayores) | alarma {n_alarma}, aviso {n_aviso}, estable {len(tabla) - n_alarma - n_aviso}")
    ax.set_xlabel("PSI")
    plt.tight_layout()
    fig.savefig(out / f"monitoreo_{args.mes}.png", dpi=130)

    # resumen
    print(f"Variables: {len(tabla)} | alarma {n_alarma} | aviso {n_aviso} | estable {len(tabla) - n_alarma - n_aviso}")
    print("Mayor deriva:")
    print(tabla.head(10).to_string(index=False))
    print(f"Predicción: PSI {pred['psi_probabilidad']} ({pred['estado']}) | % unos ref {pred['pct_uno_ref']:.3f} -> act {pred['pct_uno_act']:.3f}")
    print(f"  probabilidad media ref {pred['prob_media_ref']:.3f} -> act {pred['prob_media_act']:.3f}")
    if real:
        print("Desempeño real:", real, "| reentrenar:", decidir_reentreno([real["f1"]]))

    # MLflow
    metricas = {"n_variables": len(tabla), "n_alarma": n_alarma, "n_aviso": n_aviso, "psi_max": float(tabla.psi.max()), "psi_mediana": float(tabla.psi.median()),
                "psi_probabilidad": pred["psi_probabilidad"], "pct_uno_ref": pred["pct_uno_ref"], "pct_uno_act": pred["pct_uno_act"], "prob_media_ref": pred["prob_media_ref"], "prob_media_act": pred["prob_media_act"]}
    if real:
        metricas.update({f"real_{k}": v for k, v in real.items()})
    with grupo(f"monitoreo_{args.mes}", modelo=modelo.version, notebook="src/monitoreo_mensual.py", validacion="psi", particion=f"ref=train 2023-08..12 / act={args.mes}"):
        rid = registrar_final({"modelo": modelo.version, "mes": args.mes, "umbral_aviso": UMBRAL_AVISO, "umbral_alarma": UMBRAL_ALARMA, "estado_prediccion": clasificar(pred["psi_probabilidad"])},
                              metricas, modelo.umbral, feats, figuras={"psi": fig}, tags={"tipo_run": "monitoreo"})
    anexar(rid, artefactos={"monitoreo": out / f"monitoreo_{args.mes}.csv"})
    print("MLflow run:", rid)


if __name__ == "__main__":
    main()
