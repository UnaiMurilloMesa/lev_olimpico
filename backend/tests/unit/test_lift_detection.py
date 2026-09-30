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
    for wrist in (PoseLandmarkId.LEFT_WRIST, PoseLandmarkId.RIGHT_WRIST):
        landmarks[wrist] = Landmark(0.5, bar_y, 0.0, 1.0)
    return PoseFrame(index=index, timestamp_ms=index * 33, landmarks=tuple(landmarks))


def _sequence(bar_ys: list[float | None]) -> PoseSequence:
    return PoseSequence(
        frames=tuple(_frame(index, y) for index, y in enumerate(bar_ys)), fps=FPS
    )


def _snatch() -> list[float | None]:
    """Curva típica: tirón, recepción y punto más alto al incorporarse."""
    tiron = [0.90 - 0.020 * paso for paso in range(30)]      # sube hasta 0.30
    recepcion = [0.30 + 0.010 * paso for paso in range(10)]  # baja hasta 0.40
    recuperacion = [0.40 - 0.015 * paso for paso in range(20)]  # máximo en 0.115
    sostenida = [0.15] * 15                                     # la barra baja al sostenerla
    return tiron + recepcion + recuperacion + sostenida


# --- Medición de alturas ---


def test_la_altura_se_mide_invertida_respecto_al_eje_de_imagen() -> None:
    alturas = bar_heights_from(_sequence([0.9, 0.2]), start_index=0)

    assert alturas.values[0] == pytest.approx(0.1)
    assert alturas.values[1] == pytest.approx(0.8)


def test_localiza_el_punto_mas_alto_de_la_barra() -> None:
    alturas = bar_heights_from(_sequence([0.9, 0.5, 0.2, 0.4]), start_index=0)

    assert alturas.highest_index() == 2


def test_ante_alturas_iguales_se_toma_la_primera() -> None:
    alturas = bar_heights_from(_sequence([0.9, 0.5, 0.2, 0.2, 0.2]), start_index=0)

    assert alturas.highest_index() == 2


def test_ignora_los_fotogramas_previos_al_inicio() -> None:
    alturas = bar_heights_from(_sequence([0.9, 0.8, 0.3]), start_index=2)

    assert len(alturas.values) == 1


def test_una_secuencia_sin_pose_no_tiene_maximo() -> None:
    alturas = bar_heights_from(_sequence([None, None]), start_index=0)

    assert alturas.highest_index() is None


# --- Detección del final ---


def test_el_final_es_el_punto_mas_alto_de_la_barra() -> None:
    """En la curva del snatch, el máximo llega al terminar de incorporarse."""
    final = detect_lift_end(_sequence(_snatch()), start_index=0)

    assert final == 59


def test_ignora_lo_que_ocurre_tras_el_punto_mas_alto() -> None:
    """Soltar la barra al acabar no debe alargar la ventana."""
    caida = [0.15 + 0.05 * paso for paso in range(20)]

    final = detect_lift_end(_sequence(_snatch() + caida), start_index=0)

    assert final == 59


def test_el_descenso_de_la_recepcion_no_se_confunde_con_el_final() -> None:
    final = detect_lift_end(_sequence(_snatch()), start_index=0)

    # El mínimo local de la recepción está en el fotograma 39.
    assert final > 39


def test_respeta_una_duracion_minima() -> None:
    """Un máximo inmediato no debe producir una ventana degenerada."""
    engañosa = [0.2] + [0.9 - 0.01 * paso for paso in range(60)]
    config = LiftDetectionConfig(min_lift_ms=1000)

    final = detect_lift_end(_sequence(engañosa), start_index=0, config=config)

    assert final == 30  # 1 segundo a 30 fps


def test_se_acota_por_la_duracion_maxima() -> None:
    ascenso = [0.95 - 0.004 * indice for indice in range(300)]
    config = LiftDetectionConfig(max_lift_ms=2000)

    final = detect_lift_end(_sequence(ascenso), start_index=0, config=config)

    assert final == 60


def test_una_secuencia_sin_pose_se_acota_por_duracion_maxima() -> None:
    config = LiftDetectionConfig(max_lift_ms=1000)

    final = detect_lift_end(_sequence([None] * 60), start_index=0, config=config)

    assert final == 30


def test_el_final_no_supera_el_ultimo_fotograma() -> None:
    final = detect_lift_end(_sequence(_snatch()[:20]), start_index=0)

    assert final <= 19


# --- Construcción de la ventana ---


def test_la_ventana_arranca_en_el_instante_indicado() -> None:
    ventana = detect_lift_window(_sequence(_snatch()), start_seconds=0.2)

    assert ventana.start_index == 6


def test_el_final_nunca_precede_al_inicio() -> None:
    ventana = detect_lift_window(_sequence(_snatch()), start_seconds=0.5)

    assert ventana.end_index >= ventana.start_index


def test_la_ventana_cubre_el_levantamiento_completo() -> None:
    ventana = detect_lift_window(_sequence(_snatch()), start_seconds=0.0)

    assert ventana.duration_seconds(FPS) == pytest.approx(2.0, abs=0.1)