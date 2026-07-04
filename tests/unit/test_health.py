"""Unit tests for liveness and readiness health endpoints."""

from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import create_app


def test_health_returns_200(minimal_env) -> None:
    client = TestClient(create_app())

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_ready_returns_200_when_dependencies_healthy(
    minimal_env,
) -> None:
    client = TestClient(create_app())

    with (
        patch(
            "app.infrastructure.health_checks.check_database",
            return_value=True,
        ),
        patch(
            "app.infrastructure.health_checks.check_redis",
            return_value=True,
        ),
    ):
        response = client.get("/health/ready")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "database": "ok",
        "redis": "ok",
    }


def test_health_ready_returns_503_when_database_unreachable(
    minimal_env,
) -> None:
    client = TestClient(create_app())

    with (
        patch(
            "app.infrastructure.health_checks.check_database",
            return_value=False,
        ),
        patch(
            "app.infrastructure.health_checks.check_redis",
            return_value=True,
        ),
    ):
        response = client.get("/health/ready")

    assert response.status_code == 503
    assert response.json() == {
        "status": "error",
        "database": "error",
        "redis": "ok",
    }


def test_health_ready_returns_503_when_redis_unreachable(
    minimal_env,
) -> None:
    client = TestClient(create_app())

    with (
        patch(
            "app.infrastructure.health_checks.check_database",
            return_value=True,
        ),
        patch(
            "app.infrastructure.health_checks.check_redis",
            return_value=False,
        ),
    ):
        response = client.get("/health/ready")

    assert response.status_code == 503
    assert response.json() == {
        "status": "error",
        "database": "ok",
        "redis": "error",
    }
