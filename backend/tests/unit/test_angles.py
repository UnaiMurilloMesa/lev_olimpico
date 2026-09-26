"""Pruebas del cálculo de ángulos articulares."""

import math

import pytest

from app.domain.angles import JOINT_DEFINITIONS, JointName, angle_between, joint_angles
from app.domain.landmarks import Landmark, PoseFrame, PoseLandmarkId


def _point(x: float, y: float) -> Landmark:
    return Landmark(x=x, y=y, z=0.0, visibility=1.0)


def test_tres_puntos_alineados_forman_180_grados() -> None:
    angulo = angle_between(_point(0.0, 0.0), _point(0.5, 0.0), _point(1.0, 0.0))

    assert angulo == pytest.approx(180.0)


def test_un_angulo_recto_mide_90_grados() -> None:
    angulo = angle_between(_point(0.0, 0.0), _point(0.0, 1.0), _point(1.0, 1.0))

    assert angulo == pytest.approx(90.0)


def test_un_angulo_de_45_grados() -> None:
    angulo = angle_between(_point(1.0, 0.0), _point(0.0, 0.0), _point(1.0, 1.0))

    assert angulo == pytest.approx(45.0)


def test_los_puntos_coincidentes_devuelven_cero() -> None:
    origen = _point(0.5, 0.5)

    assert angle_between(origen, origen, _point(1.0, 1.0)) == 0.0


def test_el_angulo_es_simetrico_respecto_al_orden_de_los_extremos() -> None:
    a, vertice, b = _point(0.0, 0.0), _point(0.5, 0.5), _point(1.0, 0.0)

    assert angle_between(a, vertice, b) == pytest.approx(angle_between(b, vertice, a))


def test_el_angulo_nunca_supera_los_180_grados() -> None:
    for grados in range(0, 360, 15):
        radianes = math.radians(grados)
        extremo = _point(math.cos(radianes), math.sin(radianes))

        angulo = angle_between(_point(1.0, 0.0), _point(0.0, 0.0), extremo)

        assert 0.0 <= angulo <= 180.0


def test_calcula_todas_las_articulaciones_definidas() -> None:
    landmarks = tuple(_point(index / 100, index / 100) for index in range(33))
    frame = PoseFrame(index=0, timestamp_ms=0, landmarks=landmarks)

    angulos = joint_angles(frame)

    assert set(angulos) == set(JointName)
    assert len(angulos) == 10


def test_un_fotograma_sin_pose_no_produce_angulos() -> None:
    frame = PoseFrame(index=0, timestamp_ms=0, landmarks=())

    assert joint_angles(frame) == {}


def test_la_rodilla_extendida_se_acerca_a_180_grados() -> None:
    """Pierna recta: cadera, rodilla y tobillo en vertical."""
    landmarks = [_point(0.5, 0.5) for _ in range(33)]
    landmarks[PoseLandmarkId.LEFT_HIP] = _point(0.5, 0.4)
    landmarks[PoseLandmarkId.LEFT_KNEE] = _point(0.5, 0.6)
    landmarks[PoseLandmarkId.LEFT_ANKLE] = _point(0.5, 0.8)
    frame = PoseFrame(index=0, timestamp_ms=0, landmarks=tuple(landmarks))

    assert joint_angles(frame)[JointName.LEFT_KNEE] == pytest.approx(180.0)


def test_la_rodilla_flexionada_da_un_angulo_menor() -> None:
    """Sentadilla profunda: el tobillo queda bajo la cadera."""
    landmarks = [_point(0.5, 0.5) for _ in range(33)]
    landmarks[PoseLandmarkId.LEFT_HIP] = _point(0.5, 0.5)
    landmarks[PoseLandmarkId.LEFT_KNEE] = _point(0.6, 0.6)
    landmarks[PoseLandmarkId.LEFT_ANKLE] = _point(0.5, 0.7)
    frame = PoseFrame(index=0, timestamp_ms=0, landmarks=tuple(landmarks))

    assert joint_angles(frame)[JointName.LEFT_KNEE] < 100.0


@pytest.mark.parametrize("joint", list(JointName))
def test_cada_articulacion_usa_tres_puntos_distintos(joint: JointName) -> None:
    definicion = JOINT_DEFINITIONS[joint]

    assert len({definicion.first, definicion.vertex, definicion.second}) == 3
