"""Dibujo del esqueleto detectado sobre los fotogramas del vídeo."""

from dataclasses import dataclass, field
from typing import Protocol

import cv2
import numpy as np

from app.domain.landmarks import ConfidenceLevel, PoseFrame
from app.domain.pose_connections import POSE_CONNECTIONS

# Colores en formato BGR, el que usa OpenCV.
COLOR_HIGH_CONFIDENCE = (0, 200, 0)
COLOR_MEDIUM_CONFIDENCE = (0, 200, 255)
COLOR_LOW_CONFIDENCE = (0, 0, 255)


def _default_palette() -> dict[ConfidenceLevel, tuple[int, int, int]]:
    return {
        ConfidenceLevel.HIGH: COLOR_HIGH_CONFIDENCE,
        ConfidenceLevel.MEDIUM: COLOR_MEDIUM_CONFIDENCE,
        ConfidenceLevel.LOW: COLOR_LOW_CONFIDENCE,
    }


@dataclass(frozen=True)
class SkeletonStyle:
    """Parámetros visuales del esqueleto dibujado."""

    point_radius: int = 4
    line_thickness: int = 2
    palette: dict[ConfidenceLevel, tuple[int, int, int]] = field(default_factory=_default_palette)

    def color_for(self, level: ConfidenceLevel) -> tuple[int, int, int]:
        """Devuelve el color asociado a un nivel de confianza."""
        return self.palette[level]


class FrameRenderer(Protocol):
    """Contrato de cualquier componente que dibuje sobre un fotograma."""

    def render(self, frame_bgr: np.ndarray, pose: PoseFrame) -> np.ndarray:
        """Devuelve una copia del fotograma con la información dibujada."""
        ...


class SkeletonRenderer:
    """Dibuja los puntos corporales y sus conexiones coloreados por confianza."""

    def __init__(self, style: SkeletonStyle | None = None) -> None:
        """Crea el renderizador con el estilo indicado o el predeterminado."""
        self._style = style or SkeletonStyle()

    def render(self, frame_bgr: np.ndarray, pose: PoseFrame) -> np.ndarray:
        """Devuelve una copia del fotograma con el esqueleto dibujado."""
        canvas = frame_bgr.copy()
        if not pose.is_detected:
            return canvas

        height, width = canvas.shape[:2]
        points = [landmark.to_pixels(width, height) for landmark in pose.landmarks]

        self._draw_connections(canvas, pose, points)
        self._draw_points(canvas, pose, points)
        return canvas

    def _draw_connections(
        self,
        canvas: np.ndarray,
        pose: PoseFrame,
        points: list[tuple[int, int]],
    ) -> None:
        """Dibuja los segmentos que unen los puntos corporales."""
        for start, end in POSE_CONNECTIONS:
            level = self._weakest_confidence(
                pose.landmarks[start].confidence, pose.landmarks[end].confidence
            )
            cv2.line(
                canvas,
                points[start],
                points[end],
                self._style.color_for(level),
                self._style.line_thickness,
            )

    def _draw_points(
        self,
        canvas: np.ndarray,
        pose: PoseFrame,
        points: list[tuple[int, int]],
    ) -> None:
        """Dibuja cada punto corporal con el color de su nivel de confianza."""
        for landmark, point in zip(pose.landmarks, points, strict=True):
            cv2.circle(
                canvas,
                point,
                self._style.point_radius,
                self._style.color_for(landmark.confidence),
                thickness=-1,
            )

    @staticmethod
    def _weakest_confidence(first: ConfidenceLevel, second: ConfidenceLevel) -> ConfidenceLevel:
        """Devuelve el menor de dos niveles de confianza."""
        order = (ConfidenceLevel.LOW, ConfidenceLevel.MEDIUM, ConfidenceLevel.HIGH)
        return min(first, second, key=order.index)