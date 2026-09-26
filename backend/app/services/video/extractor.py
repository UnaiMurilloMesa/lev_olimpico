"""Primera pasada: extracción de las poses de un vídeo."""

from __future__ import annotations

import logging
from pathlib import Path

import cv2

from app.domain.landmarks import PoseFrame
from app.domain.sequence import PoseSequence
from app.services.pose.estimator import PoseEstimator
from app.services.video.processor import (
    VideoMetadata,
    VideoProcessingError,
    frame_step_for,
    sanitize_fps,
)

logger = logging.getLogger(__name__)


class PoseExtractor:
    """Recorre un vídeo y acumula las poses detectadas en cada fotograma."""

    def __init__(self, estimator: PoseEstimator) -> None:
        """Crea el extractor sobre el estimador indicado."""
        self._estimator = estimator

    def extract(self, source: Path) -> tuple[PoseSequence, VideoMetadata]:
        """Devuelve la secuencia de poses y los metadatos efectivos del vídeo.

        Raises:
            VideoProcessingError: Si el vídeo no se puede abrir.
        """
        capture = cv2.VideoCapture(str(source))
        if not capture.isOpened():
            raise VideoProcessingError(f"No se pudo abrir el vídeo de entrada: {source}")

        try:
            return self._extract_from(capture)
        finally:
            capture.release()

    def _extract_from(
        self, capture: cv2.VideoCapture
    ) -> tuple[PoseSequence, VideoMetadata]:
        """Recorre la captura conservando uno de cada `step` fotogramas."""
        source_fps = sanitize_fps(capture.get(cv2.CAP_PROP_FPS))
        step = frame_step_for(source_fps)
        effective_fps = source_fps / step

        if step > 1:
            logger.info(
                "Submuestreo activo: %.1f fps de origen, se analiza a %.1f fps",
                source_fps,
                effective_fps,
            )

        frames: list[PoseFrame] = []
        read_index = 0

        while True:
            ok, frame = capture.read()
            if not ok:
                break

            if read_index % step == 0:
                kept = len(frames)
                timestamp_ms = int(kept * 1000 / effective_fps)
                frames.append(self._estimator.estimate(frame, kept, timestamp_ms))

            read_index += 1

        metadata = VideoMetadata(
            width=int(capture.get(cv2.CAP_PROP_FRAME_WIDTH)),
            height=int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT)),
            fps=effective_fps,
            frame_count=len(frames),
        )
        sequence = PoseSequence(frames=tuple(frames), fps=effective_fps)

        logger.info(
            "Extracción completada: %d fotogramas, pose detectada en %.1f%%",
            len(sequence),
            sequence.detection_ratio * 100,
        )
        return sequence, metadata