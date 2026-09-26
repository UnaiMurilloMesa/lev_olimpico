"""Pruebas de la reconstrucción de huecos en señales temporales."""

import pytest

from app.domain.interpolation import interpolate_gaps, max_gap_frames


def test_una_senal_completa_no_se_modifica() -> None:
    resultado = interpolate_gaps([1.0, 2.0, 3.0], max_gap=5)

    assert resultado.values == (1.0, 2.0, 3.0)
    assert resultado.filled_count == 0


def test_rellena_un_hueco_de_un_fotograma() -> None:
    resultado = interpolate_gaps([0.0, None, 2.0], max_gap=5)

    assert resultado.values == (0.0, 1.0, 2.0)
    assert resultado.interpolated == (False, True, False)


def test_rellena_un_hueco_de_varios_fotogramas_de_forma_lineal() -> None:
    resultado = interpolate_gaps([0.0, None, None, None, 4.0], max_gap=5)

    assert resultado.values == (0.0, 1.0, 2.0, 3.0, 4.0)
    assert resultado.filled_count == 3


def test_no_rellena_un_hueco_demasiado_largo() -> None:
    resultado = interpolate_gaps([0.0, None, None, None, 4.0], max_gap=2)

    assert resultado.values == (0.0, None, None, None, 4.0)
    assert resultado.filled_count == 0


def test_rellena_un_hueco_del_tamano_limite() -> None:
    resultado = interpolate_gaps([0.0, None, None, 3.0], max_gap=2)

    assert resultado.filled_count == 2


def test_no_extrapola_al_principio_de_la_senal() -> None:
    resultado = interpolate_gaps([None, None, 2.0, 3.0], max_gap=5)

    assert resultado.values[:2] == (None, None)


def test_no_extrapola_al_final_de_la_senal() -> None:
    resultado = interpolate_gaps([0.0, 1.0, None, None], max_gap=5)

    assert resultado.values[2:] == (None, None)


def test_rellena_varios_huecos_independientes() -> None:
    resultado = interpolate_gaps([0.0, None, 2.0, None, 4.0], max_gap=1)

    assert resultado.values == (0.0, 1.0, 2.0, 3.0, 4.0)
    assert resultado.filled_count == 2


def test_una_senal_sin_ningun_valor_conocido_queda_igual() -> None:
    resultado = interpolate_gaps([None, None, None], max_gap=5)

    assert resultado.filled_count == 0


def test_una_senal_vacia_no_falla() -> None:
    assert interpolate_gaps([], max_gap=5).values == ()


@pytest.mark.parametrize(
    ("fps", "milisegundos", "esperado"),
    [(30.0, 400, 12), (60.0, 400, 24), (30.0, 100, 3)],
)
def test_traduce_la_duracion_maxima_de_hueco_a_fotogramas(
    fps: float, milisegundos: int, esperado: int
) -> None:
    assert max_gap_frames(fps, milisegundos) == esperado