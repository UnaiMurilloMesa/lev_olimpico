"""Pruebas del modelo de fases del levantamiento."""

import pytest

from app.domain.lift_window import LiftWindow
from app.domain.phases import LiftPhase, PhaseSpan, build_breakdown

WINDOW = LiftWindow(start_index=10, end_index=110)


def test_un_tramo_incluye_ambos_extremos() -> None:
    span = PhaseSpan(LiftPhase.FIRST_PULL, start_index=10, end_index=20)

    assert len(span) == 11
    assert span.contains(10) is True
    assert span.contains(20) is True
    assert span.contains(21) is False


def test_calcula_la_duracion_de_un_tramo() -> None:
    span = PhaseSpan(LiftPhase.SECOND_PULL, start_index=0, end_index=29)

    assert span.duration_seconds(30.0) == pytest.approx(1.0)


def test_divide_el_levantamiento_en_cinco_fases() -> None:
    breakdown = build_breakdown(WINDOW, (30, 50, 70, 90))

    assert len(breakdown) == 5
    assert [span.phase for span in breakdown.spans] == list(LiftPhase)


def test_las_fases_cubren_la_ventana_sin_huecos() -> None:
    breakdown = build_breakdown(WINDOW, (30, 50, 70, 90))

    assert breakdown.spans[0].start_index == WINDOW.start_index
    assert breakdown.spans[-1].end_index == WINDOW.end_index
    for anterior, siguiente in zip(breakdown.spans, breakdown.spans[1:], strict=False):
        assert siguiente.start_index == anterior.end_index + 1


def test_localiza_la_fase_de_un_fotograma() -> None:
    breakdown = build_breakdown(WINDOW, (30, 50, 70, 90))

    assert breakdown.phase_at(20) is LiftPhase.FIRST_PULL
    assert breakdown.phase_at(60) is LiftPhase.SECOND_PULL
    assert breakdown.phase_at(100) is LiftPhase.RECOVERY


def test_un_fotograma_fuera_de_la_ventana_no_tiene_fase() -> None:
    breakdown = build_breakdown(WINDOW, (30, 50, 70, 90))

    assert breakdown.phase_at(5) is None
    assert breakdown.phase_at(200) is None


def test_devuelve_el_tramo_de_una_fase_concreta() -> None:
    breakdown = build_breakdown(WINDOW, (30, 50, 70, 90))

    span = breakdown.span_for(LiftPhase.TURNOVER)

    assert span is not None
    assert (span.start_index, span.end_index) == (71, 90)


def test_los_limites_desordenados_no_invierten_las_fases() -> None:
    """Una detección imprecisa no debe producir tramos inválidos."""
    breakdown = build_breakdown(WINDOW, (70, 30, 90, 50))

    for span in breakdown.spans:
        assert span.end_index >= span.start_index


def test_los_limites_fuera_de_la_ventana_se_acotan() -> None:
    breakdown = build_breakdown(WINDOW, (5, 50, 70, 500))

    assert breakdown.spans[0].start_index >= WINDOW.start_index
    assert breakdown.spans[-1].end_index == WINDOW.end_index


def test_cada_fase_tiene_un_nombre_legible() -> None:
    assert LiftPhase.FIRST_PULL.label == "Primera tirada"
    assert all(phase.label for phase in LiftPhase)


def test_ninguna_fase_sale_de_la_ventana() -> None:
    breakdown = build_breakdown(WINDOW, (5, 50, 70, 500))

    for span in breakdown.spans:
        assert span.start_index >= WINDOW.start_index
        assert span.end_index <= WINDOW.end_index