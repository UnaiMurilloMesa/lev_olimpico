"""Construcción de los servicios de la aplicación."""

from app.core.config import Settings
from app.domain.bar_path import extract_bar_path
from app.domain.sequence import PoseSequence
from app.services.analysis.velocity_chart import MatplotlibVelocityChart
from app.services.analysis_service import AnalysisService
from app.services.pose.angle_renderer import AngleRenderer
from app.services.pose.bar_path_minimap import BarPathMinimapRenderer
from app.services.pose.bar_path_renderer import BarPathRenderer
from app.services.pose.composite import CompositeFrameRenderer
from app.services.pose.estimator import MediaPipePoseEstimator
from app.services.pose.renderer import FrameRenderer, SkeletonRenderer
from app.services.pose.smoother import SavitzkyGolaySmoother
from app.services.video.extractor import PoseExtractor
from app.services.video.renderer import PoseVideoRenderer
from app.services.video.transcoder import FfmpegTranscoder


def build_frame_renderer(sequence: PoseSequence) -> FrameRenderer:
    """Compone las capas de dibujo para una secuencia concreta."""
    bar_path = extract_bar_path(sequence)
    return CompositeFrameRenderer(
        BarPathRenderer(bar_path),
        SkeletonRenderer(),
        AngleRenderer(),
        BarPathMinimapRenderer(bar_path),
    )


def build_analysis_service(settings: Settings) -> AnalysisService:
    """Crea un servicio de análisis con las implementaciones reales."""
    estimator = MediaPipePoseEstimator(model_path=settings.pose_model_path)
    return AnalysisService(
        extractor=PoseExtractor(estimator),
        smoother=SavitzkyGolaySmoother(),
        video_renderer=PoseVideoRenderer(build_frame_renderer),
        transcoder=FfmpegTranscoder(),
        chart_renderer=MatplotlibVelocityChart(),
    )