"""Pruebas de integración del endpoint de salud."""

from fastapi.testclient import TestClient


def test_health_devuelve_estado_ok(client: TestClient) -> None:
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_health_expone_la_version(client: TestClient) -> None:
    response = client.get("/api/v1/health")

    assert response.json()["version"] == "0.1.0"


def test_health_informa_de_la_disponibilidad_del_modelo(client: TestClient) -> None:
    response = client.get("/api/v1/health")

    assert isinstance(response.json()["pose_model_available"], bool)
