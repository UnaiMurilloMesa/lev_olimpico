"""Detección de los eventos que separan las fases del levantamiento."""

from __future__ import annotations

from dataclasses import dataclass

from app.domain.angles import JointName, joint_angles
from app.domain.bar_path import bar_position
from app.domain.landmarks import PoseFrame, PoseLandmarkId
from app.domain.lift_window import LiftWindow
from app.domain.phases import PhaseBreakdown, build_breakdown
from app.domain.sequence import PoseSequence


@dataclass(frozen=True, slots=True)
class PhaseDetectionConfig:
    """Parámetros del detector de eventos.

    Attributes:
        knee_tolerance: Margen vertical, en unidades normalizadas, aplicado a la
        altura de la rodilla. Un valor negativo exige que la barra la supere
        antes de dar por terminada la primera tirada.
    """

    knee_tolerance: float = -0.02
    peak_drop: float = 0.015


def knee_height(frame: PoseFrame) -> float | None:
    """Altura media de ambas rodillas, invertida respecto al eje de imagen."""
    if not frame.is_detected:
        return None
    left = frame.landmarks[PoseLandmarkId.LEFT_KNEE].y
    right = frame.landmarks[PoseLandmarkId.RIGHT_KNEE].y
    return 1.0 - (left + right) / 2


def bar_height(frame: PoseFrame) -> float | None:
    """Altura de la barra, invertida respecto al eje de imagen."""
    position = bar_position(frame)
    return None if position is None else 1.0 - position.y


def hip_extension(frame: PoseFrame) -> float | None:
    """Ángulo medio de cadera; 180º corresponde a la extensión completa."""
    angles = joint_angles(frame)
    if not angles:
        return None
    return (angles[JointName.LEFT_HIP] + angles[JointName.RIGHT_HIP]) / 2


def find_knee_pass(lift: PoseSequence, config: PhaseDetectionConfig) -> int | None:
    """Localiza el fotograma en que la barra alcanza la altura de la rodilla.

    Marca el final de la primera tirada: a partir de ahí el atleta reorganiza
    la posición para la segunda tirada.
    """
    for frame in lift.frames:
        bar = bar_height(frame)
        knee = knee_height(frame)
        if bar is None or knee is None:
            continue
        if bar >= knee - config.knee_tolerance:
            return frame.index
    return None


def find_hip_extension(lift: PoseSequence, after_index: int) -> int | None:
    """Localiza la máxima extensión de cadera posterior a un fotograma.

    Marca el final de la transición: el instante del triple extensión, cuando
    el atleta termina de abrir la cadera antes de pasar bajo la barra.
    """
    best_index: int | None = None
    best_angle = float("-inf")

    for frame in lift.frames:
        if frame.index <= after_index:
            continue
        angle = hip_extension(frame)
        if angle is not None and angle > best_angle:
            best_angle = angle
            best_index = frame.index

    return best_index


def find_bar_peak(lift: PoseSequence, after_index: int, drop: float = 0.015) -> int | None:
    """Localiza el fin del impulso de la segunda tirada.

    No se busca la altura máxima absoluta. La barra alcanza su punto más alto
    al final de la recuperación, cuando el atleta ya está erguido. Lo que marca
    el fin de la segunda tirada es el primer máximo local, el instante en que
    la barra deja de subir por el impulso y comienza a descender mientras el
    atleta pasa por debajo.
    """
    best_index: int | None = None
    best_height = float("-inf")

    for frame in lift.frames:
        if frame.index <= after_index:
            continue
        height = bar_height(frame)
        if height is None:
            continue

        if height > best_height:
            best_height = height
            best_index = frame.index
        elif best_index is not None and best_height - height >= drop:
            # La barra ha descendido lo suficiente: el máximo era real y no ruido.
            return best_index

    return best_index


def find_catch(lift: PoseSequence, after_index: int) -> int | None:
    """Localiza el punto más bajo de la recepción posterior a un fotograma.

    Marca el final del turnover: el atleta ha recibido la barra en sentadilla
    y a partir de ahí se incorpora.
    """
    best_index: int | None = None
    lowest = float("inf")

    for frame in lift.frames:
        if frame.index <= after_index:
            continue
        height = hip_height(frame)
        if height is not None and height < lowest:
            lowest = height
            best_index = frame.index

    return best_index


def hip_height(frame: PoseFrame) -> float | None:
    """Altura media de ambas caderas, invertida respecto al eje de imagen."""
    if not frame.is_detected:
        return None
    left = frame.landmarks[PoseLandmarkId.LEFT_HIP].y
    right = frame.landmarks[PoseLandmarkId.RIGHT_HIP].y
    return 1.0 - (left + right) / 2


def detect_phases(
    lift: PoseSequence,
    window: LiftWindow,
    config: PhaseDetectionConfig | None = None,
) -> PhaseBreakdown:
    """Divide el levantamiento en sus cinco fases.

    Cada evento se busca a partir del anterior, lo que impone el orden natural
    del movimiento aunque una señal concreta sea ruidosa. Si un evento no se
    detecta, se usa el límite anterior y la fase resultante queda vacía en vez
    de desplazar al resto.
    """
    config = config or PhaseDetectionConfig()

    knee = find_knee_pass(lift, config) or window.start_index
    extension = find_hip_extension(lift, knee) or knee
    peak = find_bar_peak(lift, extension, config.peak_drop) or extension
    catch = find_catch(lift, peak) or peak

    return build_breakdown(window, (knee, extension, peak, catch))