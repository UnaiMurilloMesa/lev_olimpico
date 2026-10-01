"""Caso de uso principal: analizar un vídeo de levantamiento."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from app.domain.bar_path import extract_bar_path
from app.domain.lift_detection import detect_lift_window
from app.domain.lift_window import LiftWindow, slice_sequence
from app.domain.scale import estimate_scale
from app.domain.sequence import KEY_LANDMARKS, PoseSequence
from app.services.analysis.velocity import BarVelocity, compute_bar_velocity
from app.services.analysis.velocity_chart import VelocityChartRenderer
from app.services.pose.smoother import PoseSmoother
from app.services.video.extractor import PoseExtractor
from app.services.video.metadata import VideoMetadata
from app.services.video.renderer import PoseVideoRenderer
from app.services.video.transcoder import VideoTranscoder

logger = logging.getLogger(__name__)

RAW_OUTPUT_SUFFIX = "_raw.mp4"
FINAL_OUTPUT_NAME = "analysis.mp4"
VELOCITY_CHART_NAME = "velocity.png"
DEFAULT_ATHLETE_HEIGHT_M = 1.75


@dataclass(frozen=True, slots=True)
class AnalysisResult:
    """Resultado del análisis de un vídeo."""

    video_path: Path
    processed_frames: int
    detected_frames: int
    detection_ratio: float
    duration_seconds: float
    bar_path_deviation: float
    bar_path_quality: str
    lift_start_seconds: float
    lift_end_seconds: float
    lift_duration_seconds: float
    peak_velocity_ms: float
    peak_velocity_time: float
    velocity_chart: Path | None
    athlete_height_m: float
    interpolated_frames: int


class AnalysisService:
    """Coordina el análisis completo de un vídeo de levantamiento.

    El proceso consta de tres fases: extracción de las poses, suavizado
    temporal de las trayectorias y renderizado del vídeo con la pose ya
    suavizada. El suavizado necesita la secuencia completa, incluidos los
    fotogramas posteriores a cada instante, de ahí que no pueda hacerse en
    una única pasada sobre el vídeo.
    """

    def __init__(
        self,
        extractor: PoseExtractor,
        smoother: PoseSmoother,
        video_renderer: PoseVideoRenderer,
        transcoder: VideoTranscoder,
        chart_renderer: VelocityChartRenderer,
    ) -> None:
        """Crea el servicio con sus colaboradores."""
        self._extractor = extractor
        self._smoother = smoother
        self._video_renderer = video_renderer
        self._transcoder = transcoder
        self._chart_renderer = chart_renderer

    def analyze(
        self,
        source: Path,
        workspace: Path,
        start_seconds: float = 0.0,
        athlete_height_m: float = DEFAULT_ATHLETE_HEIGHT_M,
    ) -> AnalysisResult:
        """Analiza un vídeo y deja el resultado listo para su descarga.

        Args:
            source: Vídeo original subido por el usuario.
            workspace: Directorio de trabajo exclusivo de este análisis.
            start_seconds: Instante en que la barra despega del suelo.
            athlete_height_m: Estatura del levantador, usada para escalar a metros.

        Returns:
            El resumen del análisis, con las rutas de los artefactos generados.
        """
        workspace.mkdir(parents=True, exist_ok=True)
        raw_output = workspace / f"{source.stem}{RAW_OUTPUT_SUFFIX}"
        final_output = workspace / FINAL_OUTPUT_NAME

        logger.info("Iniciando análisis de %s desde %.2fs", source.name, start_seconds)
        sequence, metadata = self._extractor.extract(source)
        smoothed = self._smoother.smooth(sequence)

        window = detect_lift_window(smoothed, start_seconds)
        lift = slice_sequence(smoothed, window)
        raw_lift = slice_sequence(sequence, window)
        logger.info(
            "Levantamiento acotado entre los fotogramas %d y %d (%.2fs), "
            "pose detectada en %.1f%% de los fotogramas",
            window.start_index,
            window.end_index,
            window.duration_seconds(smoothed.fps),
            raw_lift.detection_ratio * 100,
        )



        bar_path_debug = extract_bar_path(lift)
        if bar_path_debug.points:
            logger.info(
                "Bar path: %d puntos, del fotograma %d al %d (ventana %d-%d)",
                len(bar_path_debug),
                bar_path_debug.points[0].frame_index,
                bar_path_debug.points[-1].frame_index,
                window.start_index,
                window.end_index,
            )




        velocity, chart = self._compute_velocity(smoothed, lift, workspace, athlete_height_m)

        self._video_renderer.render(source, raw_output, smoothed, metadata, lift)
        self._transcoder.to_android_compatible(raw_output, final_output)
        raw_output.unlink(missing_ok=True)

        return self._build_result(
            final_output, metadata, smoothed, lift, raw_lift, window, velocity, chart,
            athlete_height_m,
        )

    def _compute_velocity(
        self,
        full: PoseSequence,
        lift: PoseSequence,
        workspace: Path,
        athlete_height_m: float,
    ) -> tuple[BarVelocity, Path | None]:
        """Calcula la velocidad de la barra y genera su gráfica.

        La escala se estima sobre la secuencia completa, donde es más probable
        encontrar al atleta erguido, pero la velocidad solo se calcula en el
        tramo del levantamiento.
        """
        scale = estimate_scale(full, athlete_height_m)
        if scale is None:
            logger.warning("Sin escala corporal: no se puede calcular la velocidad.")
            return BarVelocity(samples=()), None

        velocity = compute_bar_velocity(lift, scale)
        chart = self._chart_renderer.render(velocity, workspace / VELOCITY_CHART_NAME)
        return velocity, chart

    def _build_result(
        self,
        video_path: Path,
        metadata: VideoMetadata,
        full: PoseSequence,
        lift: PoseSequence,
        raw_lift: PoseSequence,
        window: LiftWindow,
        velocity: BarVelocity,
        chart: Path | None,
        athlete_height_m: float,
    ) -> AnalysisResult:
        """Compone el resumen del análisis a partir del tramo acotado."""
        bar_path = extract_bar_path(lift)
        return AnalysisResult(
            video_path=video_path,
            processed_frames=len(full),
            detected_frames=raw_lift.detected_count,
            detection_ratio=raw_lift.tracking_quality(KEY_LANDMARKS),
            interpolated_frames=lift.detected_count - raw_lift.detected_count,
            duration_seconds=metadata.duration_seconds,
            bar_path_deviation=round(bar_path.deviation_ratio, 4),
            bar_path_quality=bar_path.quality.value,
            lift_start_seconds=round(window.start_index / full.fps, 2),
            lift_end_seconds=round(window.end_index / full.fps, 2),
            lift_duration_seconds=round(window.duration_seconds(full.fps), 2),
            peak_velocity_ms=round(velocity.peak_velocity_ms, 2),
            peak_velocity_time=round(velocity.peak_time_seconds, 2),
            velocity_chart=chart,
            athlete_height_m=athlete_height_m,
        )