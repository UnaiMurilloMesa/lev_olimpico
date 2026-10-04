"""Pruebas de la detección de eventos que separan las fases."""

import pytest

from app.domain.landmarks import Landmark, PoseFrame, PoseLandmarkId
from app.domain.lift_window import LiftWindow
from app.domain.phase_detection import (
    PhaseDetectionConfig,
    bar_height,
    detect_phases,
    find_bar_peak,
    find_catch,
    find_hip_extension,
    find_knee_pass,
    hip_height,
    knee_height,
)
from app.domain.phases import LiftPhase
from app.domain.sequence import PoseSequence

FPS = 30.0


def _frame(
    index: int,
    bar_y: float = 0.9,
    knee_y: float = 0.7,
    hip_y: float = 0.6,
    shoulder_y: float = 0.4,
    ankle_y: float = 0.9,
    knee_x: float = 0.5,
    detected: bool = True,
) -> PoseFrame:
    """Fotograma con las alturas verticales indicadas, todo alineado en x."""
    if not detected:
        return PoseFrame(index=index, timestamp_ms=index * 33, landmarks=())

    points = [Landmark(0.5, 0.5, 0.0, 1.0) for _ in range(33)]
    for wrist in (PoseLandmarkId.LEFT_WRIST, PoseLandmarkId.RIGHT_WRIST):
        points[wrist] = Landmark(0.5, bar_y, 0.0, 1.0)
    for knee in (PoseLandmarkId.LEFT_KNEE, PoseLandmarkId.RIGHT_KNEE):
        points[knee] = Landmark(knee_x, knee_y, 0.0, 1.0)
    for hip in (PoseLandmarkId.LEFT_HIP, PoseLandmarkId.RIGHT_HIP):
        points[hip] = Landmark(0.5, hip_y, 0.0, 1.0)
    for shoulder in (PoseLandmarkId.LEFT_SHOULDER, PoseLandmarkId.RIGHT_SHOULDER):
        points[shoulder] = Landmark(0.5, shoulder_y, 0.0, 1.0)
    for ankle in (PoseLandmarkId.LEFT_ANKLE, PoseLandmarkId.RIGHT_ANKLE):
        points[ankle] = Landmark(0.5, ankle_y, 0.0, 1.0)

    return PoseFrame(index=index, timestamp_ms=index * 33, landmarks=tuple(points))


def _sequence(frames: list[PoseFrame]) -> PoseSequence:
    return PoseSequence(frames=tuple(frames), fps=FPS)


# --- Medidas básicas ---


def test_la_altura_de_la_barra_se_mide_invertida() -> None:
    assert bar_height(_frame(0, bar_y=0.8)) == pytest.approx(0.2)


def test_la_altura_de_la_rodilla_promedia_ambas_piernas() -> None:
    assert knee_height(_frame(0, knee_y=0.7)) == pytest.approx(0.3)


def test_la_altura_de_la_cadera_promedia_ambos_lados() -> None:
    assert hip_height(_frame(0, hip_y=0.6)) == pytest.approx(0.4)


def test_un_fotograma_sin_pose_no_aporta_medidas() -> None:
    vacio = _frame(0, detected=False)

    assert bar_height(vacio) is None
    assert knee_height(vacio) is None
    assert hip_height(vacio) is None


# --- Paso por la rodilla ---


def test_detecta_cuando_la_barra_alcanza_la_rodilla() -> None:
    """La barra sube desde el suelo hasta superar la altura de la rodilla."""
    frames = [_frame(i, bar_y=0.95 - 0.03 * i, knee_y=0.70) for i in range(15)]

    indice = find_knee_pass(_sequence(frames), PhaseDetectionConfig())

    # bar_y alcanza 0.72 (dentro de la tolerancia de 0.02) en el fotograma 8.
    assert indice == 8


def test_sin_paso_por_la_rodilla_no_hay_evento() -> None:
    frames = [_frame(i, bar_y=0.95, knee_y=0.40) for i in range(10)]

    assert find_knee_pass(_sequence(frames), PhaseDetectionConfig()) is None


def test_la_tolerancia_adelanta_la_deteccion() -> None:
    frames = [_frame(i, bar_y=0.95 - 0.03 * i, knee_y=0.70) for i in range(15)]

    estricta = find_knee_pass(_sequence(frames), PhaseDetectionConfig(knee_tolerance=0.0))
    laxa = find_knee_pass(_sequence(frames), PhaseDetectionConfig(knee_tolerance=0.10))

    assert laxa is not None and estricta is not None
    assert laxa < estricta


# --- Extensión de cadera ---


def test_detecta_la_maxima_extension_de_cadera() -> None:
    """El ángulo de cadera es máximo cuando tronco y muslo se alinean."""
    frames = [
        _frame(0, hip_y=0.60, shoulder_y=0.50, knee_y=0.70, knee_x=0.70),  # flexionado
        _frame(1, hip_y=0.60, shoulder_y=0.40, knee_y=0.72, knee_x=0.62),  # intermedio
        _frame(2, hip_y=0.60, shoulder_y=0.30, knee_y=0.75, knee_x=0.50),  # extendido
        _frame(3, hip_y=0.60, shoulder_y=0.45, knee_y=0.70, knee_x=0.66),  # flexiona
    ]

    assert find_hip_extension(_sequence(frames), after_index=-1) == 2


def test_la_extension_se_busca_tras_el_evento_anterior() -> None:
    frames = [
        _frame(0, hip_y=0.60, shoulder_y=0.30, knee_y=0.75, knee_x=0.50),  # máximo global
        _frame(1, hip_y=0.60, shoulder_y=0.50, knee_y=0.70, knee_x=0.72),  # flexionado
        _frame(2, hip_y=0.60, shoulder_y=0.35, knee_y=0.74, knee_x=0.55),  # máximo posterior
    ]

    assert find_hip_extension(_sequence(frames), after_index=0) == 2


# --- Altura máxima de la barra ---


def test_detecta_la_altura_maxima_de_la_barra() -> None:
    frames = [_frame(i, bar_y=y) for i, y in enumerate([0.9, 0.6, 0.3, 0.5, 0.7])]

    assert find_bar_peak(_sequence(frames), after_index=-1) == 2


def test_el_pico_de_barra_se_busca_tras_el_evento_anterior() -> None:
    frames = [_frame(i, bar_y=y) for i, y in enumerate([0.1, 0.9, 0.4, 0.8])]

    assert find_bar_peak(_sequence(frames), after_index=0) == 2


# --- Recepción ---


def test_detecta_el_punto_mas_bajo_de_la_recepcion() -> None:
    """La cadera baja al recibir en sentadilla y luego sube al incorporarse."""
    frames = [_frame(i, hip_y=y) for i, y in enumerate([0.40, 0.60, 0.75, 0.55, 0.35])]

    assert find_catch(_sequence(frames), after_index=-1) == 2


def test_la_recepcion_se_busca_tras_la_segunda_tirada() -> None:
    frames = [_frame(i, hip_y=y) for i, y in enumerate([0.90, 0.40, 0.70, 0.45])]

    assert find_catch(_sequence(frames), after_index=0) == 2


# --- División completa ---


def _snatch_frames() -> list[PoseFrame]:
    """Secuencia sintética con los cuatro eventos en orden."""
    frames: list[PoseFrame] = []

    # Primera tirada: barra desde el suelo hasta la rodilla, atleta flexionado.
    for i in range(10):
        frames.append(_frame(i, bar_y=0.95 - 0.025 * i, knee_y=0.70, knee_x=0.70,
                             hip_y=0.65, shoulder_y=0.55))
    # Transición: la cadera se abre hasta la extensión completa.
    for i in range(10, 18):
        frames.append(_frame(i, bar_y=0.70 - 0.02 * (i - 10), knee_y=0.75,
                             knee_x=0.70 - 0.025 * (i - 10),
                             hip_y=0.60, shoulder_y=0.55 - 0.03 * (i - 10)))
    # Segunda tirada: la barra sigue subiendo hasta su máximo.
    for i in range(18, 26):
        frames.append(_frame(i, bar_y=0.54 - 0.04 * (i - 18), knee_y=0.80, knee_x=0.55,
                             hip_y=0.60, shoulder_y=0.40))
    # Recepción: el atleta baja bajo la barra.
    for i in range(26, 34):
        frames.append(_frame(i, bar_y=0.25, knee_y=0.70, knee_x=0.68,
                             hip_y=0.60 + 0.02 * (i - 26), shoulder_y=0.45))
    # Recuperación: se incorpora.
    for i in range(34, 42):
        frames.append(_frame(i, bar_y=0.20, knee_y=0.80, knee_x=0.55,
                             hip_y=0.74 - 0.02 * (i - 34), shoulder_y=0.35))

    return frames


def test_divide_el_levantamiento_en_las_cinco_fases() -> None:
    frames = _snatch_frames()
    window = LiftWindow(start_index=0, end_index=41)

    breakdown = detect_phases(_sequence(frames), window)

    assert len(breakdown) == 5
    assert [span.phase for span in breakdown.spans] == list(LiftPhase)


def test_las_fases_respetan_el_orden_del_movimiento() -> None:
    frames = _snatch_frames()
    window = LiftWindow(start_index=0, end_index=41)

    breakdown = detect_phases(_sequence(frames), window)

    limites = [span.end_index for span in breakdown.spans]
    assert limites == sorted(limites)


def test_las_fases_cubren_toda_la_ventana() -> None:
    frames = _snatch_frames()
    window = LiftWindow(start_index=0, end_index=41)

    breakdown = detect_phases(_sequence(frames), window)

    assert breakdown.spans[0].start_index == 0
    assert breakdown.spans[-1].end_index == 41


def test_una_secuencia_sin_poses_produce_fases_degeneradas_pero_validas() -> None:
    frames = [_frame(i, detected=False) for i in range(20)]
    window = LiftWindow(start_index=0, end_index=19)

    breakdown = detect_phases(_sequence(frames), window)

    assert len(breakdown) == 5
    for span in breakdown.spans:
        assert span.end_index >= span.start_index


def test_el_fin_del_tiron_es_el_primer_maximo_local() -> None:
    """La barra sube, baja en la recepción y vuelve a subir al incorporarse."""
    alturas = [0.9, 0.7, 0.5, 0.3, 0.35, 0.45, 0.35, 0.2, 0.1]
    frames = [_frame(i, bar_y=y) for i, y in enumerate(alturas)]

    assert find_bar_peak(_sequence(frames), after_index=-1) == 3


def test_una_oscilacion_minima_no_cierra_la_segunda_tirada() -> None:
    alturas = [0.9, 0.6, 0.30, 0.305, 0.28, 0.1]
    frames = [_frame(i, bar_y=y) for i, y in enumerate(alturas)]

    assert find_bar_peak(_sequence(frames), after_index=-1) == 5


def test_sin_descenso_devuelve_el_punto_mas_alto() -> None:
    alturas = [0.9, 0.7, 0.5, 0.3, 0.1]
    frames = [_frame(i, bar_y=y) for i, y in enumerate(alturas)]

    assert find_bar_peak(_sequence(frames), after_index=-1) == 4