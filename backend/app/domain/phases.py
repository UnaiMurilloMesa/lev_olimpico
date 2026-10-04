"""Fases del levantamiento olímpico y sus límites temporales."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from app.domain.lift_window import LiftWindow


class LiftPhase(StrEnum):
    """Fases en que se divide un snatch."""

    FIRST_PULL = "first_pull"
    TRANSITION = "transition"
    SECOND_PULL = "second_pull"
    TURNOVER = "turnover"
    RECOVERY = "recovery"

    @property
    def label(self) -> str:
        """Nombre legible de la fase."""
        return _PHASE_LABELS[self]


_PHASE_LABELS: dict[LiftPhase, str] = {
    LiftPhase.FIRST_PULL: "Primera tirada",
    LiftPhase.TRANSITION: "Transición",
    LiftPhase.SECOND_PULL: "Segunda tirada",
    LiftPhase.TURNOVER: "Recepción",
    LiftPhase.RECOVERY: "Recuperación",
}


@dataclass(frozen=True, slots=True)
class PhaseSpan:
    """Tramo de fotogramas que ocupa una fase.

    Los índices son absolutos y ambos extremos están incluidos.
    """

    phase: LiftPhase
    start_index: int
    end_index: int

    def __len__(self) -> int:
        """Número de fotogramas de la fase."""
        return self.end_index - self.start_index + 1

    def contains(self, frame_index: int) -> bool:
        """Indica si un fotograma pertenece a la fase."""
        return self.start_index <= frame_index <= self.end_index

    def duration_seconds(self, fps: float) -> float:
        """Duración de la fase en segundos."""
        return len(self) / fps if fps else 0.0


@dataclass(frozen=True, slots=True)
class PhaseBreakdown:
    """División completa del levantamiento en fases."""

    spans: tuple[PhaseSpan, ...]

    def __len__(self) -> int:
        """Número de fases identificadas."""
        return len(self.spans)

    def span_for(self, phase: LiftPhase) -> PhaseSpan | None:
        """Devuelve el tramo de una fase concreta."""
        return next((span for span in self.spans if span.phase is phase), None)

    def phase_at(self, frame_index: int) -> LiftPhase | None:
        """Indica a qué fase pertenece un fotograma."""
        return next(
            (span.phase for span in self.spans if span.contains(frame_index)), None
        )


def build_breakdown(window: LiftWindow, boundaries: tuple[int, int, int, int]) -> PhaseBreakdown:
    """Construye las cinco fases a partir de los cuatro límites internos.

    Los límites son el último fotograma de las cuatro primeras fases. Se
    ordenan y se acotan a la ventana, de modo que una detección imprecisa
    produzca fases cortas pero nunca solapadas ni invertidas.
    """
    ordered = _clamped_boundaries(window, boundaries)
    phases = (
        LiftPhase.FIRST_PULL,
        LiftPhase.TRANSITION,
        LiftPhase.SECOND_PULL,
        LiftPhase.TURNOVER,
        LiftPhase.RECOVERY,
    )

    starts = (window.start_index, *(min(limit + 1, window.end_index) for limit in ordered))
    ends = (*ordered, window.end_index)

    return PhaseBreakdown(
        spans=tuple(
            PhaseSpan(phase=phase, start_index=start, end_index=max(end, start))
            for phase, start, end in zip(phases, starts, ends, strict=True)
        )
    )


def _clamped_boundaries(
    window: LiftWindow, boundaries: tuple[int, int, int, int]
) -> tuple[int, ...]:
    """Ordena y acota los límites dentro de la ventana del levantamiento."""
    limits: list[int] = []
    previous = window.start_index

    for boundary in boundaries:
        value = min(max(boundary, previous), window.end_index)
        limits.append(value)
        previous = value

    return tuple(limits)