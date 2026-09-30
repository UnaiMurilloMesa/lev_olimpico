"""Pruebas de la trayectoria de la barra."""

import pytest

from app.domain.bar_path import (
    BarPath,
    BarPoint,
    PathQuality,
    bar_position,
    extract_bar_path,
)
from app.domain.landmarks import Landmark, PoseFrame, PoseLandmarkId
from app.domain.sequence import PoseSequence


def _frame(index: int, left_x: float, right_x: float, y: float) -> PoseFrame:
    landmarks = [Landmark(0.5, 0.5, 0.0, 1.0) for _ in range(33)]
    landmarks[PoseLandmarkId.LEFT_WRIST] = Landmark(left_x, y, 0.0, 1.0)
    landmarks[PoseLandmarkId.RIGHT_WRIST] = Landmark(right_x, y, 0.0, 1.0)
    return PoseFrame(index=index, timestamp_ms=index * 33, landmarks=tuple(landmarks))


def _path(*coords: tuple[float, float]) -> BarPath:
    return BarPath(
        points=tuple(BarPoint(frame_index=index, x=x, y=y) for index, (x, y) in enumerate(coords))
    )


def test_la_barra_se_situa_entre_ambas_munecas() -> None:
    posicion = bar_position(_frame(0, left_x=0.4, right_x=0.6, y=0.5))

    assert posicion is not None
    assert posicion.x == pytest.approx(0.5)
    assert posicion.y == pytest.approx(0.5)


def test_un_fotograma_sin_pose_no_aporta_posicion() -> None:
    assert bar_position(PoseFrame(index=0, timestamp_ms=0, landmarks=())) is None


def test_extrae_la_trayectoria_omitiendo_los_fotogramas_sin_pose() -> None:
    secuencia = PoseSequence(
        frames=(
            _frame(0, 0.4, 0.6, 0.9),
            PoseFrame(index=1, timestamp_ms=33, landmarks=()),
            _frame(2, 0.4, 0.6, 0.5),
        ),
        fps=30.0,
    )

    trayectoria = extract_bar_path(secuencia)

    assert len(trayectoria) == 2
    assert [punto.frame_index for punto in trayectoria.points] == [0, 2]


def test_calcula_el_recorrido_vertical() -> None:
    trayectoria = _path((0.5, 0.9), (0.5, 0.6), (0.5, 0.3))

    assert trayectoria.vertical_range == pytest.approx(0.6)


def test_una_trayectoria_perfectamente_vertical_no_tiene_desviacion() -> None:
    trayectoria = _path((0.5, 0.9), (0.5, 0.6), (0.5, 0.3))

    assert trayectoria.horizontal_deviation == pytest.approx(0.0)
    assert trayectoria.quality is PathQuality.EXCELLENT


def test_una_desviacion_pequena_se_considera_excelente() -> None:
    trayectoria = _path((0.50, 0.9), (0.53, 0.6), (0.50, 0.3))

    assert trayectoria.deviation_ratio == pytest.approx(0.05)
    assert trayectoria.quality is PathQuality.EXCELLENT


def test_una_desviacion_moderada_se_considera_aceptable() -> None:
    trayectoria = _path((0.50, 0.9), (0.65, 0.6), (0.50, 0.3))

    assert trayectoria.quality is PathQuality.ACCEPTABLE


def test_una_desviacion_grande_se_considera_deficiente() -> None:
    trayectoria = _path((0.50, 0.9), (0.85, 0.6), (0.50, 0.3))

    assert trayectoria.quality is PathQuality.POOR


def test_la_desviacion_es_independiente_de_la_escala() -> None:
    """Dos levantamientos iguales grabados a distinta distancia deben puntuar igual."""
    cercano = _path((0.40, 0.90), (0.48, 0.50), (0.40, 0.10))
    lejano = _path((0.45, 0.70), (0.49, 0.50), (0.45, 0.30))

    assert cercano.deviation_ratio == pytest.approx(lejano.deviation_ratio)


def test_una_trayectoria_vacia_no_divide_entre_cero() -> None:
    vacia = BarPath(points=())

    assert vacia.deviation_ratio == 0.0
    assert vacia.vertical_range == 0.0


@pytest.mark.parametrize(
    ("ratio", "esperado"),
    [
        (0.0, PathQuality.EXCELLENT),
        (0.20, PathQuality.EXCELLENT),
        (0.21, PathQuality.ACCEPTABLE),
        (0.30, PathQuality.ACCEPTABLE),
        (0.31, PathQuality.POOR),
        (1.0, PathQuality.POOR),
    ],
)
def test_clasifica_la_calidad_en_los_bordes_de_los_umbrales(
    ratio: float, esperado: PathQuality
) -> None:
    assert PathQuality.from_deviation(ratio) is esperado
