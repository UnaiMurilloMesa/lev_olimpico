"""Caso de uso principal: analizar un vídeo de levantamiento."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from app.services.pose.estimator import PoseEstimator
from app.services.pose.renderer import FrameRenderer
from app.services.video.processor import VideoPoseProcessor
from app.services.video.transcoder import VideoTranscoder

logger = logging.getLogger(__name__)

RAW_OUTPUT_SUFFIX = "_raw.mp4"
FINAL_OUTPUT_NAME = "analysis.mp4"


@dataclass(frozen=True, slots=True)
class AnalysisResult:
    """Resultado del análisis de un vídeo."""

    video_path: Path
    processed_frames: int
    detected_frames: int
    detection_ratio: float
    duration_seconds: float


class AnalysisService:
    """Coordina el análisis completo de un vídeo de levantamiento."""

    def __init__(
        self,
        estimator: PoseEstimator,
        renderer: FrameRenderer,
        transcoder: VideoTranscoder,
    ) -> None:
        """Crea el servicio con sus colaboradores."""
        self._processor = VideoPoseProcessor(estimator, renderer)
        self._transcoder = transcoder

    def analyze(self, source: Path, workspace: Path) -> AnalysisResult:
        """Analiza un vídeo y deja el resultado listo para su descarga.

        Args:
            source: Vídeo original subido por el usuario.
            workspace: Directorio de trabajo exclusivo de este análisis.

        Returns:
            El resumen del análisis, con la ruta del vídeo final.
        """
        workspace.mkdir(parents=True, exist_ok=True)
        raw_output = workspace / f"{source.stem}{RAW_OUTPUT_SUFFIX}"
        final_output = workspace / FINAL_OUTPUT_NAME

        logger.info("Iniciando análisis de %s", source.name)
        processing = self._processor.process(source, raw_output)
        self._transcoder.to_android_compatible(raw_output, final_output)
        raw_output.unlink(missing_ok=True)

        return AnalysisResult(
            video_path=final_output,
            processed_frames=processing.processed_frames,
            detected_frames=processing.detected_frames,
            detection_ratio=processing.detection_ratio,
            duration_seconds=processing.metadata.duration_seconds,
        )