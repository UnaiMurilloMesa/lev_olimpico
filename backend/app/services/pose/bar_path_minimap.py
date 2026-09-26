"""Panel fijo con la trayectoria completa de la barra."""

from __future__ import annotations

from dataclasses import dataclass, field

import cv2
import numpy as np

from app.domain.bar_path import BarPath, PathQuality
from app.domain.landmarks import PoseFrame
from app.services.pose.bar_path_renderer import (
    COLOR_ACCEPTABLE,
    COLOR_EXCELLENT,
    COLOR_POOR,
)


PANEL_TITLE = "Bar Path"
TITLE_COLOR = (230, 230, 230)
PANEL_BACKGROUND = (30, 30, 30)
PANEL_BORDER = (120, 120, 120)
TRACE_BACKGROUND = (70, 70, 70)


def _default_palette() -> dict[PathQuality, tuple[int, int, int]]:
    return {
        PathQuality.EXCELLENT: COLOR_EXCELLENT,
        PathQuality.ACCEPTABLE: COLOR_ACCEPTABLE,
        PathQuality.POOR: COLOR_POOR,
    }


@dataclass(frozen=True)
class MinimapStyle:
    """Parámetros visuales del panel de trayectoria."""

    title_scale: float = 0.4
    title_thickness: int = 1
    title_margin: int = 6
    width_ratio: float = 0.18
    margin_ratio: float = 0.02
    aspect_ratio: float = 1.6
    padding: int = 8
    opacity: float = 0.75
    thickness: int = 2
    marker_radius: int = 3
    palette: dict[PathQuality, tuple[int, int, int]] = field(default_factory=_default_palette)


class BarPathMinimapRenderer:
    """Dibuja en una esquina la trayectoria completa de la barra.

    A diferencia del rastro sobre el vídeo, el panel muestra el recorrido
    entero desde el primer fotograma y resalta la posición actual, de modo que
    la forma de la trayectoria sigue visible una vez terminado el levantamiento.
    """

    def __init__(self, path: BarPath, style: MinimapStyle | None = None) -> None:
        """Crea el panel para una trayectoria concreta."""
        self._path = path
        self._style = style or MinimapStyle()
        self._color = self._style.palette[path.quality]
        self._by_frame = {point.frame_index: index for index, point in enumerate(path.points)}
        self._bounds = self._compute_bounds()

    def render(self, frame_bgr: np.ndarray, pose: PoseFrame) -> np.ndarray:
        """Devuelve el fotograma con el panel dibujado en la esquina."""
        canvas = frame_bgr.copy()
        if not self._path.points:
            return canvas

        panel = self._panel_rect(canvas.shape[1], canvas.shape[0])
        self._draw_panel_background(canvas, panel)
        self._draw_title(canvas, panel)
        self._draw_trace(canvas, panel)
        self._draw_current_position(canvas, panel, pose.index)
        return canvas

    def _panel_rect(self, width: int, height: int) -> tuple[int, int, int, int]:
        """Calcula el rectángulo del panel en la esquina inferior derecha."""
        style = self._style
        panel_width = int(width * style.width_ratio)
        panel_height = int(panel_width * style.aspect_ratio)
        margin = int(width * style.margin_ratio)

        x2 = width - margin
        y2 = height - margin
        return x2 - panel_width, y2 - panel_height, x2, y2

    def _draw_panel_background(
        self, canvas: np.ndarray, panel: tuple[int, int, int, int]
    ) -> None:
        """Dibuja el fondo semitransparente del panel."""
        x1, y1, x2, y2 = panel
        overlay = canvas.copy()
        cv2.rectangle(overlay, (x1, y1), (x2, y2), PANEL_BACKGROUND, thickness=-1)
        cv2.addWeighted(
            overlay, self._style.opacity, canvas, 1 - self._style.opacity, 0, dst=canvas
        )
        cv2.rectangle(canvas, (x1, y1), (x2, y2), PANEL_BORDER, thickness=1)

    def _draw_trace(self, canvas: np.ndarray, panel: tuple[int, int, int, int]) -> None:
        """Dibuja la trayectoria completa dentro del panel."""
        points = [self._to_panel(point.x, point.y, panel) for point in self._path.points]
        if len(points) > 1:
            cv2.polylines(
                canvas,
                [np.array(points, dtype=np.int32)],
                isClosed=False,
                color=TRACE_BACKGROUND,
                thickness=self._style.thickness + 2,
                lineType=cv2.LINE_AA,
            )
            cv2.polylines(
                canvas,
                [np.array(points, dtype=np.int32)],
                isClosed=False,
                color=self._color,
                thickness=self._style.thickness,
                lineType=cv2.LINE_AA,
            )

    def _draw_current_position(
        self, canvas: np.ndarray, panel: tuple[int, int, int, int], frame_index: int
    ) -> None:
        """Resalta dónde está la barra en el fotograma actual."""
        position = self._by_frame.get(frame_index)
        if position is None:
            return
        point = self._path.points[position]
        cv2.circle(
            canvas,
            self._to_panel(point.x, point.y, panel),
            self._style.marker_radius,
            (255, 255, 255),
            thickness=-1,
        )

    def _to_panel(
        self, x: float, y: float, panel: tuple[int, int, int, int]
    ) -> tuple[int, int]:
        """Proyecta una posición de la barra a coordenadas del panel.

        La trayectoria se reescala a los límites del recorrido real, de modo
        que ocupe todo el panel con independencia de dónde estuviera la barra
        dentro del encuadre.
        """
        x1, y1, x2, y2 = panel
        pad = self._style.padding
        min_x, max_x, min_y, max_y = self._bounds

        span_x = max_x - min_x or 1.0
        span_y = max_y - min_y or 1.0
        rel_x = (x - min_x) / span_x
        rel_y = (y - min_y) / span_y

        inner_width = (x2 - x1) - 2 * pad
        inner_height = (y2 - y1) - 2 * pad
        return x1 + pad + round(rel_x * inner_width), y1 + pad + round(rel_y * inner_height)

    def _compute_bounds(self) -> tuple[float, float, float, float]:
        """Calcula los límites de la trayectoria, con margen mínimo en x.

        Sin un ancho mínimo, una trayectoria casi perfectamente vertical se
        estiraría hasta ocupar todo el panel y aparentaría una desviación
        enorme.
        """
        if not self._path.points:
            return 0.0, 1.0, 0.0, 1.0

        xs = [point.x for point in self._path.points]
        ys = [point.y for point in self._path.points]
        center_x = (min(xs) + max(xs)) / 2
        half_span = max((max(xs) - min(xs)) / 2, (max(ys) - min(ys)) / 4)

        return center_x - half_span, center_x + half_span, min(ys), max(ys)

    def _draw_title(self, canvas: np.ndarray, panel: tuple[int, int, int, int]) -> None:
        """Escribe el rótulo del panel sobre su borde superior."""
        x1, y1, x2, _ = panel
        style = self._style

        (text_width, text_height), _ = cv2.getTextSize(
            PANEL_TITLE, cv2.FONT_HERSHEY_SIMPLEX, style.title_scale, style.title_thickness
        )
        origin_x = x1 + ((x2 - x1) - text_width) // 2
        origin_y = y1 - style.title_margin

        # Si el panel está pegado al borde superior, el rótulo se dibuja dentro.
        if origin_y - text_height < 0:
            origin_y = y1 + text_height + style.title_margin

        cv2.putText(
            canvas,
            PANEL_TITLE,
            (origin_x, origin_y),
            cv2.FONT_HERSHEY_SIMPLEX,
            style.title_scale,
            TITLE_COLOR,
            style.title_thickness,
            cv2.LINE_AA,
        )