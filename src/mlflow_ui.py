"""Abre la interfaz web de MLflow apuntando a la base del proyecto.

Uso (desde cualquier carpeta):
    python src/mlflow_ui.py            # http://127.0.0.1:5000
    python src/mlflow_ui.py --port 5001
"""

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "mlflow.db"

if __name__ == "__main__":
    port = sys.argv[sys.argv.index("--port") + 1] if "--port" in sys.argv else "5000"
    if not DB.exists():
        sys.exit(f"No existe {DB}. Ejecuta primero un notebook que registre experimentos.")
    os.environ.setdefault("MLFLOW_DISABLE_AGENT_HINT", "1")
    print(f"MLflow UI -> http://127.0.0.1:{port}   (base: {DB})")
    subprocess.run([sys.executable, "-m", "mlflow", "ui", "--backend-store-uri", f"sqlite:///{DB.as_posix()}", "--port", port], cwd=ROOT)
