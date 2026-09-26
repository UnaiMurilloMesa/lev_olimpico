"""Cálculo de la velocidad vertical de la barra."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.signal import savgol_filter

from app.domain.bar_path import bar_position
from app.domain.scale import BodyScale
from app.domain.sequence import PoseSequence
from app.services.pose.smoother import DEFAULT_POLYNOMIAL_ORDER, DEFAULT_WINDOW_MS


@dataclass(frozen=True, slots=True)
class VelocitySample:
    """Velocidad vertical de la barra en un instante."""

    frame_index: int
    time_seconds: float
    velocity_ms: float


@dataclass(frozen=True, slots=True)
class BarVelocity:
    """Serie temporal de velocidad vertical de la barra.

    Los valores positivos corresponden a la barra subiendo.
    """

    samples: tuple[VelocitySample, ...]

    def __len__(self) -> int:
        """Número de muestras de la serie."""
        return len(self.samples)

    @property
    def peak(self) -> VelocitySample | None:
        """Muestra de velocidad ascendente máxima."""
        if not self.samples:
            return None
        return max(self.samples, key=lambda sample: sample.velocity_ms)

    @property
    def peak_velocity_ms(self) -> float:
        """Velocidad ascendente máxima alcanzada, en m/s."""
        peak = self.peak
        return peak.velocity_ms if peak else 0.0

    @property
    def peak_time_seconds(self) -> float:
        """Instante en que se alcanza la velocidad máxima."""
        peak = self.peak
        return peak.time_seconds if peak else 0.0

    def as_series(self) -> tuple[list[float], list[float]]:
        """Devuelve la serie como dos listas paralelas de tiempo y velocidad."""
        return (
            [sample.time_seconds for sample in self.samples],
            [sample.velocity_ms for sample in self.samples],
        )


def compute_bar_velocity(
    sequence: PoseSequence,
    scale: BodyScale,
    window_ms: int = DEFAULT_WINDOW_MS,
    polynomial_order: int = DEFAULT_POLYNOMIAL_ORDER,
) -> BarVelocity:
    """Calcula la velocidad vertical de la barra a lo largo de la secuencia.

    La derivada se obtiene del propio filtro de Savitzky-Golay, que ajusta un
    polinomio local y lo deriva analíticamente. Esto evita amplificar el ruido,
    que es lo que ocurre al derivar por diferencias finitas.
    """
    positions = [
        (frame.index, bar_position(frame))
        for frame in sequence.frames
    ]
    known = [(index, point) for index, point in positions if point is not None]
    if len(known) < 3:
        return BarVelocity(samples=())

    # El eje y de la imagen crece hacia abajo: se invierte para que subir sea
    # velocidad positiva.
    heights = np.array([1.0 - point.y for _, point in known], dtype=float)
    window = _odd_window(sequence.fps, window_ms, len(heights), polynomial_order)

    if window is None:
        derivative = np.gradient(heights) * sequence.fps
    else:
        derivative = savgol_filter(
            heights,
            window_length=window,
            polyorder=polynomial_order,
            deriv=1,
            delta=1.0 / sequence.fps,
            mode="interp",
        )

    first_index = known[0][0]
    samples = tuple(
        VelocitySample(
            frame_index=index,
            time_seconds=(index - first_index) / sequence.fps,
            velocity_ms=scale.to_meters(float(value)),
        )
        for (index, _), value in zip(known, derivative, strict=True)
    )
    return BarVelocity(samples=samples)


def _odd_window(
    fps: float, window_ms: int, length: int, polynomial_order: int
) -> int | None:
    """Calcula una ventana impar válida, o None si la serie es demasiado corta."""
    window = max(3, round(fps * window_ms / 1000))
    if window % 2 == 0:
        window += 1
    if window > length:
        window = length if length % 2 == 1 else length - 1
    return window if window > polynomial_order else None