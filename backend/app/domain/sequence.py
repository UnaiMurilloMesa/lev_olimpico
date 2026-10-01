"""Secuencia temporal de poses extraídas de un vídeo."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from app.domain.landmarks import ConfidenceLevel, PoseFrame, PoseLandmarkId

# Puntos de los que depende el análisis biomecánico; la cara y los dedos se
# excluyen porque su visibilidad no afecta a los resultados.
KEY_LANDMARKS: tuple[PoseLandmarkId, ...] = (
    PoseLandmarkId.LEFT_WRIST,
    PoseLandmarkId.RIGHT_WRIST,
    PoseLandmarkId.LEFT_SHOULDER,
    PoseLandmarkId.RIGHT_SHOULDER,
    PoseLandmarkId.LEFT_HIP,
    PoseLandmarkId.RIGHT_HIP,
    PoseLandmarkId.LEFT_KNEE,
    PoseLandmarkId.RIGHT_KNEE,
    PoseLandmarkId.LEFT_ANKLE,
    PoseLandmarkId.RIGHT_ANKLE,
)

@dataclass(frozen=True, slots=True)
class PoseSequence:
    """Poses detectadas en un vídeo, en orden temporal."""

    frames: tuple[PoseFrame, ...]
    fps: float

    def __len__(self) -> int:
        """Número de fotogramas de la secuencia."""
        return len(self.frames)

    @property
    def detected_count(self) -> int:
        """Número de fotogramas con pose detectada."""
        return sum(1 for frame in self.frames if frame.is_detected)

    @property
    def detection_ratio(self) -> float:
        """Proporción de fotogramas con pose detectada."""
        return self.detected_count / len(self.frames) if self.frames else 0.0

    def coordinates_of(
        self, landmark_id: PoseLandmarkId
    ) -> list[tuple[float, float, float] | None]:
        """Devuelve la trayectoria de un punto a lo largo del vídeo.

        Los fotogramas sin pose detectada se representan como `None` en la
        posición correspondiente, para que el suavizador sepa dónde hay huecos.
        """
        return [
            (frame.landmarks[landmark_id].x,
             frame.landmarks[landmark_id].y,
             frame.landmarks[landmark_id].z)
            if frame.is_detected
            else None
            for frame in self.frames
        ]

    def window_size_for(self, milliseconds: int) -> int:
        """Traduce una ventana temporal a un número impar de fotogramas.

        Savitzky-Golay exige una ventana impar.
        """
        size = max(3, round(self.fps * milliseconds / 1000))
        return size if size % 2 == 1 else size + 1


    def replacing_frames(self, frames: tuple[PoseFrame, ...]) -> PoseSequence:
        """Devuelve una secuencia nueva con los fotogramas indicados."""
        return PoseSequence(frames=frames, fps=self.fps)

    
    def tracking_quality(self, landmark_ids: Sequence[PoseLandmarkId]) -> float:
        """Proporción de puntos relevantes detectados con alta confianza.

        A diferencia de `detection_ratio`, que solo indica si hubo pose, esta
        medida refleja la fiabilidad real del rastreo: el modelo devuelve una
        pose casi siempre, aunque los puntos estén mal situados.
        """
        total = 0
        reliable = 0

        for frame in self.frames:
            if not frame.is_detected:
                total += len(landmark_ids)
                continue
            for landmark_id in landmark_ids:
                total += 1
                if frame.landmarks[landmark_id].confidence is ConfidenceLevel.HIGH:
                    reliable += 1

        return reliable / total if total else 0.0