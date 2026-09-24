"""Modelo de dominio para los puntos corporales detectados en un fotograma."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, IntEnum

# Umbrales de confianza usados para clasificar y colorear cada punto.
HIGH_CONFIDENCE_THRESHOLD = 0.75
MEDIUM_CONFIDENCE_THRESHOLD = 0.40


class PoseLandmarkId(IntEnum):
    """Índices de los 33 puntos corporales del modelo de pose."""

    NOSE = 0
    LEFT_EYE_INNER = 1
    LEFT_EYE = 2
    LEFT_EYE_OUTER = 3
    RIGHT_EYE_INNER = 4
    RIGHT_EYE = 5
    RIGHT_EYE_OUTER = 6
    LEFT_EAR = 7
    RIGHT_EAR = 8
    MOUTH_LEFT = 9
    MOUTH_RIGHT = 10
    LEFT_SHOULDER = 11
    RIGHT_SHOULDER = 12
    LEFT_ELBOW = 13
    RIGHT_ELBOW = 14
    LEFT_WRIST = 15
    RIGHT_WRIST = 16
    LEFT_PINKY = 17
    RIGHT_PINKY = 18
    LEFT_INDEX = 19
    RIGHT_INDEX = 20
    LEFT_THUMB = 21
    RIGHT_THUMB = 22
    LEFT_HIP = 23
    RIGHT_HIP = 24
    LEFT_KNEE = 25
    RIGHT_KNEE = 26
    LEFT_ANKLE = 27
    RIGHT_ANKLE = 28
    LEFT_HEEL = 29
    RIGHT_HEEL = 30
    LEFT_FOOT_INDEX = 31
    RIGHT_FOOT_INDEX = 32


class ConfidenceLevel(Enum):
    """Nivel de fiabilidad de un punto corporal detectado."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

    @classmethod
    def from_visibility(cls, visibility: float) -> ConfidenceLevel:
        """Clasifica un valor de visibilidad en un nivel de confianza."""
        if visibility >= HIGH_CONFIDENCE_THRESHOLD:
            return cls.HIGH
        if visibility >= MEDIUM_CONFIDENCE_THRESHOLD:
            return cls.MEDIUM
        return cls.LOW


class LandmarkOrigin(Enum):
    """Procedencia del valor de un punto corporal."""

    DETECTED = "detected"
    INTERPOLATED = "interpolated"


@dataclass(frozen=True, slots=True)
class Landmark:
    """Punto corporal en coordenadas normalizadas [0, 1]."""

    x: float
    y: float
    z: float
    visibility: float
    origin: LandmarkOrigin = LandmarkOrigin.DETECTED

    @property
    def is_interpolated(self) -> bool:
        """Indica si el valor se reconstruyó a partir de fotogramas vecinos."""
        return self.origin is LandmarkOrigin.INTERPOLATED

    @property
    def confidence(self) -> ConfidenceLevel:
        """Nivel de confianza del punto.

        Un punto reconstruido nunca se considera fiable, con independencia de
        la visibilidad heredada de los fotogramas vecinos.
        """
        if self.is_interpolated:
            return ConfidenceLevel.LOW
        return ConfidenceLevel.from_visibility(self.visibility)

    def to_pixels(self, width: int, height: int) -> tuple[int, int]:
        """Convierte las coordenadas normalizadas a píxeles de la imagen."""
        return round(self.x * width), round(self.y * height)

    def moved_to(self, x: float, y: float, z: float) -> Landmark:
        """Devuelve una copia del punto en una posición distinta."""
        return Landmark(x=x, y=y, z=z, visibility=self.visibility, origin=self.origin)


@dataclass(frozen=True, slots=True)
class PoseFrame:
    """Conjunto de puntos corporales detectados en un fotograma concreto."""

    index: int
    timestamp_ms: int
    landmarks: tuple[Landmark, ...]

    @property
    def is_detected(self) -> bool:
        """Indica si se detectó una pose en el fotograma."""
        return len(self.landmarks) > 0

    def landmark(self, landmark_id: PoseLandmarkId) -> Landmark:
        """Devuelve un punto concreto del fotograma.

        Raises:
            LookupError: Si el fotograma no contiene pose detectada.
        """
        if not self.is_detected:
            raise LookupError(f"El fotograma {self.index} no contiene pose detectada.")
        return self.landmarks[landmark_id]