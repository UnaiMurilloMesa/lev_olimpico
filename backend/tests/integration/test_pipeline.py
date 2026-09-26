"""Prueba de extremo a extremo del pipeline de análisis con dependencias reales."""

from pathlib import Path

import cv2
import numpy as np
import pytest

from app.core.config import get_settings
from app.services.analysis_service import AnalysisService
from app.services.pose.estimator import MediaPipePoseEstimator
from app.services.pose.renderer import SkeletonRenderer
from app.services.pose.smoother import SavitzkyGolaySmoother
from app.services.video.extractor import PoseExtractor
from app.services.video.renderer import PoseVideoRenderer
from app.services.video.transcoder import FfmpegTranscoder

pytestmark = pytest.mark.slow

WIDTH, HEIGHT, FPS, FRAMES = 320, 240, 30.0, 15


@pytest.fixture(scope="module")
def settings():
    return get_settings()


@pytest.fixture
def synthetic_video(tmp_path: Path) -> Path:
    """Vídeo sintético sin personas: válido para ejercitar el pipeline."""
    path = tmp_path / "prueba.mp4"
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), FPS, (WIDTH, HEIGHT))
    for i in range(FRAMES):
        frame = np.full((HEIGHT, WIDTH, 3), (i * 8) % 256, dtype=np.uint8)
        writer.write(frame)
    writer.release()
    return path


def test_el_modelo_de_pose_esta_disponible(settings) -> None:
    assert settings.pose_model_path.is_file()


def test_ffmpeg_esta_disponible() -> None:
    assert FfmpegTranscoder().is_available is True


def test_el_pipeline_completo_genera_un_video_reproducible(
    synthetic_video: Path, tmp_path: Path, settings
) -> None:
    with MediaPipePoseEstimator(settings.pose_model_path) as estimator:
        service = AnalysisService(
            extractor=PoseExtractor(estimator),
            smoother=SavitzkyGolaySmoother(),
            video_renderer=PoseVideoRenderer(SkeletonRenderer()),
            transcoder=FfmpegTranscoder(),
        )
        result = service.analyze(synthetic_video, tmp_path / "job-integracion")

    assert result.processed_frames == FRAMES
    assert result.video_path.is_file()

    capture = cv2.VideoCapture(str(result.video_path))
    try:
        assert capture.isOpened()
        assert int(capture.get(cv2.CAP_PROP_FRAME_WIDTH)) == WIDTH
    finally:
        capture.release()