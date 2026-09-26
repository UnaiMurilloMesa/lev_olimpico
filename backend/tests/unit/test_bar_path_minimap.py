"""Pruebas del panel de trayectoria de la barra."""

import numpy as np

from app.domain.bar_path import BarPath, BarPoint
from app.domain.landmarks import Landmark, PoseFrame
from app.services.pose.bar_path_minimap import BarPathMinimapRenderer, MinimapStyle

WIDTH, HEIGHT = 400, 600


def _image() -> np.ndarray:
    return np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)


def _pose(index: int) -> PoseFrame:
    return PoseFrame(
        index=index,
        timestamp_ms=index * 33,
        landmarks=tuple(Landmark(0.5, 0.5, 0.0, 1.0) for _ in range(33)),
    )


def _path(*coords: tuple[float, float]) -> BarPath:
    return BarPath(
        points=tuple(BarPoint(frame_index=i, x=x, y=y) for i, (x, y) in enumerate(coords))
    )


def test_no_modifica_el_fotograma_original() -> None:
    original = _image()

    BarPathMinimapRenderer(_path((0.5, 0.9), (0.5, 0.1))).render(original, _pose(0))

    assert not original.any()


def test_dibuja_el_panel_en_la_esquina_inferior_derecha() -> None:
    renderer = BarPathMinimapRenderer(_path((0.5, 0.9), (0.5, 0.5), (0.5, 0.1)))

    resultado = renderer.render(_image(), _pose(1))

    assert resultado[HEIGHT - 30 :, WIDTH - 30 :].any()
    assert not resultado[:100, :100].any()


def test_el_panel_sigue_visible_fuera_del_levantamiento() -> None:
    """Aunque el fotograma no pertenezca a la trayectoria, el panel se dibuja."""
    renderer = BarPathMinimapRenderer(_path((0.5, 0.9), (0.5, 0.1)))

    resultado = renderer.render(_image(), _pose(999))

    assert resultado.any()


def test_una_trayectoria_vacia_no_dibuja_nada() -> None:
    resultado = BarPathMinimapRenderer(BarPath(points=())).render(_image(), _pose(0))

    assert not resultado.any()


def test_el_panel_respeta_el_tamano_configurado() -> None:
    estilo = MinimapStyle(width_ratio=0.5, margin_ratio=0.0, aspect_ratio=1.0)
    renderer = BarPathMinimapRenderer(_path((0.5, 0.9), (0.5, 0.1)), estilo)

    resultado = renderer.render(_image(), _pose(0))

    # Con la mitad del ancho y sin margen, el panel llega hasta el centro.
    assert resultado[HEIGHT - 10, WIDTH // 2 + 10].any()
    assert not resultado[HEIGHT - 10, WIDTH // 2 - 30].any()


def test_una_trayectoria_vertical_no_se_estira_a_lo_ancho() -> None:
    """El reescalado no debe convertir un tirón recto en un zigzag."""
    recta = _path((0.5, 0.9), (0.5, 0.5), (0.5, 0.1))
    renderer = BarPathMinimapRenderer(recta)

    panel = renderer._panel_rect(WIDTH, HEIGHT)
    puntos = [renderer._to_panel(p.x, p.y, panel) for p in recta.points]

    columnas = {x for x, _ in puntos}
    filas = {y for _, y in puntos}
    assert len(columnas) == 1
    assert len(filas) == 3
