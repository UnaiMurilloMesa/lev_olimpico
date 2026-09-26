"""Detección automática del final del levantamiento."""

from __future__ import annotations

from dataclasses import dataclass

from app.domain.bar_path import bar_position
from app.domain.lift_window import LiftWindow
from app.domain.sequence import PoseSequence

# La barra se considera estabilizada cuando su altura varía menos que este
# margen (en coordenadas normalizadas) durante la ventana de reposo.
DEFAULT_STABILITY_THRESHOLD = 0.012
DEFAULT_STABILITY_MS = 400
DEFAULT_MAX_LIFT_MS = 8000

DEFAULT_DROP_RATIO = 0.15


@dataclass(frozen=True, slots=True)
class LiftDetectionConfig:
    """Parámetros del detector del final del levantamiento."""

    stability_threshold: float = DEFAULT_STABILITY_THRESHOLD
    stability_ms: int = DEFAULT_STABILITY_MS
    max_lift_ms: int = DEFAULT_MAX_LIFT_MS
    drop_ratio: float = DEFAULT_DROP_RATIO


@dataclass(frozen=True, slots=True)
class BarHeights:
    """Alturas de la barra a partir de un fotograma dado.

    La altura se expresa invertida respecto a la coordenada de imagen: valores
    mayores significan barra más alta, lo que resulta más intuitivo que el
    eje `y` de MediaPipe, que crece hacia abajo.
    """

    start_index: int
    values: tuple[float | None, ...]

    def highest_index(self) -> int | None:
        """Índice absoluto del fotograma donde la barra alcanza su máximo.

        Ante alturas repetidas se devuelve la primera, ya que tras la recepción
        la barra permanece en su altura máxima durante varios fotogramas y nos
        interesa el instante en que llega, no el último en que sigue ahí.
        """
        best_offset: int | None = None
        best_value = float("-inf")

        for offset, value in enumerate(self.values):
            if value is not None and value > best_value:
                best_value = value
                best_offset = offset

        return None if best_offset is None else self.start_index + best_offset


def bar_heights_from(sequence: PoseSequence, start_index: int) -> BarHeights:
    """Extrae la altura de la barra desde un fotograma hasta el final."""
    values: list[float | None] = []
    for frame in sequence.frames:
        if frame.index < start_index:
            continue
        position = bar_position(frame)
        values.append(None if position is None else 1.0 - position.y)
    return BarHeights(start_index=start_index, values=tuple(values))


def detect_lift_end(
    sequence: PoseSequence,
    start_index: int,
    config: LiftDetectionConfig | None = None,
) -> int:
    """Estima el fotograma en que termina el levantamiento.

    Se aplican dos criterios y gana el que ocurra antes: que la barra deje de
    variar de altura (el atleta la sostiene arriba) o que descienda de forma
    apreciable desde su máximo (el atleta la suelta). Si no se cumple ninguno,
    se acota por la duración máxima configurada.
    """
    config = config or LiftDetectionConfig()
    heights = bar_heights_from(sequence, start_index)
    last_index = sequence.frames[-1].index if sequence.frames else start_index

    limit = min(last_index, start_index + _frames_for(sequence.fps, config.max_lift_ms))
    peak = heights.highest_index()
    if peak is None:
        return limit

    window = _frames_for(sequence.fps, config.stability_ms)
    candidates = [
        _first_stable_index(heights, peak, window, config.stability_threshold),
        _descent_index(heights, peak, config.drop_ratio),
    ]
    found = [index for index in candidates if index is not None]
    return min(min(found), limit) if found else limit


def _descent_index(heights: BarHeights, peak_index: int, drop_ratio: float) -> int | None:
    """Busca el fotograma en que la barra cae desde su altura máxima."""
    known = [value for value in heights.values if value is not None]
    if not known:
        return None

    peak_height = max(known)
    lift_range = peak_height - known[0]
    if lift_range <= 0:
        return None

    floor = peak_height - drop_ratio * lift_range
    offset = peak_index - heights.start_index

    for position in range(offset + 1, len(heights.values)):
        value = heights.values[position]
        if value is not None and value < floor:
            return heights.start_index + position - 1

    return None


def _first_stable_index(
    heights: BarHeights, peak_index: int, window: int, threshold: float
) -> int | None:
    """Busca el primer tramo estable posterior al máximo de la barra."""
    offset = peak_index - heights.start_index

    for position in range(offset, len(heights.values) - window + 1):
        segment = heights.values[position : position + window]
        known = [value for value in segment if value is not None]
        if len(known) < window:
            continue
        if max(known) - min(known) <= threshold:
            return heights.start_index + position + window - 1

    return None


def _frames_for(fps: float, milliseconds: int) -> int:
    """Traduce una duración en milisegundos a número de fotogramas."""
    return max(1, round(fps * milliseconds / 1000))


def detect_lift_window(
    sequence: PoseSequence,
    start_seconds: float,
    config: LiftDetectionConfig | None = None,
) -> LiftWindow:
    """Construye la ventana del levantamiento desde el inicio indicado."""
    start = LiftWindow.from_seconds(start_seconds, sequence)
    end_index = detect_lift_end(sequence, start.start_index, config)
    return LiftWindow(start_index=start.start_index, end_index=max(end_index, start.start_index))