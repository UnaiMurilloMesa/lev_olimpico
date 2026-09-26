"""Pruebas de la detección del final del levantamiento."""

import pytest

from app.domain.landmarks import Landmark, PoseFrame, PoseLandmarkId
from app.domain.lift_detection import (
    LiftDetectionConfig,
    bar_heights_from,
    detect_lift_end,
    detect_lift_window,
)
from app.domain.sequence import PoseSequence

FPS = 30.0


def _frame(index: int, bar_y: float | None) -> PoseFrame:
    if bar_y is None:
        return PoseFrame(index=index, timestamp_ms=index * 33, landmarks=())
    landmarks = [Landmark(0.5, 0.5, 0.0, 1.0) for _ in range(33)]
    landmarks[PoseLandmarkId.LEFT_WRIST] = Landmark(0.5, bar_y, 0.0, 1.0)
    landmarks[PoseLandmarkId.RIGHT_WRIST] = Landmark(0.5, bar_y, 0.0, 1.0)
    return PoseFrame(index=index, timestamp_ms=index * 33, landmarks=tuple(landmarks))


def _sequence(bar_ys: list[float | None]) -> PoseSequence:
    return PoseSequence(
        frames=tuple(_frame(index, y) for index, y in enumerate(bar_ys)), fps=FPS
    )


def _lift(subida: int = 20, estable: int = 30) -> list[float | None]:
    """Barra que sube desde el suelo y luego se mantiene arriba."""
    descenso = [0.9 - 0.03 * paso for paso in range(subida)]
    return descenso + [descenso[-1]] * estable


def test_la_altura_se_mide_invertida_respecto_al_eje_de_imagen() -> None:
    """Una barra arriba (y pequeña) debe dar una altura grande."""
    alturas = bar_heights_from(_sequence([0.9, 0.2]), start_index=0)

    assert alturas.values[0] == pytest.approx(0.1)
    assert alturas.values[1] == pytest.approx(0.8)


def test_localiza_el_punto_mas_alto_de_la_barra() -> None:
    alturas = bar_heights_from(_sequence([0.9, 0.5, 0.2, 0.4]), start_index=0)

    assert alturas.highest_index() == 2


def test_ignora_los_fotogramas_previos_al_inicio() -> None:
    alturas = bar_heights_from(_sequence([0.9, 0.8, 0.3]), start_index=2)

    assert len(alturas.values) == 1


def test_detecta_el_final_cuando_la_barra_se_estabiliza() -> None:
    final = detect_lift_end(_sequence(_lift()), start_index=0)

    # La barra deja de subir en el fotograma 19; el tramo estable de 400 ms
    # (12 fotogramas) se completa poco después.
    assert 19 <= final <= 35


def test_un_movimiento_sin_estabilizar_se_acota_por_duracion_maxima() -> None:
    oscilante = [0.9 - 0.3 * (indice % 2) for indice in range(200)]
    config = LiftDetectionConfig(max_lift_ms=2000)

    final = detect_lift_end(_sequence(oscilante), start_index=0, config=config)

    assert final == 60  # 2 segundos a 30 fps


def test_una_secuencia_sin_pose_devuelve_el_limite() -> None:
    sin_pose = _sequence([None] * 40)
    config = LiftDetectionConfig(max_lift_ms=1000)

    final = detect_lift_end(sin_pose, start_index=0, config=config)

    assert final == 30


def test_el_final_nunca_precede_al_inicio() -> None:
    ventana = detect_lift_window(_sequence(_lift()), start_seconds=0.5)

    assert ventana.end_index >= ventana.start_index


def test_la_ventana_arranca_en_el_instante_indicado() -> None:
    ventana = detect_lift_window(_sequence(_lift(subida=20, estable=60)), start_seconds=0.2)

    assert ventana.start_index == 6


def test_el_final_no_supera_el_ultimo_fotograma() -> None:
    ventana = detect_lift_window(_sequence(_lift(subida=10, estable=5)), start_seconds=0.0)

    assert ventana.end_index <= 14


def test_un_pequeno_temblor_no_impide_detectar_la_estabilizacion() -> None:
    """El umbral debe tolerar el ruido residual de la detección."""
    subida = [0.9 - 0.03 * paso for paso in range(20)]
    temblor = [subida[-1] + 0.004 * (1 if indice % 2 else -1) for indice in range(30)]

    final = detect_lift_end(_sequence(subida + temblor), start_index=0)

    assert final < 49

def test_ante_alturas_iguales_se_toma_la_primera() -> None:
    """Tras la recepción la barra se mantiene arriba; el pico es cuando llega."""
    alturas = bar_heights_from(_sequence([0.9, 0.5, 0.2, 0.2, 0.2]), start_index=0)

    assert alturas.highest_index() == 2