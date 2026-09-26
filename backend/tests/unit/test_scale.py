"""Pruebas de la estimación de escala corporal."""

import pytest

from app.domain.landmarks import Landmark, PoseFrame, PoseLandmarkId
from app.domain.scale import (
    BodyScale,
    InvalidHeightError,
    estimate_scale,
    validate_height,
    visible_body_span,
)
from app.domain.sequence import PoseSequence


def _frame(index: int, eye_y: float, foot_y: float) -> PoseFrame:
    landmarks = [Landmark(0.5, 0.5, 0.0, 1.0) for _ in range(33)]
    for point in (PoseLandmarkId.LEFT_EYE, PoseLandmarkId.RIGHT_EYE):
        landmarks[point] = Landmark(0.5, eye_y, 0.0, 1.0)
    for point in (
        PoseLandmarkId.LEFT_HEEL,
        PoseLandmarkId.RIGHT_HEEL,
        PoseLandmarkId.LEFT_FOOT_INDEX,
        PoseLandmarkId.RIGHT_FOOT_INDEX,
    ):
        landmarks[point] = Landmark(0.5, foot_y, 0.0, 1.0)
    return PoseFrame(index=index, timestamp_ms=index * 33, landmarks=tuple(landmarks))


def test_convierte_distancias_a_metros() -> None:
    escala = BodyScale(meters_per_unit=2.0)

    assert escala.to_meters(0.5) == pytest.approx(1.0)


def test_mide_la_extension_vertical_del_cuerpo() -> None:
    span = visible_body_span(_frame(0, eye_y=0.1, foot_y=0.9))

    assert span is not None
    # 0.8 entre ojos y pies, extrapolado hasta la coronilla.
    assert span == pytest.approx(0.8 / 0.94)


def test_un_fotograma_sin_pose_no_aporta_medida() -> None:
    assert visible_body_span(PoseFrame(index=0, timestamp_ms=0, landmarks=())) is None


def test_una_extension_invertida_no_es_valida() -> None:
    assert visible_body_span(_frame(0, eye_y=0.9, foot_y=0.1)) is None


def test_usa_el_fotograma_mas_extendido() -> None:
    """En flexión el cuerpo se proyecta más corto y no debe fijar la escala."""
    secuencia = PoseSequence(
        frames=(
            _frame(0, eye_y=0.5, foot_y=0.9),  # Flexionado
            _frame(1, eye_y=0.1, foot_y=0.9),  # Erguido
        ),
        fps=30.0,
    )

    escala = estimate_scale(secuencia, height_m=1.75)

    assert escala is not None
    assert escala.meters_per_unit == pytest.approx(1.75 / (0.8 / 0.94))


def test_una_secuencia_sin_poses_no_produce_escala() -> None:
    vacia = PoseSequence(frames=(PoseFrame(index=0, timestamp_ms=0, landmarks=()),), fps=30.0)

    assert estimate_scale(vacia, height_m=1.75) is None


def test_un_atleta_mas_alto_produce_una_escala_mayor() -> None:
    secuencia = PoseSequence(frames=(_frame(0, 0.1, 0.9),), fps=30.0)

    baja = estimate_scale(secuencia, height_m=1.60)
    alta = estimate_scale(secuencia, height_m=1.90)

    assert baja is not None and alta is not None
    assert alta.meters_per_unit > baja.meters_per_unit


@pytest.mark.parametrize("altura", [1.20, 1.75, 2.30])
def test_acepta_estaturas_plausibles(altura: float) -> None:
    assert validate_height(altura) == altura


@pytest.mark.parametrize("altura", [0.5, 1.19, 2.31, 175.0])
def test_rechaza_estaturas_fuera_de_rango(altura: float) -> None:
    with pytest.raises(InvalidHeightError, match="estatura"):
        validate_height(altura)
