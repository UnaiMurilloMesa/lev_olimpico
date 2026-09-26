"""Caso de uso principal: analizar un vídeo de levantamiento."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from app.services.pose.smoother import PoseSmoother
from app.services.video.extractor import PoseExtractor
from app.services.video.renderer import PoseVideoRenderer
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
    """Coordina el análisis completo de un vídeo de levantamiento.

    El proceso consta de tres fases: extracción de las poses, suavizado
    temporal de las trayectorias y renderizado del vídeo con la pose ya
    suavizada. El suavizado necesita la secuencia completa, incluidos los
    fotogramas posteriores a cada instante, de ahí que no pueda hacerse en
    una única pasada sobre el vídeo.
    """

    def __init__(
        self,
        extractor: PoseExtractor,
        smoother: PoseSmoother,
        video_renderer: PoseVideoRenderer,
        transcoder: VideoTranscoder,
    ) -> None:
        """Crea el servicio con sus colaboradores."""
        self._extractor = extractor
        self._smoother = smoother
        self._video_renderer = video_renderer
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
        sequence, metadata = self._extractor.extract(source)
        smoothed = self._smoother.smooth(sequence)
        self._video_renderer.render(source, raw_output, smoothed, metadata)
        self._transcoder.to_android_compatible(raw_output, final_output)
        raw_output.unlink(missing_ok=True)

        return AnalysisResult(
            video_path=final_output,
            processed_frames=len(smoothed),
            detected_frames=smoothed.detected_count,
            detection_ratio=smoothed.detection_ratio,
            duration_seconds=metadata.duration_seconds,
        )