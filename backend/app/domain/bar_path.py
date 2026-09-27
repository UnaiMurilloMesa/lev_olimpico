"""Trayectoria de la barra durante el levantamiento."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from app.domain.landmarks import PoseFrame, PoseLandmarkId
from app.domain.sequence import PoseSequence

# Umbrales de desviación horizontal, expresados como fracción del recorrido
# vertical total de la barra.
EXCELLENT_DEVIATION = 0.20
ACCEPTABLE_DEVIATION = 0.30


class PathQuality(StrEnum):
    """Valoración de la verticalidad de la trayectoria de la barra."""

    EXCELLENT = "excellent"
    ACCEPTABLE = "acceptable"
    POOR = "poor"

    @classmethod
    def from_deviation(cls, ratio: float) -> PathQuality:
        """Clasifica una desviación relativa en un nivel de calidad."""
        if ratio <= EXCELLENT_DEVIATION:
            return cls.EXCELLENT
        if ratio <= ACCEPTABLE_DEVIATION:
            return cls.ACCEPTABLE
        return cls.POOR


@dataclass(frozen=True, slots=True)
class BarPoint:
    """Posición estimada de la barra en un fotograma."""

    frame_index: int
    x: float
    y: float


@dataclass(frozen=True, slots=True)
class BarPath:
    """Trayectoria completa de la barra a lo largo del levantamiento."""

    points: tuple[BarPoint, ...]

    def __len__(self) -> int:
        """Número de posiciones registradas."""
        return len(self.points)

    @property
    def vertical_range(self) -> float:
        """Recorrido vertical total de la barra, en coordenadas normalizadas."""
        if not self.points:
            return 0.0
        ys = [point.y for point in self.points]
        return max(ys) - min(ys)

    @property
    def horizontal_deviation(self) -> float:
        """Amplitud horizontal máxima de la trayectoria."""
        if not self.points:
            return 0.0
        xs = [point.x for point in self.points]
        return max(xs) - min(xs)

    @property
    def deviation_ratio(self) -> float:
        """Desviación horizontal relativa al recorrido vertical.

        Normalizar por el recorrido vertical hace la medida independiente de
        la distancia a la cámara y de la estatura del levantador.
        """
        if self.vertical_range == 0:
            return 0.0
        return self.horizontal_deviation / self.vertical_range

    @property
    def quality(self) -> PathQuality:
        """Valoración global de la verticalidad de la trayectoria."""
        return PathQuality.from_deviation(self.deviation_ratio)


def bar_position(frame: PoseFrame) -> BarPoint | None:
    """Estima la posición de la barra como punto medio entre ambas muñecas.

    Devuelve `None` si el fotograma no tiene pose detectada.
    """
    if not frame.is_detected:
        return None

    left = frame.landmarks[PoseLandmarkId.LEFT_WRIST]
    right = frame.landmarks[PoseLandmarkId.RIGHT_WRIST]
    return BarPoint(
        frame_index=frame.index,
        x=(left.x + right.x) / 2,
        y=(left.y + right.y) / 2,
    )


def extract_bar_path(sequence: PoseSequence) -> BarPath:
    """Construye la trayectoria de la barra a partir de una secuencia de poses."""
    points = tuple(
        position
        for position in (bar_position(frame) for frame in sequence.frames)
        if position is not None
    )
    return BarPath(points=points)