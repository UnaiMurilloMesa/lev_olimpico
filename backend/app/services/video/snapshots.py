"""Extracción de capturas representativas de cada fase."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import cv2

from app.domain.phases import LiftPhase, PhaseBreakdown
from app.domain.sequence import PoseSequence
from app.services.pose.renderer import FrameRenderer
from app.services.video.metadata import VideoProcessingError, frame_step_for, sanitize_fps
from app.services.video.renderer import RendererFactory

logger = logging.getLogger(__name__)

SNAPSHOT_QUALITY = 90


@dataclass(frozen=True, slots=True)
class PhaseSnapshot:
    """Captura asociada al inicio de una fase."""

    phase: LiftPhase
    frame_index: int
    time_seconds: float
    path: Path


class PhaseSnapshotExtractor:
    """Extrae una imagen por fase con la pose dibujada encima."""

    def __init__(self, renderer_factory: RendererFactory) -> None:
        """Crea el extractor sobre la misma factoría que usa el vídeo.

        Reutilizar la factoría garantiza que las capturas lleven exactamente
        las mismas capas que el vídeo analizado.
        """
        self._renderer_factory = renderer_factory

    def extract(
        self,
        source: Path,
        destination_dir: Path,
        lift: PoseSequence,
        breakdown: PhaseBreakdown,
    ) -> tuple[PhaseSnapshot, ...]:
        """Guarda una captura por fase y devuelve sus descriptores.

        Raises:
            VideoProcessingError: Si el vídeo no se puede abrir.
        """
        capture = cv2.VideoCapture(str(source))
        if not capture.isOpened():
            raise VideoProcessingError(f"No se pudo abrir el vídeo de entrada: {source}")

        try:
            return self._extract_from(capture, destination_dir, lift, breakdown)
        finally:
            capture.release()

    def _extract_from(
        self,
        capture: cv2.VideoCapture,
        destination_dir: Path,
        lift: PoseSequence,
        breakdown: PhaseBreakdown,
    ) -> tuple[PhaseSnapshot, ...]:
        """Recorre el vídeo una vez guardando los fotogramas buscados."""
        destination_dir.mkdir(parents=True, exist_ok=True)
        renderer: FrameRenderer = self._renderer_factory(lift)

        wanted: dict[int, list[LiftPhase]] = {}
        for span in breakdown.spans:
            wanted.setdefault(span.start_index, []).append(span.phase)
        poses = {frame.index: frame for frame in lift.frames}
        step = frame_step_for(sanitize_fps(capture.get(cv2.CAP_PROP_FPS)))

        snapshots: list[PhaseSnapshot] = []
        read_index = 0
        sequence_index = 0

        while wanted:
            ok, frame = capture.read()
            if not ok:
                break

            if read_index % step == 0:
                for phase in wanted.pop(sequence_index, []):
                    if sequence_index in poses:
                        snapshots.append(
                            self._save(
                                renderer.render(frame, poses[sequence_index]),
                                destination_dir,
                                phase,
                                sequence_index,
                                lift.fps,
                            )
                        )
                sequence_index += 1

            read_index += 1

        logger.info("Capturas generadas: %d de %d fases", len(snapshots), len(breakdown))
        return tuple(snapshots)

    @staticmethod
    def _save(
        image: cv2.typing.MatLike,
        destination_dir: Path,
        phase: LiftPhase,
        frame_index: int,
        fps: float,
    ) -> PhaseSnapshot:
        """Escribe una captura en disco."""
        path = destination_dir / f"{phase.value}.jpg"
        cv2.imwrite(str(path), image, [cv2.IMWRITE_JPEG_QUALITY, SNAPSHOT_QUALITY])
        return PhaseSnapshot(
            phase=phase,
            frame_index=frame_index,
            time_seconds=frame_index / fps if fps else 0.0,
            path=path,
        )