"""Pruebas de la extracción de capturas por fase."""

from pathlib import Path

import cv2
import numpy as np
import pytest

from app.domain.landmarks import Landmark, PoseFrame
from app.domain.lift_window import LiftWindow
from app.domain.phases import LiftPhase, build_breakdown
from app.domain.sequence import PoseSequence
from app.services.video.metadata import VideoProcessingError
from app.services.video.snapshots import PhaseSnapshotExtractor

WIDTH, HEIGHT, FRAMES, FPS = 64, 48, 30, 30.0


class PassthroughRenderer:
    """Dibujante que marca el fotograma para poder reconocerlo."""

    def render(self, frame_bgr: np.ndarray, pose: PoseFrame) -> np.ndarray:
        canvas = frame_bgr.copy()
        canvas[0, 0] = (255, 255, 255)
        return canvas


@pytest.fixture
def video(tmp_path: Path) -> Path:
    path = tmp_path / "entrada.mp4"
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter.fourcc(*"mp4v"), FPS, (WIDTH, HEIGHT))
    for index in range(FRAMES):
        writer.write(np.full((HEIGHT, WIDTH, 3), index * 5, dtype=np.uint8))
    writer.release()
    return path


def _lift() -> PoseSequence:
    frames = tuple(
        PoseFrame(
            index=index,
            timestamp_ms=int(index * 1000 / FPS),
            landmarks=tuple(Landmark(0.5, 0.5, 0.0, 1.0) for _ in range(33)),
        )
        for index in range(FRAMES)
    )
    return PoseSequence(frames=frames, fps=FPS)


def _extractor() -> PhaseSnapshotExtractor:
    return PhaseSnapshotExtractor(lambda _: PassthroughRenderer())


def test_genera_una_captura_por_fase(video: Path, tmp_path: Path) -> None:
    breakdown = build_breakdown(LiftWindow(0, 29), (5, 11, 17, 23))

    snapshots = _extractor().extract(video, tmp_path / "shots", _lift(), breakdown)

    assert len(snapshots) == 5
    assert {shot.phase for shot in snapshots} == set(LiftPhase)


def test_las_capturas_existen_en_disco(video: Path, tmp_path: Path) -> None:
    breakdown = build_breakdown(LiftWindow(0, 29), (5, 11, 17, 23))

    snapshots = _extractor().extract(video, tmp_path / "shots", _lift(), breakdown)

    for shot in snapshots:
        assert shot.path.is_file()
        assert shot.path.stat().st_size > 0


def test_cada_captura_corresponde_al_inicio_de_su_fase(video: Path, tmp_path: Path) -> None:
    breakdown = build_breakdown(LiftWindow(0, 29), (5, 11, 17, 23))

    snapshots = _extractor().extract(video, tmp_path / "shots", _lift(), breakdown)
    indices = {shot.phase: shot.frame_index for shot in snapshots}

    assert indices[LiftPhase.FIRST_PULL] == 0
    assert indices[LiftPhase.TRANSITION] == 6
    assert indices[LiftPhase.SECOND_PULL] == 12


def test_las_capturas_llevan_la_pose_dibujada(video: Path, tmp_path: Path) -> None:
    breakdown = build_breakdown(LiftWindow(0, 29), (5, 11, 17, 23))

    snapshots = _extractor().extract(video, tmp_path / "shots", _lift(), breakdown)
    imagen = cv2.imread(str(snapshots[0].path))

    assert imagen is not None
    assert tuple(imagen[0, 0]) != (0, 0, 0)


def test_informa_del_instante_de_cada_captura(video: Path, tmp_path: Path) -> None:
    breakdown = build_breakdown(LiftWindow(0, 29), (5, 11, 17, 23))

    snapshots = _extractor().extract(video, tmp_path / "shots", _lift(), breakdown)
    tiempos = {shot.phase: shot.time_seconds for shot in snapshots}

    assert tiempos[LiftPhase.TRANSITION] == pytest.approx(0.2)


def test_un_video_inexistente_falla(tmp_path: Path) -> None:
    breakdown = build_breakdown(LiftWindow(0, 29), (5, 11, 17, 23))

    with pytest.raises(VideoProcessingError):
        _extractor().extract(tmp_path / "no.mp4", tmp_path / "shots", _lift(), breakdown)


def test_genera_captura_para_fases_que_comparten_inicio(video: Path, tmp_path: Path) -> None:
    """Dos eventos detectados en el mismo fotograma no deben perder capturas."""
    breakdown = build_breakdown(LiftWindow(0, 29), (5, 11, 17, 17))

    snapshots = _extractor().extract(video, tmp_path / "shots", _lift(), breakdown)

    assert len(snapshots) == 5