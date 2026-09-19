"""Pruebas del servicio de análisis con dobles de prueba."""

from pathlib import Path

import numpy as np
import pytest

from app.domain.landmarks import Landmark, PoseFrame
from app.services.analysis_service import FINAL_OUTPUT_NAME, AnalysisService


class FakeEstimator:
    def estimate(self, frame_bgr: np.ndarray, index: int, timestamp_ms: int) -> PoseFrame:
        landmarks = tuple(Landmark(0.5, 0.5, 0.0, 1.0) for _ in range(33))
        return PoseFrame(index=index, timestamp_ms=timestamp_ms, landmarks=landmarks)


class FakeRenderer:
    def render(self, frame_bgr: np.ndarray, pose: PoseFrame) -> np.ndarray:
        return frame_bgr


class FakeTranscoder:
    """Conversor falso que copia el contenido y registra las llamadas."""

    def __init__(self) -> None:
        self.calls: list[tuple[Path, Path]] = []

    def to_android_compatible(self, source: Path, destination: Path) -> Path:
        self.calls.append((source, destination))
        destination.write_bytes(source.read_bytes())
        return destination


@pytest.fixture
def sample_video(tmp_path: Path) -> Path:
    import cv2

    path = tmp_path / "levantamiento.mp4"
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), 30.0, (64, 48))
    for _ in range(5):
        writer.write(np.zeros((48, 64, 3), dtype=np.uint8))
    writer.release()
    return path


def _service(transcoder: FakeTranscoder) -> AnalysisService:
    return AnalysisService(FakeEstimator(), FakeRenderer(), transcoder)


def test_devuelve_el_video_final_transcodificado(sample_video: Path, tmp_path: Path) -> None:
    workspace = tmp_path / "job-1"

    result = _service(FakeTranscoder()).analyze(sample_video, workspace)

    assert result.video_path == workspace / FINAL_OUTPUT_NAME
    assert result.video_path.is_file()


def test_invoca_la_transcodificacion_una_vez(sample_video: Path, tmp_path: Path) -> None:
    transcoder = FakeTranscoder()

    _service(transcoder).analyze(sample_video, tmp_path / "job-1")

    assert len(transcoder.calls) == 1


def test_elimina_el_video_intermedio(sample_video: Path, tmp_path: Path) -> None:
    workspace = tmp_path / "job-1"

    _service(FakeTranscoder()).analyze(sample_video, workspace)

    assert list(workspace.glob("*_raw.mp4")) == []


def test_informa_de_las_estadisticas_de_deteccion(sample_video: Path, tmp_path: Path) -> None:
    result = _service(FakeTranscoder()).analyze(sample_video, tmp_path / "job-1")

    assert result.processed_frames == 5
    assert result.detected_frames == 5
    assert result.detection_ratio == pytest.approx(1.0)


def test_crea_el_directorio_de_trabajo_si_no_existe(sample_video: Path, tmp_path: Path) -> None:
    workspace = tmp_path / "nivel1" / "nivel2"

    _service(FakeTranscoder()).analyze(sample_video, workspace)

    assert workspace.is_dir()