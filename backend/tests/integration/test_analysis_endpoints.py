"""Pruebas de integración de los endpoints de análisis."""

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_job_registry
from app.core.config import Settings, get_settings
from app.domain.job import JobStatus
from app.main import create_app
from app.services.job_registry import JobState


class FakeRegistry:
    """Registro de trabajos controlado desde el test."""

    def __init__(self, state: JobState) -> None:
        self._state = state

    def get_state(self, job_id: str) -> JobState:
        return self._state


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(storage_dir=tmp_path / "storage", models_dir=tmp_path / "models")


@pytest.fixture
def client(settings: Settings, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    """Cliente con la cola simulada y almacenamiento temporal."""
    enqueued: list[str] = []

    def fake_apply_async(*args: Any, **kwargs: Any) -> None:
        enqueued.append(kwargs.get("task_id", ""))

    monkeypatch.setattr("app.api.v1.endpoints.analysis.analyze_lift.apply_async", fake_apply_async)

    app = create_app(settings)
    app.dependency_overrides[get_settings] = lambda: settings

    with TestClient(app) as test_client:
        test_client.enqueued = enqueued  # type: ignore[attr-defined]
        yield test_client


def _resumen(**overrides: object) -> dict[str, object]:
    """Resumen de análisis completo, con los campos que se quieran sobrescribir."""
    base = {
        "job_id": "abc",
        "video_name": "analysis.mp4",
        "processed_frames": 120,
        "detected_frames": 118,
        "detection_ratio": 0.9833,
        "duration_seconds": 4.0,
        "bar_path_deviation": 0.12,
        "bar_path_quality": "acceptable",
        "lift_start_seconds": 1.5,
        "lift_end_seconds": 4.2,
        "lift_duration_seconds": 2.7,
        "peak_velocity_ms": 1.82,
        "peak_velocity_time": 0.65,
        "has_velocity_chart": True,
        "interpolated_frames": 2,
    }
    return base | overrides


def _upload(client: TestClient, filename: str = "snatch.mp4", content: bytes = b"x" * 2048):
    return client.post(
        "/api/v1/analyses",
        files={"video": (filename, content, "video/mp4")},
        data={"lift_type": "snatch"},
    )


def test_encolar_un_video_devuelve_202_con_identificador(client: TestClient) -> None:
    response = _upload(client)

    assert response.status_code == 202
    assert response.json()["status"] == "pending"
    assert len(response.json()["job_id"]) == 36


def test_el_video_se_guarda_en_el_espacio_del_trabajo(
    client: TestClient, settings: Settings
) -> None:
    job_id = _upload(client).json()["job_id"]

    assert (settings.storage_dir / job_id / "source.mp4").is_file()


def test_el_trabajo_se_encola_con_su_identificador(client: TestClient) -> None:
    job_id = _upload(client).json()["job_id"]

    assert client.enqueued == [job_id]  # type: ignore[attr-defined]


def test_rechaza_una_extension_no_admitida(client: TestClient) -> None:
    response = _upload(client, filename="documento.pdf")

    assert response.status_code == 422


def test_consultar_un_trabajo_en_proceso(client: TestClient) -> None:
    client.app.dependency_overrides[get_job_registry] = lambda: FakeRegistry(
        JobState(JobStatus.PROCESSING)
    )

    response = client.get("/api/v1/analyses/abc")

    assert response.json()["status"] == "processing"
    assert response.json()["result"] is None


def test_consultar_un_trabajo_completado_devuelve_el_resumen(client: TestClient) -> None:
    client.app.dependency_overrides[get_job_registry] = lambda: FakeRegistry(
        JobState(JobStatus.COMPLETED, result=_resumen())
    )

    response = client.get("/api/v1/analyses/abc")

    assert response.json()["status"] == "completed"
    assert response.json()["result"]["processed_frames"] == 120


def test_descargar_un_video_inexistente_devuelve_404(client: TestClient) -> None:
    assert client.get("/api/v1/analyses/desconocido/video").status_code == 404


def test_descargar_el_video_de_un_trabajo_completado(
    client: TestClient, settings: Settings
) -> None:
    job_id = "trabajo-listo"
    carpeta = settings.storage_dir / job_id
    carpeta.mkdir(parents=True)
    (carpeta / "analysis.mp4").write_bytes(b"contenido-video")

    response = client.get(f"/api/v1/analyses/{job_id}/video")

    assert response.status_code == 200
    assert response.headers["content-type"] == "video/mp4"


def test_eliminar_un_analisis_borra_su_espacio_de_trabajo(
    client: TestClient, settings: Settings
) -> None:
    job_id = _upload(client).json()["job_id"]

    response = client.delete(f"/api/v1/analyses/{job_id}")

    assert response.status_code == 204
    assert not (settings.storage_dir / job_id).exists()


def test_acepta_el_instante_de_inicio(client: TestClient) -> None:
    response = client.post(
        "/api/v1/analyses",
        files={"video": ("snatch.mp4", b"x" * 2048, "video/mp4")},
        data={"lift_type": "snatch", "start_seconds": "1.5"},
    )

    assert response.status_code == 202
