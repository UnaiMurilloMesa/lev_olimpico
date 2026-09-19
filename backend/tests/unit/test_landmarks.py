"""Pruebas del modelo de dominio de puntos corporales."""

import pytest

from app.domain.landmarks import ConfidenceLevel, Landmark, PoseFrame, PoseLandmarkId


def _landmark(visibility: float = 1.0, x: float = 0.5, y: float = 0.5) -> Landmark:
    return Landmark(x=x, y=y, z=0.0, visibility=visibility)


@pytest.mark.parametrize(
    ("visibility", "expected"),
    [
        (1.0, ConfidenceLevel.HIGH),
        (0.75, ConfidenceLevel.HIGH),
        (0.74, ConfidenceLevel.MEDIUM),
        (0.40, ConfidenceLevel.MEDIUM),
        (0.39, ConfidenceLevel.LOW),
        (0.0, ConfidenceLevel.LOW),
    ],
)
def test_clasifica_la_confianza_segun_la_visibilidad(
    visibility: float, expected: ConfidenceLevel
) -> None:
    assert _landmark(visibility).confidence is expected


def test_convierte_coordenadas_normalizadas_a_pixeles() -> None:
    landmark = _landmark(x=0.5, y=0.25)

    assert landmark.to_pixels(width=1920, height=1080) == (960, 270)


def test_un_fotograma_sin_puntos_no_tiene_pose_detectada() -> None:
    frame = PoseFrame(index=0, timestamp_ms=0, landmarks=())

    assert frame.is_detected is False


def test_acceder_a_un_punto_sin_pose_detectada_falla() -> None:
    frame = PoseFrame(index=7, timestamp_ms=0, landmarks=())

    with pytest.raises(LookupError, match="7"):
        frame.landmark(PoseLandmarkId.LEFT_HIP)


def test_devuelve_el_punto_solicitado_por_su_identificador() -> None:
    landmarks = tuple(_landmark(x=i / 100) for i in range(33))
    frame = PoseFrame(index=0, timestamp_ms=0, landmarks=landmarks)

    assert frame.landmark(PoseLandmarkId.LEFT_HIP).x == pytest.approx(0.23)