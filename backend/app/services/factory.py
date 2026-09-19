"""Construcción de los servicios de la aplicación."""

from app.core.config import Settings
from app.services.analysis_service import AnalysisService
from app.services.pose.estimator import MediaPipePoseEstimator
from app.services.pose.renderer import SkeletonRenderer
from app.services.video.transcoder import FfmpegTranscoder


def build_analysis_service(settings: Settings) -> AnalysisService:
    """Crea un servicio de análisis con las implementaciones reales."""
    return AnalysisService(
        estimator=MediaPipePoseEstimator(model_path=settings.pose_model_path),
        renderer=SkeletonRenderer(),
        transcoder=FfmpegTranscoder(),
    )