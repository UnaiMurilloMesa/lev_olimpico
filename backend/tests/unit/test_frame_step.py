"""Pruebas del submuestreo de fotogramas."""

import pytest

from app.services.video.processor import frame_step_for


@pytest.mark.parametrize(
    ("fps", "esperado"),
    [
        (30.0, 1),
        (60.0, 1),
        (92.0, 2),
        (120.0, 2),
        (240.0, 4),
    ],
)
def test_calcula_el_paso_de_submuestreo(fps: float, esperado: int) -> None:
    assert frame_step_for(fps) == esperado


def test_los_fps_efectivos_nunca_superan_el_limite() -> None:
    for fps in (30.0, 59.9, 60.0, 92.121, 120.0, 240.0):
        assert fps / frame_step_for(fps) <= 60.0 + 1e-9