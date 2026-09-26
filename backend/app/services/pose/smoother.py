"""Suavizado temporal de las trayectorias de los puntos corporales."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Protocol

import numpy as np
from scipy.signal import savgol_filter

from app.domain.interpolation import DEFAULT_MAX_GAP_MS, interpolate_gaps, max_gap_frames
from app.domain.landmarks import Landmark, LandmarkOrigin, PoseFrame
from app.domain.sequence import PoseSequence

logger = logging.getLogger(__name__)

DEFAULT_WINDOW_MS = 230
DEFAULT_POLYNOMIAL_ORDER = 2
COORDINATE_COUNT = 3


@dataclass(frozen=True, slots=True)
class SmoothingConfig:
    """Parámetros del suavizado temporal."""

    window_ms: int = DEFAULT_WINDOW_MS
    polynomial_order: int = DEFAULT_POLYNOMIAL_ORDER
    max_gap_ms: int = DEFAULT_MAX_GAP_MS


class PoseSmoother(Protocol):
    """Contrato de cualquier suavizador de secuencias de pose."""

    def smooth(self, sequence: PoseSequence) -> PoseSequence:
        """Devuelve una secuencia nueva con las trayectorias suavizadas."""
        ...


class SavitzkyGolaySmoother:
    """Suaviza las trayectorias con un filtro de Savitzky-Golay.

    A diferencia de una media móvil, este filtro ajusta un polinomio local, de
    modo que conserva la amplitud de los picos del movimiento en lugar de
    aplanarlos. Eso importa en halterofilia, donde la extensión explosiva de la
    segunda tirada es justamente un pico.
    """

    def __init__(self, config: SmoothingConfig | None = None) -> None:
        """Crea el suavizador con la configuración indicada."""
        self._config = config or SmoothingConfig()

    def smooth(self, sequence: PoseSequence) -> PoseSequence:
        """Reconstruye los huecos y suaviza cada coordenada de cada punto."""
        if not sequence.frames:
            return sequence

        window = self._effective_window(sequence)
        if window is None:
            logger.warning("Secuencia demasiado corta para suavizar; se devuelve sin cambios.")
            return sequence

        gap_limit = max_gap_frames(sequence.fps, self._config.max_gap_ms)
        landmark_count = self._landmark_count(sequence)
        if landmark_count == 0:
            return sequence

        tracks = [
            self._smooth_landmark(sequence, landmark_index, window, gap_limit)
            for landmark_index in range(landmark_count)
        ]
        return sequence.replacing_frames(self._rebuild_frames(sequence, tracks))

    def _smooth_landmark(
        self,
        sequence: PoseSequence,
        landmark_index: int,
        window: int,
        gap_limit: int,
    ) -> list[tuple[float, float, float] | None]:
        """Suaviza las tres coordenadas de un punto a lo largo del vídeo."""
        raw = [
            (frame.landmarks[landmark_index].x,
             frame.landmarks[landmark_index].y,
             frame.landmarks[landmark_index].z)
            if frame.is_detected
            else None
            for frame in sequence.frames
        ]

        axes: list[list[float | None]] = []
        for axis in range(COORDINATE_COUNT):
            values = [point[axis] if point is not None else None for point in raw]
            filled = interpolate_gaps(values, max_gap=gap_limit)
            axes.append(self._apply_filter(filled.values, window))

        smoothed: list[tuple[float, float, float] | None] = []
        for index in range(len(sequence.frames)):
            x, y, z = axes[0][index], axes[1][index], axes[2][index]
            if x is None or y is None or z is None:
                smoothed.append(None)
            else:
                smoothed.append((x, y, z))
        return smoothed

    def _apply_filter(
        self, values: tuple[float | None, ...], window: int
    ) -> list[float | None]:
        """Aplica el filtro a los tramos continuos de la señal.

        Los valores ausentes se conservan como tales: solo se filtran los
        segmentos de datos conocidos, cada uno de forma independiente.
        """
        result: list[float | None] = list(values)
        for start, end in _continuous_segments(values):
            length = end - start
            if length < window:
                continue
            segment = np.array(values[start:end], dtype=float)
            filtered = savgol_filter(
                segment,
                window_length=window,
                polyorder=self._config.polynomial_order,
                mode="interp",
            )
            result[start:end] = [float(value) for value in filtered]
        return result

    def _effective_window(self, sequence: PoseSequence) -> int | None:
        """Calcula la ventana en fotogramas, o None si la secuencia es corta."""
        window = sequence.window_size_for(self._config.window_ms)
        if window > len(sequence):
            window = len(sequence) if len(sequence) % 2 == 1 else len(sequence) - 1
        if window <= self._config.polynomial_order:
            return None
        return window

    @staticmethod
    def _landmark_count(sequence: PoseSequence) -> int:
        """Número de puntos por fotograma, tomado del primer fotograma detectado."""
        for frame in sequence.frames:
            if frame.is_detected:
                return len(frame.landmarks)
        return 0

    @staticmethod
    def _rebuild_frames(
        sequence: PoseSequence,
        tracks: list[list[tuple[float, float, float] | None]],
    ) -> tuple[PoseFrame, ...]:
        """Reconstruye los fotogramas con las coordenadas ya suavizadas."""
        rebuilt: list[PoseFrame] = []

        for index, frame in enumerate(sequence.frames):
            positions = [track[index] for track in tracks]
            if all(position is None for position in positions):
                rebuilt.append(
                    PoseFrame(index=frame.index, timestamp_ms=frame.timestamp_ms, landmarks=())
                )
                continue

            landmarks = tuple(
                _rebuild_landmark(frame, landmark_index, position)
                for landmark_index, position in enumerate(positions)
            )
            rebuilt.append(
                PoseFrame(
                    index=frame.index, timestamp_ms=frame.timestamp_ms, landmarks=landmarks
                )
            )

        return tuple(rebuilt)


def _rebuild_landmark(
    frame: PoseFrame, landmark_index: int, position: tuple[float, float, float] | None
) -> Landmark:
    """Crea el punto suavizado, marcándolo como interpolado si procede."""
    if position is None:
        return Landmark(x=0.0, y=0.0, z=0.0, visibility=0.0,
                        origin=LandmarkOrigin.INTERPOLATED)

    if frame.is_detected:
        return frame.landmarks[landmark_index].moved_to(*position)

    return Landmark(
        x=position[0], y=position[1], z=position[2],
        visibility=0.0, origin=LandmarkOrigin.INTERPOLATED,
    )


def _continuous_segments(values: tuple[float | None, ...]) -> list[tuple[int, int]]:
    """Localiza los tramos de valores conocidos como pares [inicio, fin)."""
    segments: list[tuple[int, int]] = []
    start: int | None = None

    for index, value in enumerate(values):
        if value is not None and start is None:
            start = index
        elif value is None and start is not None:
            segments.append((start, index))
            start = None

    if start is not None:
        segments.append((start, len(values)))
    return segments