"""Fixtures compartidas por la suite de pruebas."""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture
def client() -> Iterator[TestClient]:
    """Cliente HTTP contra una instancia aislada de la aplicación."""
    with TestClient(create_app()) as test_client:
        yield test_client