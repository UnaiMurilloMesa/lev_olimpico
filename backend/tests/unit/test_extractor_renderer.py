"""Pruebas de la extracción y el renderizado en dos pasadas."""

from pathlib import Path

import cv2
import numpy as np
import pytest

from app.domain.landmarks import Landmark, PoseFrame
from app.domain.sequence import PoseSequence
from app.services.video.extractor import PoseExtractor
from app.services.video.metadata import VideoProcessingError
from app.services.video.renderer import PoseVideoRenderer

WIDTH, HEIGHT, FRAMES = 64, 48, 12


class FakeEstimator:
    """Estimador que devuelve una pose fija y registra los timestamps."""

    def __init__(self, detected: bool = True) -> None:
        self.timestamps: list[int] = []
        self._detected = detected

    def estimate(self, frame_bgr: np.ndarray, index: int, timestamp_ms: int) -> PoseFrame:
        self.timestamps.append(timestamp_ms)
        landmarks = tuple(Landmark(0.5, 0.5, 0.0, 1.0) for _ in range(33)) if self._detected else ()
        return PoseFrame(index=index, timestamp_ms=timestamp_ms, landmarks=landmarks)


class SpyRenderer:
    """Dibujante que cuenta invocaciones sin alterar el fotograma."""

    def __init__(self) -> None:
        self.poses: list[PoseFrame] = []

    def render(self, frame_bgr: np.ndarray, pose: PoseFrame) -> np.ndarray:
        self.poses.append(pose)
        return frame_bgr


def _video(path: Path, fps: float) -> Path:
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter.fourcc(*"mp4v"), fps, (WIDTH, HEIGHT))
    for index in range(FRAMES):
        writer.write(np.full((HEIGHT, WIDTH, 3), index * 10, dtype=np.uint8))
    writer.release()
    return path


@pytest.fixture
def video_30fps(tmp_path: Path) -> Path:
    return _video(tmp_path / "entrada30.mp4", fps=30.0)


@pytest.fixture
def video_120fps(tmp_path: Path) -> Path:
    return _video(tmp_path / "entrada120.mp4", fps=120.0)


def test_extrae_una_pose_por_fotograma(video_30fps: Path) -> None:
    sequence, metadata = PoseExtractor(FakeEstimator()).extract(video_30fps)

    assert len(sequence) == FRAMES
    assert metadata.fps == pytest.approx(30.0)


def test_los_timestamps_son_estrictamente_crecientes(video_30fps: Path) -> None:
    estimator = FakeEstimator()

    PoseExtractor(estimator).extract(video_30fps)

    assert estimator.timestamps == sorted(set(estimator.timestamps))


def test_submuestrea_los_videos_de_alta_tasa(video_120fps: Path) -> None:
    sequence, metadata = PoseExtractor(FakeEstimator()).extract(video_120fps)

    assert metadata.fps == pytest.approx(60.0)
    assert len(sequence) == FRAMES // 2


def test_informa_de_la_proporcion_de_deteccion(video_30fps: Path) -> None:
    sequence, _ = PoseExtractor(FakeEstimator(detected=False)).extract(video_30fps)

    assert sequence.detection_ratio == 0.0


def test_extraer_un_video_inexistente_falla(tmp_path: Path) -> None:
    with pytest.raises(VideoProcessingError, match="entrada"):
        PoseExtractor(FakeEstimator()).extract(tmp_path / "inexistente.mp4")


def test_el_renderizado_dibuja_la_secuencia_suministrada(video_30fps: Path, tmp_path: Path) -> None:
    sequence, metadata = PoseExtractor(FakeEstimator()).extract(video_30fps)
    spy = SpyRenderer()

    PoseVideoRenderer(lambda _: spy).render(
        video_30fps, tmp_path / "salida.mp4", sequence, metadata
    )

    assert len(spy.poses) == len(sequence)


def test_el_renderizado_genera_el_fichero(video_30fps: Path, tmp_path: Path) -> None:
    sequence, metadata = PoseExtractor(FakeEstimator()).extract(video_30fps)
    destino = tmp_path / "sub" / "salida.mp4"

    PoseVideoRenderer(lambda _: SpyRenderer()).render(video_30fps, destino, sequence, metadata)

    assert destino.is_file()
    assert destino.stat().st_size > 0


def test_las_dos_pasadas_recorren_los_mismos_fotogramas(video_120fps: Path, tmp_path: Path) -> None:
    """El submuestreo debe coincidir en extracción y renderizado."""
    sequence, metadata = PoseExtractor(FakeEstimator()).extract(video_120fps)
    spy = SpyRenderer()

    PoseVideoRenderer(lambda _: spy).render(
        video_120fps, tmp_path / "salida.mp4", sequence, metadata
    )

    assert [pose.index for pose in spy.poses] == [frame.index for frame in sequence.frames]


def test_renderizar_con_una_secuencia_vacia_no_falla(video_30fps: Path, tmp_path: Path) -> None:
    sequence, metadata = PoseExtractor(FakeEstimator()).extract(video_30fps)
    vacia = PoseSequence(frames=(), fps=metadata.fps)

    PoseVideoRenderer(lambda _: SpyRenderer()).render(
        video_30fps, tmp_path / "salida.mp4", vacia, metadata
    )
