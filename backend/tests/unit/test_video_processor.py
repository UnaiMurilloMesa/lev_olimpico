"""Pruebas del procesador de vídeo con dobles de prueba."""

from pathlib import Path

import cv2
import numpy as np
import pytest

from app.domain.landmarks import Landmark, PoseFrame
from app.services.video.processor import VideoPoseProcessor, VideoProcessingError, DEFAULT_FPS, MAX_FPS, sanitize_fps

WIDTH, HEIGHT, FPS, FRAMES = 64, 48, 30.0, 10

@pytest.mark.parametrize(
    ("entrada", "esperado"),
    [
        (30.0, 30.0),
        (29.97, 30.0),
        (92.121, 92.0),  # Caso real: cámara lenta de móvil
        (59.94, 60.0),
    ],
)
def test_redondea_los_fps_fraccionarios(entrada: float, esperado: float) -> None:
    assert sanitize_fps(entrada) == esperado


@pytest.mark.parametrize("entrada", [0.0, -1.0])
def test_usa_el_valor_por_defecto_si_los_fps_no_son_validos(entrada: float) -> None:
    assert sanitize_fps(entrada) == DEFAULT_FPS


def test_acota_los_fps_excesivos() -> None:
    assert sanitize_fps(1000.0) == MAX_FPS


class FakeEstimator:
    """Estimador que devuelve una pose fija y registra las llamadas."""

    def __init__(self, detected: bool = True) -> None:
        self.timestamps: list[int] = []
        self._detected = detected

    def estimate(self, frame_bgr: np.ndarray, index: int, timestamp_ms: int) -> PoseFrame:
        self.timestamps.append(timestamp_ms)
        landmarks = (
            tuple(Landmark(0.5, 0.5, 0.0, 1.0) for _ in range(33)) if self._detected else ()
        )
        return PoseFrame(index=index, timestamp_ms=timestamp_ms, landmarks=landmarks)


class SpyRenderer:
    """Renderizador que cuenta invocaciones y no altera el fotograma."""

    def __init__(self) -> None:
        self.calls = 0

    def render(self, frame_bgr: np.ndarray, pose: PoseFrame) -> np.ndarray:
        self.calls += 1
        return frame_bgr


@pytest.fixture
def sample_video(tmp_path: Path) -> Path:
    """Genera un vídeo sintético de prueba."""
    path = tmp_path / "entrada.mp4"
    writer = cv2.VideoWriter(
        str(path), cv2.VideoWriter_fourcc(*"mp4v"), FPS, (WIDTH, HEIGHT)
    )
    for i in range(FRAMES):
        frame = np.full((HEIGHT, WIDTH, 3), i * 10, dtype=np.uint8)
        writer.write(frame)
    writer.release()
    return path


def test_procesa_todos_los_fotogramas(sample_video: Path, tmp_path: Path) -> None:
    renderer = SpyRenderer()
    processor = VideoPoseProcessor(FakeEstimator(), renderer)

    result = processor.process(sample_video, tmp_path / "salida.mp4")

    assert result.processed_frames == FRAMES
    assert renderer.calls == FRAMES


def test_genera_el_fichero_de_salida(sample_video: Path, tmp_path: Path) -> None:
    destino = tmp_path / "sub" / "salida.mp4"

    VideoPoseProcessor(FakeEstimator(), SpyRenderer()).process(sample_video, destino)

    assert destino.is_file()
    assert destino.stat().st_size > 0


def test_conserva_las_dimensiones_y_los_fps(sample_video: Path, tmp_path: Path) -> None:
    result = VideoPoseProcessor(FakeEstimator(), SpyRenderer()).process(
        sample_video, tmp_path / "salida.mp4"
    )

    assert (result.metadata.width, result.metadata.height) == (WIDTH, HEIGHT)
    assert result.metadata.fps == pytest.approx(FPS)


def test_los_timestamps_son_estrictamente_crecientes(
    sample_video: Path, tmp_path: Path
) -> None:
    estimator = FakeEstimator()

    VideoPoseProcessor(estimator, SpyRenderer()).process(sample_video, tmp_path / "salida.mp4")

    assert estimator.timestamps == sorted(set(estimator.timestamps))
    assert estimator.timestamps[:3] == [0, 33, 66]


def test_cuenta_los_fotogramas_sin_deteccion(sample_video: Path, tmp_path: Path) -> None:
    processor = VideoPoseProcessor(FakeEstimator(detected=False), SpyRenderer())

    result = processor.process(sample_video, tmp_path / "salida.mp4")

    assert result.detected_frames == 0
    assert result.detection_ratio == 0.0


def test_falla_si_el_video_de_entrada_no_existe(tmp_path: Path) -> None:
    processor = VideoPoseProcessor(FakeEstimator(), SpyRenderer())

    with pytest.raises(VideoProcessingError, match="entrada"):
        processor.process(tmp_path / "inexistente.mp4", tmp_path / "salida.mp4")