"""Pruebas de la secuencia temporal de poses."""

import pytest

from app.domain.landmarks import Landmark, PoseFrame, PoseLandmarkId
from app.domain.sequence import PoseSequence


def _frame(index: int, detected: bool = True, x: float = 0.5) -> PoseFrame:
    landmarks = (
        tuple(Landmark(x=x, y=0.5, z=0.0, visibility=1.0) for _ in range(33))
        if detected
        else ()
    )
    return PoseFrame(index=index, timestamp_ms=index * 33, landmarks=landmarks)


def _sequence(*frames: PoseFrame, fps: float = 30.0) -> PoseSequence:
    return PoseSequence(frames=frames, fps=fps)


def test_cuenta_los_fotogramas() -> None:
    assert len(_sequence(_frame(0), _frame(1), _frame(2))) == 3


def test_calcula_la_proporcion_de_deteccion() -> None:
    secuencia = _sequence(_frame(0), _frame(1, detected=False), _frame(2), _frame(3))

    assert secuencia.detected_count == 3
    assert secuencia.detection_ratio == pytest.approx(0.75)


def test_una_secuencia_vacia_no_divide_entre_cero() -> None:
    assert _sequence().detection_ratio == 0.0


def test_extrae_la_trayectoria_de_un_punto() -> None:
    secuencia = _sequence(_frame(0, x=0.1), _frame(1, x=0.2), _frame(2, x=0.3))

    trayectoria = secuencia.coordinates_of(PoseLandmarkId.LEFT_WRIST)

    assert [punto[0] for punto in trayectoria] == [0.1, 0.2, 0.3]


def test_los_fotogramas_sin_deteccion_aparecen_como_huecos() -> None:
    secuencia = _sequence(_frame(0), _frame(1, detected=False), _frame(2))

    trayectoria = secuencia.coordinates_of(PoseLandmarkId.NOSE)

    assert trayectoria[1] is None
    assert trayectoria[0] is not None


@pytest.mark.parametrize(
    ("fps", "milisegundos", "esperado"),
    [
        (30.0, 230, 7),
        (60.0, 230, 15),
        (30.0, 100, 3),
        (60.0, 500, 31),
    ],
)
def test_traduce_la_ventana_temporal_a_fotogramas_impares(
    fps: float, milisegundos: int, esperado: int
) -> None:
    ventana = _sequence(fps=fps).window_size_for(milisegundos)

    assert ventana == esperado
    assert ventana % 2 == 1


def test_la_ventana_nunca_es_menor_que_tres() -> None:
    assert _sequence(fps=30.0).window_size_for(10) == 3


def test_sustituir_los_fotogramas_conserva_los_fps() -> None:
    original = _sequence(_frame(0), fps=60.0)

    nueva = original.replacing_frames((_frame(0), _frame(1)))

    assert nueva.fps == 60.0
    assert len(nueva) == 2