"""Conversión de medidas biomecánicas en puntuaciones comprensibles."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

MIN_SCORE = 0.0
MAX_SCORE = 10.0
GOOD_SCORE_THRESHOLD = 7.0
FAIR_SCORE_THRESHOLD = 5.0


class ScoreLevel(StrEnum):
    """Valoración cualitativa de una puntuación."""

    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"

    @classmethod
    def from_score(cls, score: float) -> ScoreLevel:
        """Clasifica una puntuación en un nivel."""
        if score >= GOOD_SCORE_THRESHOLD:
            return cls.GOOD
        if score >= FAIR_SCORE_THRESHOLD:
            return cls.FAIR
        return cls.POOR


@dataclass(frozen=True, slots=True)
class ScoreScale:
    """Transforma una medida física en una puntuación de 0 a 10.

    La escala se define por los dos valores de la medida que corresponden a la
    nota máxima y a la nota mínima. Entre ambos la puntuación varía de forma
    lineal, lo que mantiene la nota explicable: siempre se puede decir qué
    valor habría hecho falta para subir un punto.

    Si `best` es mayor que `worst`, la escala es creciente (más medida, mejor
    nota); en caso contrario es decreciente.
    """

    best: float
    worst: float

    def __post_init__(self) -> None:
        """Valida que la escala tenga recorrido.

        Raises:
            ValueError: Si ambos extremos coinciden.
        """
        if self.best == self.worst:
            raise ValueError("Una escala de puntuación necesita dos extremos distintos.")

    def score(self, value: float) -> float:
        """Puntúa una medida, acotando el resultado al rango válido."""
        ratio = (value - self.worst) / (self.best - self.worst)
        return round(min(max(ratio, 0.0), 1.0) * MAX_SCORE, 1)


@dataclass(frozen=True, slots=True)
class CriterionScore:
    """Puntuación de un criterio concreto, con su justificación."""

    criterion: str
    score: float
    measured_value: float
    explanation: str

    @property
    def level(self) -> ScoreLevel:
        """Valoración cualitativa de la puntuación."""
        return ScoreLevel.from_score(self.score)


@dataclass(frozen=True, slots=True)
class PhaseScore:
    """Puntuación de una fase, compuesta por uno o varios criterios."""

    phase: str
    criteria: tuple[CriterionScore, ...]

    @property
    def score(self) -> float:
        """Media de los criterios de la fase."""
        if not self.criteria:
            return 0.0
        return round(sum(item.score for item in self.criteria) / len(self.criteria), 1)

    @property
    def level(self) -> ScoreLevel:
        """Valoración cualitativa de la fase."""
        return ScoreLevel.from_score(self.score)


def overall_score(phases: tuple[PhaseScore, ...]) -> float:
    """Puntuación global del levantamiento, como media de sus fases.

    Las fases pesan por igual: ponderarlas exigiría una validación con
    entrenadores que este trabajo no aborda.
    """
    scored = [phase for phase in phases if phase.criteria]
    if not scored:
        return 0.0
    return round(sum(phase.score for phase in scored) / len(scored), 1)