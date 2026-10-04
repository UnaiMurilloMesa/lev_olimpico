"""Puntuación de cada fase del levantamiento."""

from __future__ import annotations

from dataclasses import dataclass

from app.domain.angles import JointName, joint_angles
from app.domain.bar_path import extract_bar_path
from app.domain.phases import LiftPhase, PhaseBreakdown, PhaseSpan
from app.domain.scoring import CriterionScore, PhaseScore, ScoreScale, overall_score
from app.domain.sequence import PoseSequence
from app.services.analysis.velocity import BarVelocity


@dataclass(frozen=True, slots=True)
class ScoringConfig:
    """Escalas que traducen cada medida en una puntuación.

    Los extremos se han fijado a partir de criterios biomecánicos y de un
    conjunto preliminar de levantamientos; son parámetros a validar con más
    datos y con el juicio de entrenadores.
    """

    verticality: ScoreScale = ScoreScale(best=0.05, worst=0.35)
    smoothness: ScoreScale = ScoreScale(best=0.0, worst=0.15)
    peak_velocity: ScoreScale = ScoreScale(best=1.9, worst=1.0)
    hip_extension: ScoreScale = ScoreScale(best=168.0, worst=140.0)
    turnover_speed: ScoreScale = ScoreScale(best=0.35, worst=1.0)
    recovery_stability: ScoreScale = ScoreScale(best=0.04, worst=0.25)


@dataclass(frozen=True, slots=True)
class LiftScore:
    """Puntuación completa de un levantamiento."""

    phases: tuple[PhaseScore, ...]
    overall: float


def score_lift(
    lift: PoseSequence,
    breakdown: PhaseBreakdown,
    velocity: BarVelocity,
    config: ScoringConfig | None = None,
) -> LiftScore:
    """Puntúa cada fase del levantamiento con criterios verificables.

    Cada criterio se elige para que el atleta pueda comprobarlo en su propio
    vídeo: la verticalidad se ve en el bar path, la velocidad en la gráfica y
    la extensión o la profundidad en las capturas de fase.
    """
    config = config or ScoringConfig()
    scorers = {
        LiftPhase.FIRST_PULL: _score_first_pull,
        LiftPhase.TRANSITION: _score_transition,
        LiftPhase.SECOND_PULL: _score_second_pull,
        LiftPhase.TURNOVER: _score_turnover,
        LiftPhase.RECOVERY: _score_recovery,
    }

    phases = tuple(
        PhaseScore(
            phase=span.phase.value,
            criteria=scorers[span.phase](lift, span, velocity, config),
        )
        for span in breakdown.spans
    )
    return LiftScore(phases=phases, overall=overall_score(phases))


def _score_first_pull(
    lift: PoseSequence, span: PhaseSpan, velocity: BarVelocity, config: ScoringConfig
) -> tuple[CriterionScore, ...]:
    """Puntúa la verticalidad de la barra durante la primera tirada."""
    deviation = _phase_deviation(lift, span)
    if deviation is None:
        return ()

    return (
        CriterionScore(
            criterion="verticalidad",
            score=config.verticality.score(deviation),
            measured_value=round(deviation, 3),
            explanation=(
                f"La barra se desvió un {deviation * 100:.0f}% de su recorrido vertical "
                "mientras despegaba del suelo."
            ),
        ),
    )


def _score_transition(
    lift: PoseSequence, span: PhaseSpan, velocity: BarVelocity, config: ScoringConfig
) -> tuple[CriterionScore, ...]:
    """Puntúa la continuidad del tirón durante la transición.

    Solo penaliza las caídas de velocidad: en esta fase la barra debe seguir
    acelerando hacia la segunda tirada, de modo que un aumento no es un
    defecto. Lo que delata una transición deficiente es el frenazo, cuando el
    atleta detiene la barra para reposicionarse.
    """
    samples = [s.velocity_ms for s in velocity.samples if span.contains(s.frame_index)]
    if len(samples) < 2:
        return ()

    drop = max(
        (previous - current for previous, current in zip(samples, samples[1:], strict=False)),
        default=0.0,
    )
    drop = max(drop, 0.0)

    return (
        CriterionScore(
            criterion="continuidad",
            score=config.smoothness.score(drop),
            measured_value=round(drop, 2),
            explanation=(
                f"La barra perdió {drop:.2f} m/s de velocidad durante la transición."
                if drop > 0
                else "La barra mantuvo la aceleración durante la transición."
            ),
        ),
    )


def _score_second_pull(
    lift: PoseSequence, span: PhaseSpan, velocity: BarVelocity, config: ScoringConfig
) -> tuple[CriterionScore, ...]:
    """Puntúa la potencia del tirón: velocidad alcanzada y extensión lograda."""
    criteria: list[CriterionScore] = []

    samples = [s.velocity_ms for s in velocity.samples if span.contains(s.frame_index)]
    if samples:
        peak = max(samples)
        criteria.append(
            CriterionScore(
                criterion="velocidad",
                score=config.peak_velocity.score(peak),
                measured_value=round(peak, 2),
                explanation=f"La barra alcanzó {peak:.2f} m/s en la segunda tirada.",
            )
        )

    extension = _max_hip_extension(lift, span)
    if extension is not None:
        criteria.append(
            CriterionScore(
                criterion="extension",
                score=config.hip_extension.score(extension),
                measured_value=round(extension, 1),
                explanation=f"La cadera alcanzó una apertura de {extension:.0f}º.",
            )
        )

    return tuple(criteria)


def _score_turnover(
    lift: PoseSequence, span: PhaseSpan, velocity: BarVelocity, config: ScoringConfig
) -> tuple[CriterionScore, ...]:
    """Puntúa la rapidez de la recepción bajo la barra.

    La duración solo es significativa si la fase contiene pose detectada: sin
    datos corporales, un tramo corto no indica una recepción rápida sino la
    ausencia de medición.
    """
    detected = sum(
        1 for frame in lift.frames if span.contains(frame.index) and frame.is_detected
    )
    duration = span.duration_seconds(lift.fps)
    if detected < 2 or duration <= 0:
        return ()

    return (
        CriterionScore(
            criterion="rapidez",
            score=config.turnover_speed.score(duration),
            measured_value=round(duration, 2),
            explanation=f"Tardaste {duration:.2f} s en colocarte bajo la barra.",
        ),
    )


def _score_recovery(
    lift: PoseSequence, span: PhaseSpan, velocity: BarVelocity, config: ScoringConfig
) -> tuple[CriterionScore, ...]:
    """Puntúa la estabilidad de la barra mientras el atleta se incorpora.

    La desviación se normaliza por el recorrido vertical del levantamiento
    completo: durante la recuperación la barra sube muy poco, y normalizar por
    el recorrido de la fase convertiría cualquier oscilación mínima en un
    porcentaje desproporcionado.
    """
    frames = tuple(frame for frame in lift.frames if span.contains(frame.index))
    if len(frames) < 2:
        return ()

    phase_path = extract_bar_path(PoseSequence(frames=frames, fps=lift.fps))
    full_path = extract_bar_path(lift)
    if not phase_path.points or full_path.vertical_range <= 0:
        return ()

    deviation = phase_path.horizontal_deviation / full_path.vertical_range
    return (
        CriterionScore(
            criterion="estabilidad",
            score=config.recovery_stability.score(deviation),
            measured_value=round(deviation, 3),
            explanation=(
                f"La barra osciló un {deviation * 100:.0f}% del recorrido del "
                "levantamiento mientras te incorporabas."
            ),
        ),
    )


def _phase_deviation(lift: PoseSequence, span: PhaseSpan) -> float | None:
    """Desviación horizontal relativa de la barra dentro de una fase."""
    frames = tuple(frame for frame in lift.frames if span.contains(frame.index))
    if len(frames) < 2:
        return None

    path = extract_bar_path(PoseSequence(frames=frames, fps=lift.fps))
    return path.deviation_ratio if path.points else None


def _max_hip_extension(lift: PoseSequence, span: PhaseSpan) -> float | None:
    """Mayor apertura de cadera alcanzada dentro de una fase."""
    best: float | None = None

    for frame in lift.frames:
        if not span.contains(frame.index) or not frame.is_detected:
            continue
        angles = joint_angles(frame)
        average = (angles[JointName.LEFT_HIP] + angles[JointName.RIGHT_HIP]) / 2
        if best is None or average > best:
            best = average

    return best