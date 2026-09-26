"""Pruebas del saneado de FPS y del submuestreo de fotogramas."""

import pytest

from app.services.video.metadata import DEFAULT_FPS, MAX_FPS, frame_step_for, sanitize_fps


@pytest.mark.parametrize(
    ("entrada", "esperado"),
    [
        (30.0, 30.0),
        (29.97, 30.0),
        (92.121, 92.0),
        (59.94, 60.0),
    ],
)
def test_redondea_los_fps_fraccionarios(entrada: float, esperado: float) -> None:
    assert sanitize_fps(entrada) == esperado


@pytest.mark.parametrize("entrada", [0.0, -1.0])
def test_usa_el_valor_por_defecto_si_los_fps_no_son_validos(entrada: float) -> None:
    assert sanitize_fps(entrada) == DEFAULT_FPS


def test_acota_los_fps_excesivos() -> None:
    assert sanitize_fps(1000.0) == MAX_FPS


@pytest.mark.parametrize(
    ("fps", "esperado"),
    [(30.0, 1), (60.0, 1), (92.0, 2), (120.0, 2), (240.0, 4)],
)
def test_calcula_el_paso_de_submuestreo(fps: float, esperado: int) -> None:
    assert frame_step_for(fps) == esperado


def test_los_fps_efectivos_nunca_superan_el_limite() -> None:
    for fps in (30.0, 59.9, 60.0, 92.121, 120.0, 240.0):
        assert fps / frame_step_for(fps) <= 60.0 + 1e-9