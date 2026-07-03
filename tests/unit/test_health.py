"""Unit tests for liveness health endpoint."""

from fastapi.testclient import TestClient

from app.main import create_app


def test_health_returns_200(minimal_env) -> None:
    client = TestClient(create_app())

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
