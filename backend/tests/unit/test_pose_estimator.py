"""Pruebas del estimador de pose que no requieren el modelo real."""

from pathlib import Path

import pytest

from app.services.pose.estimator import MediaPipePoseEstimator


def test_falla_si_el_modelo_no_existe(tmp_path: Path) -> None:
    ruta_inexistente = tmp_path / "no_existe.task"

    with pytest.raises(FileNotFoundError, match="no_existe.task"):
        MediaPipePoseEstimator(model_path=ruta_inexistente)