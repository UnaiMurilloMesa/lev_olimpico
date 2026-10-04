"""Pruebas del modelo de puntuación."""

import pytest

from app.domain.scoring import (
    CriterionScore,
    PhaseScore,
    ScoreLevel,
    ScoreScale,
    overall_score,
)


def _criterion(score: float, criterion: str = "prueba") -> CriterionScore:
    return CriterionScore(
        criterion=criterion, score=score, measured_value=0.0, explanation=""
    )


# --- Escala ---


def test_una_escala_decreciente_puntua_mejor_los_valores_bajos() -> None:
    escala = ScoreScale(best=0.0, worst=0.4)

    assert escala.score(0.0) == 10.0
    assert escala.score(0.2) == 5.0
    assert escala.score(0.4) == 0.0


def test_una_escala_creciente_puntua_mejor_los_valores_altos() -> None:
    escala = ScoreScale(best=2.0, worst=1.0)

    assert escala.score(2.0) == 10.0
    assert escala.score(1.5) == 5.0
    assert escala.score(1.0) == 0.0


def test_los_valores_fuera_de_rango_se_acotan() -> None:
    escala = ScoreScale(best=0.0, worst=0.4)

    assert escala.score(-1.0) == 10.0
    assert escala.score(99.0) == 0.0


def test_una_escala_sin_recorrido_no_es_valida() -> None:
    with pytest.raises(ValueError, match="extremos"):
        ScoreScale(best=1.0, worst=1.0)


# --- Niveles ---


@pytest.mark.parametrize(
    ("score", "esperado"),
    [
        (10.0, ScoreLevel.GOOD),
        (7.0, ScoreLevel.GOOD),
        (6.9, ScoreLevel.FAIR),
        (5.0, ScoreLevel.FAIR),
        (4.9, ScoreLevel.POOR),
        (0.0, ScoreLevel.POOR),
    ],
)
def test_clasifica_las_puntuaciones_en_niveles(score: float, esperado: ScoreLevel) -> None:
    assert ScoreLevel.from_score(score) is esperado


# --- Agregación ---


def test_la_puntuacion_de_una_fase_promedia_sus_criterios() -> None:
    fase = PhaseScore(phase="first_pull", criteria=(_criterion(8.0), _criterion(6.0)))

    assert fase.score == 7.0
    assert fase.level is ScoreLevel.GOOD


def test_una_fase_sin_criterios_no_puntua() -> None:
    fase = PhaseScore(phase="turnover", criteria=())

    assert fase.score == 0.0


def test_la_puntuacion_global_promedia_las_fases() -> None:
    fases = (
        PhaseScore("a", (_criterion(10.0),)),
        PhaseScore("b", (_criterion(5.0),)),
    )

    assert overall_score(fases) == 7.5


def test_las_fases_sin_criterios_no_arrastran_la_media() -> None:
    """Una fase que no se pudo medir no debe penalizar al resto."""
    fases = (
        PhaseScore("a", (_criterion(8.0),)),
        PhaseScore("b", ()),
    )

    assert overall_score(fases) == 8.0


def test_sin_ninguna_fase_puntuada_la_nota_global_es_cero() -> None:
    assert overall_score((PhaseScore("a", ()),)) == 0.0


def test_cada_criterio_conserva_su_justificacion() -> None:
    criterio = CriterionScore(
        criterion="verticalidad",
        score=6.0,
        measured_value=0.18,
        explanation="La barra se desvió un 18% del recorrido vertical.",
    )

    assert criterio.level is ScoreLevel.FAIR
    assert "18%" in criterio.explanation