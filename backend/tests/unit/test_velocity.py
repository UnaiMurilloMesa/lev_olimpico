"""Pruebas del cálculo de velocidad de la barra."""

import pytest

from app.domain.landmarks import Landmark, PoseFrame, PoseLandmarkId
from app.domain.scale import BodyScale
from app.domain.sequence import PoseSequence
from app.services.analysis.velocity import compute_bar_velocity

FPS = 30.0
SCALE = BodyScale(meters_per_unit=2.0)


def _frame(index: int, bar_y: float | None) -> PoseFrame:
    if bar_y is None:
        return PoseFrame(index=index, timestamp_ms=index * 33, landmarks=())
    landmarks = [Landmark(0.5, 0.5, 0.0, 1.0) for _ in range(33)]
    for wrist in (PoseLandmarkId.LEFT_WRIST, PoseLandmarkId.RIGHT_WRIST):
        landmarks[wrist] = Landmark(0.5, bar_y, 0.0, 1.0)
    return PoseFrame(index=index, timestamp_ms=index * 33, landmarks=tuple(landmarks))


def _sequence(bar_ys: list[float | None], fps: float = FPS) -> PoseSequence:
    return PoseSequence(frames=tuple(_frame(index, y) for index, y in enumerate(bar_ys)), fps=fps)


def test_una_barra_inmovil_tiene_velocidad_nula() -> None:
    velocidad = compute_bar_velocity(_sequence([0.5] * 30), SCALE)

    assert all(abs(muestra.velocity_ms) < 1e-6 for muestra in velocidad.samples)


def test_la_barra_subiendo_da_velocidad_positiva() -> None:
    """La coordenada y decrece al subir; la velocidad debe salir positiva."""
    subida = [0.9 - 0.01 * paso for paso in range(30)]

    velocidad = compute_bar_velocity(_sequence(subida), SCALE)

    assert velocidad.peak_velocity_ms > 0


def test_la_barra_bajando_da_velocidad_negativa() -> None:
    bajada = [0.1 + 0.01 * paso for paso in range(30)]

    velocidad = compute_bar_velocity(_sequence(bajada), SCALE)

    assert all(muestra.velocity_ms < 0 for muestra in velocidad.samples[5:-5])


def test_calcula_correctamente_una_velocidad_constante() -> None:
    """0.01 unidades por fotograma a 30 fps y escala 2 m/unidad = 0.6 m/s."""
    subida = [0.9 - 0.01 * paso for paso in range(40)]

    velocidad = compute_bar_velocity(_sequence(subida), SCALE)

    assert velocidad.peak_velocity_ms == pytest.approx(0.6, abs=0.01)


def test_la_escala_multiplica_la_velocidad() -> None:
    subida = [0.9 - 0.01 * paso for paso in range(40)]

    lenta = compute_bar_velocity(_sequence(subida), BodyScale(1.0))
    rapida = compute_bar_velocity(_sequence(subida), BodyScale(2.0))

    assert rapida.peak_velocity_ms == pytest.approx(2 * lenta.peak_velocity_ms)


def test_los_fps_afectan_a_la_velocidad() -> None:
    """El mismo desplazamiento por fotograma a doble tasa es doble velocidad."""
    subida = [0.9 - 0.01 * paso for paso in range(40)]

    treinta = compute_bar_velocity(_sequence(subida, fps=30.0), SCALE)
    sesenta = compute_bar_velocity(_sequence(subida, fps=60.0), SCALE)

    assert sesenta.peak_velocity_ms == pytest.approx(2 * treinta.peak_velocity_ms, rel=0.05)


def test_localiza_el_instante_de_velocidad_maxima() -> None:
    lenta = [0.9 - 0.002 * paso for paso in range(20)]
    rapida = [lenta[-1] - 0.02 * paso for paso in range(20)]

    velocidad = compute_bar_velocity(_sequence(lenta + rapida), SCALE)

    assert velocidad.peak_time_seconds > 0.5


def test_el_tiempo_arranca_en_cero() -> None:
    velocidad = compute_bar_velocity(_sequence([0.5] * 20), SCALE)

    assert velocidad.samples[0].time_seconds == 0.0


def test_omite_los_fotogramas_sin_pose() -> None:
    valores: list[float | None] = [0.9, 0.8, None, 0.6, 0.5, 0.4, 0.3, 0.2]

    velocidad = compute_bar_velocity(_sequence(valores), SCALE)

    assert len(velocidad) == 7


def test_una_secuencia_demasiado_corta_no_produce_muestras() -> None:
    velocidad = compute_bar_velocity(_sequence([0.5, 0.4]), SCALE)

    assert len(velocidad) == 0
    assert velocidad.peak_velocity_ms == 0.0


def test_devuelve_la_serie_para_representarla() -> None:
    velocidad = compute_bar_velocity(_sequence([0.5] * 20), SCALE)

    tiempos, valores = velocidad.as_series()

    assert len(tiempos) == len(valores) == 20


def test_las_series_cortas_no_descartan_muestras() -> None:
    velocidad = compute_bar_velocity(_sequence([0.9, 0.7, 0.5, 0.3, 0.1]), SCALE)

    assert len(velocidad.reliable_samples) == len(velocidad)


def test_la_serie_completa_sigue_disponible_para_la_grafica() -> None:
    subida = [0.9 - 0.01 * paso for paso in range(40)]

    velocidad = compute_bar_velocity(_sequence(subida), SCALE)
    tiempos, _ = velocidad.as_series()

    assert len(tiempos) == 40
    assert len(velocidad.reliable_samples) < 40


def test_el_margen_descartado_es_media_ventana_de_suavizado() -> None:
    velocidad = compute_bar_velocity(_sequence([0.5] * 40), SCALE)

    assert velocidad.edge_margin == 3  # ventana de 7 fotogramas a 30 fps


def test_el_pico_nunca_cae_en_los_fotogramas_descartados() -> None:
    """Un artefacto en el borde inicial no puede ser el pico."""
    salto = [0.9, 0.1]
    movimiento = [0.1 + 0.003 * paso for paso in range(40)]

    velocidad = compute_bar_velocity(_sequence(salto + movimiento), SCALE)

    descartados = velocidad.samples[: velocidad.edge_margin]
    assert velocidad.peak not in descartados


def test_el_pico_nunca_cae_en_el_borde_final() -> None:
    movimiento = [0.9 - 0.003 * paso for paso in range(40)]
    salto = [0.3, 0.0]

    velocidad = compute_bar_velocity(_sequence(movimiento + salto), SCALE)

    descartados = velocidad.samples[-velocidad.edge_margin :]
    assert velocidad.peak not in descartados