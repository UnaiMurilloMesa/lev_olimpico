"""Conversión entre coordenadas normalizadas y unidades físicas."""

from __future__ import annotations

from dataclasses import dataclass

from app.domain.landmarks import PoseFrame, PoseLandmarkId
from app.domain.sequence import PoseSequence

MIN_ATHLETE_HEIGHT_M = 1.20
MAX_ATHLETE_HEIGHT_M = 2.30

# Proporción de la estatura que queda por encima de los ojos. La referencia
# visible más alta y fiable en MediaPipe es la línea de los ojos, ya que la
# coronilla no se detecta; el resto se estima con esta constante
# antropométrica.
EYE_TO_CROWN_RATIO = 0.06


class InvalidHeightError(ValueError):
    """La estatura indicada está fuera del rango admisible."""


@dataclass(frozen=True, slots=True)
class BodyScale:
    """Factor de conversión entre unidades normalizadas y metros."""

    meters_per_unit: float

    def to_meters(self, normalized_distance: float) -> float:
        """Convierte una distancia normalizada a metros."""
        return normalized_distance * self.meters_per_unit


def validate_height(height_m: float) -> float:
    """Comprueba que la estatura es plausible.

    Raises:
        InvalidHeightError: Si queda fuera del rango admisible.
    """
    if not MIN_ATHLETE_HEIGHT_M <= height_m <= MAX_ATHLETE_HEIGHT_M:
        raise InvalidHeightError(
            f"La estatura debe estar entre {MIN_ATHLETE_HEIGHT_M} y {MAX_ATHLETE_HEIGHT_M} m."
        )
    return height_m


def visible_body_span(frame: PoseFrame) -> float | None:
    """Altura ocupada por el cuerpo en el fotograma, en unidades normalizadas.

    Se mide entre la línea de los ojos y el punto más bajo de los pies, y se
    extrapola hasta la coronilla.
    """
    if not frame.is_detected:
        return None

    eyes = [
        frame.landmarks[PoseLandmarkId.LEFT_EYE].y,
        frame.landmarks[PoseLandmarkId.RIGHT_EYE].y,
    ]
    feet = [
        frame.landmarks[PoseLandmarkId.LEFT_HEEL].y,
        frame.landmarks[PoseLandmarkId.RIGHT_HEEL].y,
        frame.landmarks[PoseLandmarkId.LEFT_FOOT_INDEX].y,
        frame.landmarks[PoseLandmarkId.RIGHT_FOOT_INDEX].y,
    ]

    span = max(feet) - min(eyes)
    if span <= 0:
        return None
    return span / (1 - EYE_TO_CROWN_RATIO)


def estimate_scale(sequence: PoseSequence, height_m: float) -> BodyScale | None:
    """Calcula la escala usando el fotograma en que el atleta está más erguido.

    La postura más extendida es la que mejor aproxima la estatura real, ya que
    en flexión la proyección del cuerpo sobre la imagen se acorta.
    """
    validate_height(height_m)

    spans = [
        span
        for span in (visible_body_span(frame) for frame in sequence.frames)
        if span is not None
    ]
    if not spans:
        return None

    return BodyScale(meters_per_unit=height_m / max(spans))