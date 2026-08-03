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
        patch(
            "app.infrastructure.health_checks.get_celery_queue_depth",
            return_value=4,
        ),
    ):
        response = client.get("/health/ready")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "database": "ok",
        "redis": "ok",
        "queue_depth": 4,
        "worker": {"status": "ok", "queue_depth": 4},
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
        patch(
            "app.infrastructure.health_checks.get_celery_queue_depth",
            return_value=0,
        ),
    ):
        response = client.get("/health/ready")

    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "error"
    assert body["database"] == "error"
    assert body["redis"] == "ok"
    assert body["queue_depth"] == 0
    assert body["worker"]["status"] == "ok"


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
        "queue_depth": 0,
        "worker": {"status": "error", "queue_depth": 0},
    }
