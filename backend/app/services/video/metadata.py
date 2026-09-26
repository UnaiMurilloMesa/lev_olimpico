"""Procesado de un vídeo completo: detección de pose y renderizado."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

from app.services.pose.estimator import PoseEstimator
from app.services.pose.renderer import FrameRenderer

logger = logging.getLogger(__name__)

DEFAULT_FPS = 30.0
MIN_FPS = 1.0
MAX_FPS = 240.0
TARGET_MAX_FPS = 60.0
OUTPUT_FOURCC = "mp4v"

def sanitize_fps(raw_fps: float) -> float:
    """Normaliza la tasa de fotogramas leída de un vídeo.

    Los vídeos de móvil suelen declarar tasas fraccionarias (p. ej. 92.121 fps)
    que el estándar MPEG-4 no admite como base de tiempo, por lo que se redondea
    a un entero y se acota a un rango razonable.
    """
    if not raw_fps or raw_fps <= 0:
        return DEFAULT_FPS
    return float(min(max(round(raw_fps), MIN_FPS), MAX_FPS))

def frame_step_for(fps: float, target_max_fps: float = TARGET_MAX_FPS) -> int:
    """Calcula cada cuántos fotogramas se conserva uno.

    Los vídeos grabados a alta tasa (cámara lenta de móvil) se submuestrean
    para mantener el coste de análisis acotado y una ventana de suavizado
    comparable entre grabaciones.
    """
    if fps <= target_max_fps:
        return 1
    return int(np.ceil(fps / target_max_fps))


class VideoProcessingError(RuntimeError):
    """Error irrecuperable durante el procesado de un vídeo."""


@dataclass(frozen=True, slots=True)
class VideoMetadata:
    """Propiedades básicas de un vídeo."""

    width: int
    height: int
    fps: float
    frame_count: int

    @property
    def duration_seconds(self) -> float:
        """Duración aproximada del vídeo en segundos."""
        return self.frame_count / self.fps if self.fps else 0.0