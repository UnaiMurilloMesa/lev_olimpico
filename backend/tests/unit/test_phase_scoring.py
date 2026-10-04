"""Pruebas de la puntuación por fases."""

import pytest

from app.domain.landmarks import Landmark, PoseFrame, PoseLandmarkId
from app.domain.lift_window import LiftWindow
from app.domain.phases import LiftPhase, build_breakdown
from app.domain.scoring import ScoreLevel, ScoreScale
from app.domain.sequence import PoseSequence
from app.services.analysis.phase_scoring import ScoringConfig, score_lift
from app.services.analysis.velocity import BarVelocity, VelocitySample

FPS = 30.0
WINDOW = LiftWindow(start_index=0, end_index=49)
BOUNDARIES = (9, 19, 29, 39)


def _frame(
    index: int,
    bar_x: float = 0.5,
    bar_y: float = 0.5,
    hip_y: float = 0.6,
    knee_x: float = 0.6,
    knee_y: float = 0.75,
    shoulder_y: float = 0.4,
) -> PoseFrame:
    points = [Landmark(0.5, 0.5, 0.0, 1.0) for _ in range(33)]
    for wrist in (PoseLandmarkId.LEFT_WRIST, PoseLandmarkId.RIGHT_WRIST):
        points[wrist] = Landmark(bar_x, bar_y, 0.0, 1.0)
    for hip in (PoseLandmarkId.LEFT_HIP, PoseLandmarkId.RIGHT_HIP):
        points[hip] = Landmark(0.5, hip_y, 0.0, 1.0)
    for knee in (PoseLandmarkId.LEFT_KNEE, PoseLandmarkId.RIGHT_KNEE):
        points[knee] = Landmark(knee_x, knee_y, 0.0, 1.0)
    for shoulder in (PoseLandmarkId.LEFT_SHOULDER, PoseLandmarkId.RIGHT_SHOULDER):
        points[shoulder] = Landmark(0.5, shoulder_y, 0.0, 1.0)
    return PoseFrame(index=index, timestamp_ms=int(index * 1000 / FPS),
                     landmarks=tuple(points))


def _lift(frames: list[PoseFrame] | None = None) -> PoseSequence:
    if frames is None:
        frames = [_frame(i, bar_y=0.9 - 0.016 * i) for i in range(50)]
    return PoseSequence(frames=tuple(frames), fps=FPS)


def _velocity(values: dict[int, float] | None = None) -> BarVelocity:
    """Serie de velocidad con los valores indicados por fotograma."""
    base = values or {}
    samples = tuple(
        VelocitySample(
            frame_index=index,
            time_seconds=index / FPS,
            velocity_ms=base.get(index, 0.5),
        )
        for index in range(50)
    )
    return BarVelocity(samples=samples, edge_margin=3)


def _score(lift: PoseSequence, velocity: BarVelocity) -> object:
    return score_lift(lift, build_breakdown(WINDOW, BOUNDARIES), velocity)


# --- Estructura ---


def test_puntua_las_cinco_fases() -> None:
    resultado = _score(_lift(), _velocity())

    assert len(resultado.phases) == 5
    assert [fase.phase for fase in resultado.phases] == [p.value for p in LiftPhase]


def test_la_nota_global_esta_en_el_rango_valido() -> None:
    resultado = _score(_lift(), _velocity())

    assert 0.0 <= resultado.overall <= 10.0


def test_cada_criterio_lleva_su_explicacion() -> None:
    resultado = _score(_lift(), _velocity())

    for fase in resultado.phases:
        for criterio in fase.criteria:
            assert criterio.explanation
            assert criterio.criterion


# --- Primera tirada ---


def test_una_barra_vertical_puntua_alto_en_la_primera_tirada() -> None:
    frames = [_frame(i, bar_x=0.5, bar_y=0.9 - 0.016 * i) for i in range(50)]

    resultado = _score(_lift(frames), _velocity())
    primera = resultado.phases[0]

    assert primera.level is ScoreLevel.GOOD


def test_una_barra_desviada_penaliza_la_primera_tirada() -> None:
    frames = [
        _frame(i, bar_x=0.5 + 0.02 * min(i, 9), bar_y=0.9 - 0.016 * i) for i in range(50)
    ]

    resultado = _score(_lift(frames), _velocity())

    assert resultado.phases[0].score < 7.0


# --- Transición ---


def test_una_velocidad_continua_puntua_alto_en_la_transicion() -> None:
    resultado = _score(_lift(), _velocity({i: 1.0 for i in range(10, 20)}))

    assert resultado.phases[1].level is ScoreLevel.GOOD


def test_un_frenazo_penaliza_la_transicion() -> None:
    frenazo = {10: 1.2, 11: 1.0, 12: 0.5, 13: 0.2, 14: 0.6, 15: 1.0}

    resultado = _score(_lift(), _velocity(frenazo))

    assert resultado.phases[1].score < 7.0


# --- Segunda tirada ---


def test_la_segunda_tirada_puntua_velocidad_y_extension() -> None:
    resultado = _score(_lift(), _velocity())

    criterios = {c.criterion for c in resultado.phases[2].criteria}
    assert criterios == {"velocidad", "extension"}


def test_una_velocidad_alta_mejora_la_segunda_tirada() -> None:
    lenta = _score(_lift(), _velocity({i: 1.0 for i in range(20, 30)}))
    rapida = _score(_lift(), _velocity({i: 1.9 for i in range(20, 30)}))

    assert rapida.phases[2].score > lenta.phases[2].score


# --- Recepción ---


def test_una_recepcion_rapida_puntua_alto() -> None:
    rapida = build_breakdown(WINDOW, (9, 19, 29, 37))   # 8 fotogramas ≈ 0.27 s
    lenta = build_breakdown(WINDOW, (9, 19, 29, 48))    # 19 fotogramas ≈ 0.63 s

    veloz = score_lift(_lift(), rapida, _velocity())
    tardia = score_lift(_lift(), lenta, _velocity())

    assert veloz.phases[3].score > tardia.phases[3].score


# --- Casos límite ---


def test_una_secuencia_sin_pose_no_produce_criterios() -> None:
    vacios = [PoseFrame(index=i, timestamp_ms=i * 33, landmarks=()) for i in range(50)]

    resultado = score_lift(
        PoseSequence(frames=tuple(vacios), fps=FPS),
        build_breakdown(WINDOW, BOUNDARIES),
        BarVelocity(samples=()),
    )

    assert resultado.overall == 0.0
    assert all(not fase.criteria for fase in resultado.phases)


def test_las_escalas_son_configurables() -> None:
    """Los umbrales deben poder recalibrarse sin tocar la lógica."""
    exigente = ScoringConfig(peak_velocity=ScoreScale(best=3.0, worst=2.5))

    resultado = score_lift(
        _lift(), build_breakdown(WINDOW, BOUNDARIES), _velocity(), exigente
    )
    velocidad = next(
        c for c in resultado.phases[2].criteria if c.criterion == "velocidad"
    )

    assert velocidad.score == 0.0


def test_la_nota_global_promedia_las_fases_puntuadas() -> None:
    resultado = _score(_lift(), _velocity())
    puntuadas = [f.score for f in resultado.phases if f.criteria]

    assert resultado.overall == pytest.approx(sum(puntuadas) / len(puntuadas), abs=0.1)


def test_un_criterio_temporal_exige_datos_corporales() -> None:
    """Una fase sin pose no puede puntuar por su duración."""
    vacios = [PoseFrame(index=i, timestamp_ms=i * 33, landmarks=()) for i in range(50)]

    resultado = score_lift(
        PoseSequence(frames=tuple(vacios), fps=FPS),
        build_breakdown(WINDOW, (9, 19, 29, 37)),
        BarVelocity(samples=()),
    )

    assert not resultado.phases[3].criteria