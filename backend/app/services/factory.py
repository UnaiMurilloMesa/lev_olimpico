"""Construcción de los servicios de la aplicación."""

from app.core.config import Settings
from app.services.analysis_service import AnalysisService
from app.services.pose.estimator import MediaPipePoseEstimator
from app.services.pose.renderer import SkeletonRenderer
from app.services.pose.smoother import SavitzkyGolaySmoother
from app.services.video.extractor import PoseExtractor
from app.services.video.renderer import PoseVideoRenderer
from app.services.video.transcoder import FfmpegTranscoder


def build_analysis_service(settings: Settings) -> AnalysisService:
    """Crea un servicio de análisis con las implementaciones reales."""
    estimator = MediaPipePoseEstimator(model_path=settings.pose_model_path)
    return AnalysisService(
        extractor=PoseExtractor(estimator),
        smoother=SavitzkyGolaySmoother(),
        video_renderer=PoseVideoRenderer(SkeletonRenderer()),
        transcoder=FfmpegTranscoder(),
    )