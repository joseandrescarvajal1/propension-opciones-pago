"""Descarga los datos de la competencia de Kaggle a la carpeta data/.

Uso:
    python src/download_data.py            # descarga si faltan archivos
    python src/download_data.py --force    # vuelve a descargar todo

Credenciales: variable KAGGLE_API_TOKEN en el archivo .env de la raiz del
proyecto (ver .env.example) o en el entorno.
"""

from __future__ import annotations

import argparse
import os
import sys
import zipfile
from pathlib import Path

from dotenv import load_dotenv

COMPETITION = "prueba-analitica-modelo-opciones-de-pago-season-3"
ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT_DIR / "data"

load_dotenv(ROOT_DIR / ".env")

EXPECTED_FILES = [
    "Metadata.xlsx",
    "prueba_op_base_pivot_var_rpta_alt_enmascarado_oot.csv",
    "prueba_op_base_pivot_var_rpta_alt_enmascarado_trtest.csv",
    "prueba_op_maestra_cuotas_pagos_mes_hist_enmascarado_completa.csv",
    "prueba_op_master_customer_data_enmascarado_completa.csv",
    "prueba_op_probabilidad_oblig_base_hist_enmascarado_completa.csv",
    "sample_submission.csv",
]


def missing_files(data_dir: Path) -> list[str]:
    return [f for f in EXPECTED_FILES if not (data_dir / f).exists()]


def download(data_dir: Path, force: bool) -> None:
    if not os.environ.get("KAGGLE_API_TOKEN"):
        raise SystemExit(
            "No se encontro KAGGLE_API_TOKEN. Copia .env.example a .env y coloca tu token de Kaggle."
        )

    from kaggle.api.kaggle_api_extended import KaggleApi

    api = KaggleApi()
    api.authenticate()

    print(f"Descargando '{COMPETITION}' en {data_dir} ...")
    api.competition_download_files(COMPETITION, path=str(data_dir), force=force, quiet=False)

    for zip_path in data_dir.glob("*.zip"):
        print(f"Descomprimiendo {zip_path.name} ...")
        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(data_dir)
        zip_path.unlink()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--force", action="store_true", help="vuelve a descargar aunque los archivos ya existan")
    args = parser.parse_args()

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    faltantes = missing_files(DATA_DIR)
    if not faltantes and not args.force:
        print(f"Todos los archivos ya existen en {DATA_DIR}. Usa --force para volver a descargar.")
        return 0

    if args.force:
        for f in EXPECTED_FILES:
            (DATA_DIR / f).unlink(missing_ok=True)

    download(DATA_DIR, force=args.force)

    faltantes = missing_files(DATA_DIR)
    if faltantes:
        print("ERROR: faltan archivos tras la descarga:", ", ".join(faltantes), file=sys.stderr)
        return 1

    print("\nArchivos en data/:")
    for f in EXPECTED_FILES:
        size_mb = (DATA_DIR / f).stat().st_size / 1e6
        print(f"  {f:<70} {size_mb:8.1f} MB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
