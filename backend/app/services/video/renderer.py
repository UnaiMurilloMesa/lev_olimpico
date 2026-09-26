"""Segunda pasada: escritura del vídeo con la pose ya suavizada dibujada."""

from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path

import cv2

from app.domain.sequence import PoseSequence
from app.services.pose.renderer import FrameRenderer
from app.services.video.metadata import (
    OUTPUT_FOURCC,
    VideoMetadata,
    VideoProcessingError,
    frame_step_for,
    sanitize_fps,
)

logger = logging.getLogger(__name__)

RendererFactory = Callable[[PoseSequence], FrameRenderer]


class PoseVideoRenderer:
    """Vuelve a recorrer el vídeo y dibuja sobre él la secuencia suavizada."""

    def __init__(self, renderer_factory: RendererFactory) -> None:
        """Crea el renderizador de vídeo sobre una factoria de dibujantes."""
        self._renderer_factory = renderer_factory

    def render(
        self, source: Path, destination: Path, sequence: PoseSequence, metadata: VideoMetadata
    ) -> Path:
        """Escribe en `destination` el vídeo con la pose dibujada.

        Raises:
            VideoProcessingError: Si el vídeo no se puede leer o escribir.
        """
        capture = cv2.VideoCapture(str(source))
        if not capture.isOpened():
            raise VideoProcessingError(f"No se pudo abrir el vídeo de entrada: {source}")

        try:
            writer = self._open_writer(destination, metadata)
            try:
                self._write_frames(capture, writer, sequence)
            finally:
                writer.release()
        finally:
            capture.release()

        logger.info("Vídeo renderizado en %s", destination)
        return destination

    def _write_frames(
        self,
        capture: cv2.VideoCapture,
        writer: cv2.VideoWriter,
        sequence: PoseSequence,
    ) -> None:
        """Dibuja cada pose sobre su fotograma correspondiente."""
        renderer = self._renderer_factory(sequence)
        step = frame_step_for(sanitize_fps(capture.get(cv2.CAP_PROP_FPS)))
        read_index = 0
        written = 0

        while written < len(sequence):
            ok, frame = capture.read()
            if not ok:
                break

            if read_index % step == 0:
                writer.write(renderer.render(frame, sequence.frames[written]))
                written += 1

            read_index += 1

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