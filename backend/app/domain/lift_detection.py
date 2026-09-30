"""Detección automática del final del levantamiento."""

from __future__ import annotations

from dataclasses import dataclass

from app.domain.bar_path import bar_position
from app.domain.lift_window import LiftWindow
from app.domain.sequence import PoseSequence

DEFAULT_MIN_LIFT_MS = 800
DEFAULT_MAX_LIFT_MS = 8000


@dataclass(frozen=True, slots=True)
class LiftDetectionConfig:
    """Parámetros del detector del final del levantamiento."""

    min_lift_ms: int = DEFAULT_MIN_LIFT_MS
    max_lift_ms: int = DEFAULT_MAX_LIFT_MS


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

        Ante alturas repetidas se devuelve la primera, ya que tras la
        incorporación la barra permanece arriba durante varios fotogramas y
        nos interesa el instante en que llega, no el último en que sigue ahí.
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

    Todo snatch describe la misma curva: la barra sube durante el tirón,
    desciende ligeramente en la recepción y alcanza su punto más alto cuando
    el atleta termina de incorporarse. Ese máximo marca el final del
    levantamiento, así que basta con localizarlo.

    El resultado se acota entre una duración mínima y una máxima, para evitar
    ventanas degeneradas cuando la detección de la barra es pobre.
    """
    config = config or LiftDetectionConfig()
    last_index = sequence.frames[-1].index if sequence.frames else start_index

    floor = min(last_index, start_index + _frames_for(sequence.fps, config.min_lift_ms))
    ceiling = min(last_index, start_index + _frames_for(sequence.fps, config.max_lift_ms))

    peak = bar_heights_from(sequence, start_index).highest_index()
    if peak is None:
        return ceiling

    return min(max(peak, floor), ceiling)


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