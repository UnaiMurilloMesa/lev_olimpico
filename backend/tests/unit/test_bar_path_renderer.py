"""Pruebas del renderizado de la trayectoria de la barra."""

import numpy as np

from app.domain.bar_path import BarPath, BarPoint
from app.domain.landmarks import Landmark, PoseFrame
from app.services.pose.bar_path_renderer import (
    COLOR_EXCELLENT,
    COLOR_POOR,
    BarPathRenderer,
)

SIZE = 100


def _frame_image() -> np.ndarray:
    return np.zeros((SIZE, SIZE, 3), dtype=np.uint8)


def _pose(index: int) -> PoseFrame:
    landmarks = tuple(Landmark(0.5, 0.5, 0.0, 1.0) for _ in range(33))
    return PoseFrame(index=index, timestamp_ms=index * 33, landmarks=landmarks)


def _path(*coords: tuple[float, float]) -> BarPath:
    return BarPath(
        points=tuple(BarPoint(frame_index=i, x=x, y=y) for i, (x, y) in enumerate(coords))
    )


def test_no_modifica_el_fotograma_original() -> None:
    original = _frame_image()

    BarPathRenderer(_path((0.5, 0.9), (0.5, 0.1))).render(original, _pose(1))

    assert not original.any()


def test_una_trayectoria_vertical_se_dibuja_en_verde() -> None:
    renderer = BarPathRenderer(_path((0.5, 0.9), (0.5, 0.5), (0.5, 0.1)))

    resultado = renderer.render(_frame_image(), _pose(2))

    assert tuple(resultado[50, 50]) == COLOR_EXCELLENT


def test_una_trayectoria_desviada_se_dibuja_en_rojo() -> None:
    renderer = BarPathRenderer(_path((0.5, 0.9), (0.8, 0.5), (0.5, 0.1)))

    resultado = renderer.render(_frame_image(), _pose(1))

    assert tuple(resultado[50, 80]) == COLOR_POOR


def test_solo_dibuja_el_rastro_hasta_el_fotograma_actual() -> None:
    renderer = BarPathRenderer(_path((0.5, 0.9), (0.5, 0.5), (0.5, 0.1)))

    resultado = renderer.render(_frame_image(), _pose(0))

    # El tramo superior todavía no debe existir.
    assert not resultado[10, 50].any()


def test_un_fotograma_fuera_de_la_trayectoria_no_dibuja_nada() -> None:
    renderer = BarPathRenderer(_path((0.5, 0.9), (0.5, 0.1)))

    resultado = renderer.render(_frame_image(), _pose(99))

    assert not resultado.any()


def test_una_trayectoria_vacia_no_falla() -> None:
    resultado = BarPathRenderer(BarPath(points=())).render(_frame_image(), _pose(0))

    assert not resultado.any()