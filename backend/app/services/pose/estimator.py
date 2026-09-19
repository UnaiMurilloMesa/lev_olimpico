"""Estimación de puntos corporales sobre fotogramas de vídeo."""

from __future__ import annotations

from pathlib import Path
from types import TracebackType
from typing import Protocol

import mediapipe as mp
import numpy as np
from mediapipe.tasks.python import BaseOptions
from mediapipe.tasks.python.vision import PoseLandmarker, PoseLandmarkerOptions, RunningMode

from app.domain.landmarks import Landmark, PoseFrame


class PoseEstimator(Protocol):
    """Contrato de cualquier estimador de pose sobre fotogramas."""

    def estimate(self, frame_bgr: np.ndarray, index: int, timestamp_ms: int) -> PoseFrame:
        """Detecta los puntos corporales presentes en un fotograma."""
        ...


class MediaPipePoseEstimator:
    """Estimador de pose basado en el PoseLandmarker de MediaPipe."""

    def __init__(
        self,
        model_path: Path,
        min_detection_confidence: float = 0.5,
        min_tracking_confidence: float = 0.5,
    ) -> None:
        """Crea el estimador a partir del modelo .task indicado.

        Raises:
            FileNotFoundError: Si el modelo no existe en la ruta dada.
        """
        if not model_path.is_file():
            raise FileNotFoundError(f"No se encontró el modelo de pose en {model_path}")

        options = PoseLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=str(model_path)),
            running_mode=RunningMode.VIDEO,
            num_poses=1,
            min_pose_detection_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence,
        )
        self._landmarker = PoseLandmarker.create_from_options(options)

    def estimate(self, frame_bgr: np.ndarray, index: int, timestamp_ms: int) -> PoseFrame:
        """Detecta los puntos corporales presentes en un fotograma BGR."""
        rgb = np.ascontiguousarray(frame_bgr[:, :, ::-1])
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        result = self._landmarker.detect_for_video(mp_image, timestamp_ms)

        if not result.pose_landmarks:
            return PoseFrame(index=index, timestamp_ms=timestamp_ms, landmarks=())

        landmarks = tuple(
            Landmark(
                x=point.x,
                y=point.y,
                z=point.z,
                visibility=point.visibility if point.visibility is not None else 0.0,
            )
            for point in result.pose_landmarks[0]
        )
        return PoseFrame(index=index, timestamp_ms=timestamp_ms, landmarks=landmarks)

    def close(self) -> None:
        """Libera los recursos nativos del detector."""
        self._landmarker.close()

    def __enter__(self) -> MediaPipePoseEstimator:
        """Permite usar el estimador como gestor de contexto."""
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Cierra el detector al salir del contexto."""
        self.close()