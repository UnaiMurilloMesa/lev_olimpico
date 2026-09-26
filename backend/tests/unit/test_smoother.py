"""Pruebas del suavizado de trayectorias."""

import numpy as np
import pytest

from app.domain.landmarks import Landmark, PoseFrame, PoseLandmarkId
from app.domain.sequence import PoseSequence
from app.services.pose.smoother import SavitzkyGolaySmoother, SmoothingConfig

LANDMARKS = 33
FPS = 30.0


def _frame(index: int, x: float, detected: bool = True) -> PoseFrame:
    landmarks = (
        tuple(Landmark(x=x, y=0.5, z=0.0, visibility=0.9) for _ in range(LANDMARKS))
        if detected
        else ()
    )
    return PoseFrame(index=index, timestamp_ms=int(index * 1000 / FPS), landmarks=landmarks)


def _sequence_from(xs: list[float | None]) -> PoseSequence:
    frames = tuple(
        _frame(index, x if x is not None else 0.0, detected=x is not None)
        for index, x in enumerate(xs)
    )
    return PoseSequence(frames=frames, fps=FPS)


def _xs(sequence: PoseSequence) -> list[float | None]:
    return [
        frame.landmarks[PoseLandmarkId.NOSE].x if frame.is_detected else None
        for frame in sequence.frames
    ]


def test_conserva_una_rampa_lineal() -> None:
    """Un polinomio de grado <= al del filtro debe salir intacto."""
    original = [index * 0.01 for index in range(20)]

    suavizada = _xs(SavitzkyGolaySmoother().smooth(_sequence_from(original)))

    assert suavizada == pytest.approx(original, abs=1e-9)


def test_reduce_el_ruido_de_una_senal() -> None:
    rng = np.random.default_rng(seed=42)
    limpia = np.linspace(0.2, 0.8, 60)
    ruidosa = limpia + rng.normal(0, 0.01, 60)

    suavizada = _xs(SavitzkyGolaySmoother().smooth(_sequence_from(list(ruidosa))))

    error_original = float(np.abs(ruidosa - limpia).mean())
    error_suavizado = float(np.abs(np.array(suavizada) - limpia).mean())
    assert error_suavizado < error_original


def test_conserva_mejor_la_amplitud_que_una_media_movil() -> None:
    """Sobre un pico real, Savitzky-Golay atenúa menos que promediar."""
    ventana = 7
    base = np.full(40, 0.5)
    pico = np.exp(-0.5 * ((np.arange(40) - 20) / 4.0) ** 2) * 0.3
    valores = base + pico

    suavizada = np.array(_xs(SavitzkyGolaySmoother().smooth(_sequence_from(list(valores)))))
    media_movil = np.convolve(valores, np.ones(ventana) / ventana, mode="same")

    amplitud_original = valores.max() - 0.5
    amplitud_savgol = suavizada.max() - 0.5
    amplitud_media = media_movil.max() - 0.5

    assert amplitud_savgol > amplitud_media
    assert amplitud_savgol > 0.95 * amplitud_original


def test_rellena_los_huecos_cortos_y_los_marca_como_interpolados() -> None:
    valores: list[float | None] = [0.1, 0.2, None, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]

    resultado = SavitzkyGolaySmoother().smooth(_sequence_from(valores))

    assert resultado.frames[2].is_detected is True
    assert resultado.frames[2].landmarks[PoseLandmarkId.NOSE].is_interpolated is True


def test_no_reconstruye_los_huecos_largos() -> None:
    config = SmoothingConfig(max_gap_ms=60)  # ~2 fotogramas a 30 fps
    valores: list[float | None] = [0.1, 0.2] + [None] * 10 + [0.5, 0.6]

    resultado = SavitzkyGolaySmoother(config).smooth(_sequence_from(valores))

    assert resultado.frames[6].is_detected is False


def test_una_secuencia_vacia_se_devuelve_igual() -> None:
    vacia = PoseSequence(frames=(), fps=FPS)

    assert SavitzkyGolaySmoother().smooth(vacia) is vacia


def test_una_secuencia_mas_corta_que_la_ventana_no_falla() -> None:
    corta = _sequence_from([0.1, 0.2, 0.3])

    resultado = SavitzkyGolaySmoother().smooth(corta)

    assert len(resultado) == 3


def test_conserva_los_fps_y_la_longitud() -> None:
    original = _sequence_from([0.1] * 30)

    resultado = SavitzkyGolaySmoother().smooth(original)

    assert resultado.fps == FPS
    assert len(resultado) == 30


def test_no_modifica_la_secuencia_original() -> None:
    original = _sequence_from([index * 0.01 for index in range(20)])
    copia = _xs(original)

    SavitzkyGolaySmoother().smooth(original)

    assert _xs(original) == copia