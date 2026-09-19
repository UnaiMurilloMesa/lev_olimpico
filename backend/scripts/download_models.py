"""Descarga el modelo de MediaPipe necesario para el análisis de pose."""

import sys
import urllib.request
from pathlib import Path

MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/pose_landmarker/"
    "pose_landmarker_heavy/float16/1/pose_landmarker_heavy.task"
)
MODELS_DIR = Path(__file__).resolve().parents[1] / "models"
MODEL_PATH = MODELS_DIR / "pose_landmarker_heavy.task"


def main() -> int:
    """Descarga el modelo si todavía no existe en disco."""
    if MODEL_PATH.is_file():
        print(f"El modelo ya existe en {MODEL_PATH}, se omite la descarga.")
        return 0

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    print("Descargando pose_landmarker_heavy.task...")
    urllib.request.urlretrieve(MODEL_URL, MODEL_PATH)
    print(f"Modelo guardado en {MODEL_PATH} ({MODEL_PATH.stat().st_size / 1e6:.1f} MB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())