"""Pruebas de la acotación temporal del levantamiento."""

import pytest

from app.domain.landmarks import Landmark, PoseFrame
from app.domain.lift_window import (
    InvalidLiftWindowError,
    LiftWindow,
    slice_sequence,
)
from app.domain.sequence import PoseSequence

FPS = 30.0


def _sequence(count: int, fps: float = FPS) -> PoseSequence:
    frames = tuple(
        PoseFrame(
            index=index,
            timestamp_ms=int(index * 1000 / fps),
            landmarks=tuple(Landmark(0.5, 0.5, 0.0, 1.0) for _ in range(33)),
        )
        for index in range(count)
    )
    return PoseSequence(frames=frames, fps=fps)


def test_la_ventana_incluye_ambos_extremos() -> None:
    ventana = LiftWindow(start_index=10, end_index=20)

    assert len(ventana) == 11
    assert ventana.contains(10) is True
    assert ventana.contains(20) is True


def test_los_fotogramas_fuera_de_la_ventana_se_descartan() -> None:
    ventana = LiftWindow(start_index=10, end_index=20)

    assert ventana.contains(9) is False
    assert ventana.contains(21) is False


def test_una_ventana_invertida_no_es_valida() -> None:
    with pytest.raises(InvalidLiftWindowError, match="precede"):
        LiftWindow(start_index=20, end_index=10)


def test_una_ventana_negativa_no_es_valida() -> None:
    with pytest.raises(InvalidLiftWindowError, match="negativo"):
        LiftWindow(start_index=-1, end_index=10)


def test_calcula_la_duracion_en_segundos() -> None:
    ventana = LiftWindow(start_index=0, end_index=29)

    assert ventana.duration_seconds(FPS) == pytest.approx(1.0)


def test_convierte_segundos_a_indices_de_fotograma() -> None:
    ventana = LiftWindow.from_seconds(1.0, _sequence(90))

    assert ventana.start_index == 30
    assert ventana.end_index == 89


def test_respeta_un_instante_final_explicito() -> None:
    ventana = LiftWindow.from_seconds(1.0, _sequence(150), end_seconds=3.0)

    assert (ventana.start_index, ventana.end_index) == (30, 90)


def test_un_final_posterior_al_video_se_acota_al_ultimo_fotograma() -> None:
    ventana = LiftWindow.from_seconds(0.0, _sequence(60), end_seconds=99.0)

    assert ventana.end_index == 59


def test_un_inicio_fuera_del_video_no_es_valido() -> None:
    with pytest.raises(InvalidLiftWindowError, match="excede"):
        LiftWindow.from_seconds(10.0, _sequence(60))


def test_una_secuencia_vacia_no_se_puede_acotar() -> None:
    with pytest.raises(InvalidLiftWindowError, match="vacía"):
        LiftWindow.from_seconds(0.0, PoseSequence(frames=(), fps=FPS))


def test_los_indices_se_calculan_segun_los_fps_reales() -> None:
    """A 60 fps, un segundo son 60 fotogramas, no 30."""
    ventana = LiftWindow.from_seconds(1.0, _sequence(180, fps=60.0))

    assert ventana.start_index == 60


def test_el_recorte_devuelve_solo_los_fotogramas_de_la_ventana() -> None:
    recortada = slice_sequence(_sequence(100), LiftWindow(20, 40))

    assert len(recortada) == 21


def test_el_recorte_conserva_los_indices_originales() -> None:
    recortada = slice_sequence(_sequence(100), LiftWindow(20, 40))

    assert recortada.frames[0].index == 20
    assert recortada.frames[-1].index == 40


def test_el_recorte_conserva_los_fps() -> None:
    recortada = slice_sequence(_sequence(100, fps=60.0), LiftWindow(10, 20))

    assert recortada.fps == 60.0