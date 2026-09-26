"""Dibujo de la trayectoria de la barra sobre el fotograma."""

from __future__ import annotations

from dataclasses import dataclass, field

import cv2
import numpy as np

from app.domain.bar_path import BarPath, PathQuality
from app.domain.landmarks import PoseFrame

COLOR_EXCELLENT = (0, 200, 0)
COLOR_ACCEPTABLE = (0, 200, 255)
COLOR_POOR = (0, 0, 255)


def _default_palette() -> dict[PathQuality, tuple[int, int, int]]:
    return {
        PathQuality.EXCELLENT: COLOR_EXCELLENT,
        PathQuality.ACCEPTABLE: COLOR_ACCEPTABLE,
        PathQuality.POOR: COLOR_POOR,
    }


@dataclass(frozen=True)
class BarPathStyle:
    """Parámetros visuales de la trayectoria de la barra."""

    thickness: int = 2
    marker_radius: int = 5
    palette: dict[PathQuality, tuple[int, int, int]] = field(default_factory=_default_palette)


class BarPathRenderer:
    """Dibuja el recorrido de la barra hasta el fotograma actual.

    El color refleja la verticalidad global del levantamiento: cuanto más
    recta es la trayectoria, mejor se considera la ejecución.
    """

    def __init__(self, path: BarPath, style: BarPathStyle | None = None) -> None:
        """Crea el renderizador para una trayectoria concreta."""
        self._path = path
        self._style = style or BarPathStyle()
        self._color = self._style.palette[path.quality]
        self._by_frame = {point.frame_index: index for index, point in enumerate(path.points)}

    def render(self, frame_bgr: np.ndarray, pose: PoseFrame) -> np.ndarray:
        """Devuelve el fotograma con el rastro de la barra dibujado."""
        canvas = frame_bgr.copy()
        position = self._by_frame.get(pose.index)
        if position is None:
            return canvas

        height, width = canvas.shape[:2]
        trail = [
            (round(point.x * width), round(point.y * height))
            for point in self._path.points[: position + 1]
        ]

        if len(trail) > 1:
            cv2.polylines(
                canvas,
                [np.array(trail, dtype=np.int32)],
                isClosed=False,
                color=self._color,
                thickness=self._style.thickness,
                lineType=cv2.LINE_AA,
            )

        cv2.circle(canvas, trail[-1], self._style.marker_radius, self._color, thickness=-1)
        return canvas