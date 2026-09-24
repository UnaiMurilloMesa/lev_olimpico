"""Procesado de un vídeo completo: detección de pose y renderizado."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import cv2

from app.services.pose.estimator import PoseEstimator
from app.services.pose.renderer import FrameRenderer

logger = logging.getLogger(__name__)

DEFAULT_FPS = 30.0
MIN_FPS = 1.0
MAX_FPS = 240.0
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


@dataclass(frozen=True, slots=True)
class ProcessingResult:
    """Resumen del procesado de un vídeo."""

    output_path: Path
    metadata: VideoMetadata
    processed_frames: int
    detected_frames: int

    @property
    def detection_ratio(self) -> float:
        """Proporción de fotogramas en los que se detectó pose."""
        return self.detected_frames / self.processed_frames if self.processed_frames else 0.0


class VideoPoseProcessor:
    """Aplica la estimación de pose a todos los fotogramas de un vídeo."""

    def __init__(self, estimator: PoseEstimator, renderer: FrameRenderer) -> None:
        """Crea el procesador con el estimador y el renderizador indicados."""
        self._estimator = estimator
        self._renderer = renderer

    def process(self, source: Path, destination: Path) -> ProcessingResult:
        """Genera en `destination` una copia de `source` con la pose dibujada.

        Raises:
            VideoProcessingError: Si el vídeo no se puede leer o escribir.
        """
        capture = self._open_capture(source)
        try:
            metadata = self._read_metadata(capture)
            writer = self._open_writer(destination, metadata)
            try:
                return self._process_frames(capture, writer, metadata, destination)
            finally:
                writer.release()
        finally:
            capture.release()

    def _process_frames(
        self,
        capture: cv2.VideoCapture,
        writer: cv2.VideoWriter,
        metadata: VideoMetadata,
        destination: Path,
    ) -> ProcessingResult:
        """Recorre el vídeo fotograma a fotograma y escribe la salida."""
        processed = 0
        detected = 0

        while True:
            ok, frame = capture.read()
            if not ok:
                break

            timestamp_ms = self._timestamp_for(processed, metadata.fps)
            pose = self._estimator.estimate(frame, processed, timestamp_ms)
            writer.write(self._renderer.render(frame, pose))

            processed += 1
            if pose.is_detected:
                detected += 1

        logger.info(
            "Vídeo procesado: %d fotogramas, pose detectada en %d (%.1f%%)",
            processed,
            detected,
            100 * detected / processed if processed else 0.0,
        )
        return ProcessingResult(
            output_path=destination,
            metadata=metadata,
            processed_frames=processed,
            detected_frames=detected,
        )

    @staticmethod
    def _timestamp_for(frame_index: int, fps: float) -> int:
        """Calcula el timestamp en milisegundos de un fotograma.

        Se deriva del índice y no del reloj del vídeo porque MediaPipe exige
        marcas de tiempo estrictamente crecientes en modo VIDEO.
        """
        return int(frame_index * 1000 / fps)

    @staticmethod
    def _open_capture(source: Path) -> cv2.VideoCapture:
        """Abre el vídeo de entrada."""
        capture = cv2.VideoCapture(str(source))
        if not capture.isOpened():
            raise VideoProcessingError(f"No se pudo abrir el vídeo de entrada: {source}")
        return capture

    @staticmethod
    def _read_metadata(capture: cv2.VideoCapture) -> VideoMetadata:
        """Extrae las propiedades del vídeo abierto."""
        raw_fps = capture.get(cv2.CAP_PROP_FPS)
        fps = sanitize_fps(raw_fps)
        if fps != raw_fps:
            logger.warning("FPS ajustados de %s a %s por compatibilidad", raw_fps, fps)
        return VideoMetadata(
            width=int(capture.get(cv2.CAP_PROP_FRAME_WIDTH)),
            height=int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT)),
            fps=fps,
            frame_count=int(capture.get(cv2.CAP_PROP_FRAME_COUNT)),
        )

    @staticmethod
    def _open_writer(destination: Path, metadata: VideoMetadata) -> cv2.VideoWriter:
        """Abre el escritor del vídeo de salida."""
        destination.parent.mkdir(parents=True, exist_ok=True)
        writer = cv2.VideoWriter(
            str(destination),
            cv2.VideoWriter.fourcc(*OUTPUT_FOURCC),
            metadata.fps,
            (metadata.width, metadata.height),
        )
        if not writer.isOpened():
            raise VideoProcessingError(f"No se pudo crear el vídeo de salida: {destination}")
        return writer