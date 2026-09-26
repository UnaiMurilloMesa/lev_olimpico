"""Pruebas del renderizador de esqueleto."""

import numpy as np

from app.domain.landmarks import Landmark, PoseFrame, PoseLandmarkId
from app.services.pose.renderer import (
    COLOR_HIGH_CONFIDENCE,
    COLOR_LOW_CONFIDENCE,
    SkeletonRenderer,
)

FRAME_SIZE = 100


def _blank_frame() -> np.ndarray:
    return np.zeros((FRAME_SIZE, FRAME_SIZE, 3), dtype=np.uint8)


def _pose_with(overrides: dict[int, Landmark]) -> PoseFrame:
    """Crea una pose de 33 puntos, con los indicados sobrescritos."""
    landmarks = [Landmark(x=0.0, y=0.0, z=0.0, visibility=0.0) for _ in range(33)]
    for index, landmark in overrides.items():
        landmarks[index] = landmark
    return PoseFrame(index=0, timestamp_ms=0, landmarks=tuple(landmarks))


def test_no_modifica_el_fotograma_original() -> None:
    original = _blank_frame()
    pose = _pose_with({PoseLandmarkId.NOSE: Landmark(0.5, 0.5, 0.0, 1.0)})

    SkeletonRenderer().render(original, pose)

    assert not original.any()


def test_devuelve_el_fotograma_intacto_si_no_hay_pose() -> None:
    original = _blank_frame()
    pose = PoseFrame(index=0, timestamp_ms=0, landmarks=())

    resultado = SkeletonRenderer().render(original, pose)

    assert np.array_equal(resultado, original)


def test_pinta_de_verde_un_punto_de_alta_confianza() -> None:
    pose = _pose_with({PoseLandmarkId.NOSE: Landmark(0.5, 0.5, 0.0, 0.9)})

    resultado = SkeletonRenderer().render(_blank_frame(), pose)

    assert tuple(resultado[50, 50]) == COLOR_HIGH_CONFIDENCE


def test_pinta_de_rojo_un_punto_de_baja_confianza() -> None:
    pose = _pose_with({PoseLandmarkId.NOSE: Landmark(0.5, 0.5, 0.0, 0.1)})

    resultado = SkeletonRenderer().render(_blank_frame(), pose)

    assert tuple(resultado[50, 50]) == COLOR_LOW_CONFIDENCE


def test_el_segmento_toma_el_color_del_extremo_menos_fiable() -> None:
    pose = _pose_with(
        {
            PoseLandmarkId.LEFT_SHOULDER: Landmark(0.2, 0.5, 0.0, 0.95),
            PoseLandmarkId.RIGHT_SHOULDER: Landmark(0.8, 0.5, 0.0, 0.10),
        }
    )

    resultado = SkeletonRenderer().render(_blank_frame(), pose)

    # Punto medio del segmento entre ambos hombros.
    assert tuple(resultado[50, 50]) == COLOR_LOW_CONFIDENCE
