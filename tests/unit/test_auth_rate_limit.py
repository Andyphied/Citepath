"""Unit tests for login rate-limit HTTP handling."""

from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import create_app


def test_login_rate_limit_returns_429_with_retry_after(minimal_env) -> None:
    with patch("app.api.deps.check_login_rate_limit", return_value=30):
        with TestClient(create_app()) as client:
            response = client.post(
                "/auth/login",
                json={
                    "email": "user@example.com",
                    "password": "password123",
                },
            )

    assert response.status_code == 429
    body = response.json()
    assert body["error"]["code"] == "rate_limited"
    assert body["error"]["message"] == "Too many login attempts. Please try again later."
    assert body["error"]["details"] == {}
    assert response.headers["Retry-After"] == "30"
