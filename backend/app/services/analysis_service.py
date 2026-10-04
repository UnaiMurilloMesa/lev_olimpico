"""Caso de uso principal: analizar un vídeo de levantamiento."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from app.domain.bar_path import extract_bar_path
from app.domain.lift_detection import detect_lift_window
from app.domain.lift_window import LiftWindow, slice_sequence
from app.domain.phase_detection import detect_phases
from app.domain.phases import PhaseBreakdown
from app.domain.scale import estimate_scale
from app.domain.sequence import KEY_LANDMARKS, PoseSequence
from app.services.analysis.phase_scoring import LiftScore, score_lift
from app.services.analysis.velocity import BarVelocity, compute_bar_velocity
from app.services.analysis.velocity_chart import VelocityChartRenderer
from app.services.pose.smoother import PoseSmoother
from app.services.video.extractor import PoseExtractor
from app.services.video.metadata import VideoMetadata
from app.services.video.renderer import PoseVideoRenderer
from app.services.video.snapshots import PhaseSnapshot, PhaseSnapshotExtractor
from app.services.video.transcoder import VideoTranscoder

logger = logging.getLogger(__name__)

RAW_OUTPUT_SUFFIX = "_raw.mp4"
FINAL_OUTPUT_NAME = "analysis.mp4"
VELOCITY_CHART_NAME = "velocity.png"
SNAPSHOTS_DIR = "phases"
DEFAULT_ATHLETE_HEIGHT_M = 1.75


@dataclass(frozen=True, slots=True)
class CriterionResult:
    """Criterio evaluado dentro de una fase."""

    criterion: str
    score: float
    level: str
    measured_value: float
    explanation: str


@dataclass(frozen=True, slots=True)
class PhaseResult:
    """Resumen de una fase del levantamiento."""

    phase: str
    label: str
    start_seconds: float
    end_seconds: float
    duration_seconds: float
    snapshot: str | None
    score: float
    level: str
    criteria: tuple[CriterionResult, ...]


@dataclass(frozen=True, slots=True)
class AnalysisResult:
    """Resultado del análisis de un vídeo."""

    video_path: Path
    processed_frames: int
    detected_frames: int
    detection_ratio: float
    interpolated_frames: int
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
    phases: tuple[PhaseResult, ...]
    overall_score: float


class AnalysisService:
    """Coordina el análisis completo de un vídeo de levantamiento.

    El proceso consta de tres etapas: extracción de las poses, suavizado
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
        snapshot_extractor: PhaseSnapshotExtractor,
    ) -> None:
        """Crea el servicio con sus colaboradores."""
        self._extractor = extractor
        self._smoother = smoother
        self._video_renderer = video_renderer
        self._transcoder = transcoder
        self._chart_renderer = chart_renderer
        self._snapshot_extractor = snapshot_extractor

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
            "rastreo fiable en el %.1f%% de los puntos clave",
            window.start_index,
            window.end_index,
            window.duration_seconds(smoothed.fps),
            raw_lift.tracking_quality(KEY_LANDMARKS) * 100,
        )

        breakdown = detect_phases(lift, window)
        snapshots = self._snapshot_extractor.extract(
            source, workspace / SNAPSHOTS_DIR, lift, breakdown
        )

        velocity, chart = self._compute_velocity(smoothed, lift, workspace, athlete_height_m)
        scoring = score_lift(lift, breakdown, velocity)

        self._video_renderer.render(source, raw_output, smoothed, metadata, lift)
        self._transcoder.to_android_compatible(raw_output, final_output)
        raw_output.unlink(missing_ok=True)

        return self._build_result(
            video_path=final_output,
            metadata=metadata,
            full=smoothed,
            lift=lift,
            raw_lift=raw_lift,
            window=window,
            velocity=velocity,
            chart=chart,
            athlete_height_m=athlete_height_m,
            breakdown=breakdown,
            snapshots=snapshots,
            scoring=scoring,
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
        breakdown: PhaseBreakdown,
        snapshots: tuple[PhaseSnapshot, ...],
        scoring: LiftScore,
    ) -> AnalysisResult:
        """Compone el resumen del análisis a partir del tramo acotado.

        Las métricas de rastreo se miden sobre la secuencia **sin suavizar**:
        la interpolación rellena huecos y, medida después, la calidad sería
        siempre perfecta aunque el rastreo hubiese fallado.
        """
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
            phases=self._build_phases(
                breakdown, snapshots, scoring, full.fps, window.start_index
            ),
            overall_score=scoring.overall,
        )


    @staticmethod
    def _build_phases(
        breakdown: PhaseBreakdown,
        snapshots: tuple[PhaseSnapshot, ...],
        scoring: LiftScore,
        fps: float,
        window_start: int,
    ) -> tuple[PhaseResult, ...]:
        """Compone el resumen de cada fase con su captura y su puntuación.

        Los instantes se expresan desde el despegue de la barra, no desde el
        inicio del vídeo, que es como el usuario percibe el movimiento.
        """
        by_phase = {shot.phase: shot for shot in snapshots}
        scores = {phase.phase: phase for phase in scoring.phases}

        results: list[PhaseResult] = []
        for span in breakdown.spans:
            score = scores.get(span.phase.value)
            results.append(
                PhaseResult(
                    phase=span.phase.value,
                    label=span.phase.label,
                    start_seconds=round((span.start_index - window_start) / fps, 2),
                    end_seconds=round((span.end_index - window_start) / fps, 2),
                    duration_seconds=round(span.duration_seconds(fps), 2),
                    snapshot=(
                        by_phase[span.phase].path.name if span.phase in by_phase else None
                    ),
                    score=score.score if score else 0.0,
                    level=score.level.value if score and score.criteria else "unknown",
                    criteria=tuple(
                        CriterionResult(
                            criterion=item.criterion,
                            score=item.score,
                            level=item.level.value,
                            measured_value=item.measured_value,
                            explanation=item.explanation,
                        )
                        for item in (score.criteria if score else ())
                    ),
                )
            )

        return tuple(results)