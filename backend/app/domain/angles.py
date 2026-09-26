"""Cálculo de ángulos articulares a partir de los puntos corporales."""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import StrEnum

from app.domain.landmarks import Landmark, PoseFrame, PoseLandmarkId


class JointName(StrEnum):
    """Articulaciones cuyo ángulo se monitoriza."""

    LEFT_ELBOW = "left_elbow"
    RIGHT_ELBOW = "right_elbow"
    LEFT_SHOULDER = "left_shoulder"
    RIGHT_SHOULDER = "right_shoulder"
    LEFT_HIP = "left_hip"
    RIGHT_HIP = "right_hip"
    LEFT_KNEE = "left_knee"
    RIGHT_KNEE = "right_knee"
    LEFT_ANKLE = "left_ankle"
    RIGHT_ANKLE = "right_ankle"


@dataclass(frozen=True, slots=True)
class JointDefinition:
    """Tripleta de puntos que define el ángulo de una articulación.

    El ángulo se mide en `vertex`, entre los segmentos que lo unen a `first`
    y a `second`.
    """

    first: PoseLandmarkId
    vertex: PoseLandmarkId
    second: PoseLandmarkId


JOINT_DEFINITIONS: dict[JointName, JointDefinition] = {
    JointName.LEFT_ELBOW: JointDefinition(
        PoseLandmarkId.LEFT_SHOULDER, PoseLandmarkId.LEFT_ELBOW, PoseLandmarkId.LEFT_WRIST
    ),
    JointName.RIGHT_ELBOW: JointDefinition(
        PoseLandmarkId.RIGHT_SHOULDER, PoseLandmarkId.RIGHT_ELBOW, PoseLandmarkId.RIGHT_WRIST
    ),
    JointName.LEFT_SHOULDER: JointDefinition(
        PoseLandmarkId.LEFT_ELBOW, PoseLandmarkId.LEFT_SHOULDER, PoseLandmarkId.LEFT_HIP
    ),
    JointName.RIGHT_SHOULDER: JointDefinition(
        PoseLandmarkId.RIGHT_ELBOW, PoseLandmarkId.RIGHT_SHOULDER, PoseLandmarkId.RIGHT_HIP
    ),
    JointName.LEFT_HIP: JointDefinition(
        PoseLandmarkId.LEFT_SHOULDER, PoseLandmarkId.LEFT_HIP, PoseLandmarkId.LEFT_KNEE
    ),
    JointName.RIGHT_HIP: JointDefinition(
        PoseLandmarkId.RIGHT_SHOULDER, PoseLandmarkId.RIGHT_HIP, PoseLandmarkId.RIGHT_KNEE
    ),
    JointName.LEFT_KNEE: JointDefinition(
        PoseLandmarkId.LEFT_HIP, PoseLandmarkId.LEFT_KNEE, PoseLandmarkId.LEFT_ANKLE
    ),
    JointName.RIGHT_KNEE: JointDefinition(
        PoseLandmarkId.RIGHT_HIP, PoseLandmarkId.RIGHT_KNEE, PoseLandmarkId.RIGHT_ANKLE
    ),
    JointName.LEFT_ANKLE: JointDefinition(
        PoseLandmarkId.LEFT_KNEE, PoseLandmarkId.LEFT_ANKLE, PoseLandmarkId.LEFT_FOOT_INDEX
    ),
    JointName.RIGHT_ANKLE: JointDefinition(
        PoseLandmarkId.RIGHT_KNEE, PoseLandmarkId.RIGHT_ANKLE, PoseLandmarkId.RIGHT_FOOT_INDEX
    ),
}


def angle_between(first: Landmark, vertex: Landmark, second: Landmark) -> float:
    """Devuelve el ángulo en grados que forman tres puntos, medido en el vértice.

    El cálculo se hace en el plano de la imagen (x, y). La coordenada z de
    MediaPipe es una estimación relativa poco fiable para medir ángulos, y el
    estándar de grabación a 45º ya fija la perspectiva.
    """
    ax, ay = first.x - vertex.x, first.y - vertex.y
    bx, by = second.x - vertex.x, second.y - vertex.y

    magnitude = math.hypot(ax, ay) * math.hypot(bx, by)
    if magnitude == 0:
        return 0.0

    cosine = (ax * bx + ay * by) / magnitude
    return math.degrees(math.acos(max(-1.0, min(1.0, cosine))))


def joint_angles(frame: PoseFrame) -> dict[JointName, float]:
    """Calcula todos los ángulos articulares de un fotograma.

    Devuelve un diccionario vacío si el fotograma no tiene pose detectada.
    """
    if not frame.is_detected:
        return {}

    return {
        name: angle_between(
            frame.landmarks[definition.first],
            frame.landmarks[definition.vertex],
            frame.landmarks[definition.second],
        )
        for name, definition in JOINT_DEFINITIONS.items()
    }