"""API AC proof for AUTH-006 consistent auth error envelopes."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt
from fastapi.testclient import TestClient

from app.main import create_app
from app.modules.observability.request_context import (
    REQUEST_ID_HEADER,
    is_valid_uuid,
)


def _assert_auth_error_envelope(
    response,
    *,
    status_code: int,
    code: str,
    message: str | None = None,
) -> dict:
    """Assert standard `{ error: { code, message, details, request_id } }` shape."""
    assert response.status_code == status_code
    body = response.json()
    assert "detail" not in body
    assert "error" in body
    error = body["error"]
    assert error["code"] == code
    assert isinstance(error["message"], str) and error["message"]
    if message is not None:
        assert error["message"] == message
    assert isinstance(error["details"], dict)
    assert error["request_id"]
    assert is_valid_uuid(error["request_id"])
    assert REQUEST_ID_HEADER in response.headers
    assert response.headers[REQUEST_ID_HEADER] == error["request_id"]
    return body


def test_missing_token_returns_unauthorized_envelope(minimal_env) -> None:
    client = TestClient(create_app())

    response = client.get("/auth/me")

    _assert_auth_error_envelope(
        response,
        status_code=401,
        code="unauthorized",
        message="Authentication required",
    )


def test_expired_token_returns_token_expired_envelope(minimal_env) -> None:
    client = TestClient(create_app())
    now = datetime.now(UTC)
    expired_token = jwt.encode(
        {
            "sub": str(uuid4()),
            "iat": now - timedelta(hours=2),
            "exp": now - timedelta(hours=1),
        },
        "test-secret-key",
        algorithm="HS256",
    )

    response = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {expired_token}"},
    )

    _assert_auth_error_envelope(
        response,
        status_code=401,
        code="token_expired",
        message="Access token has expired",
    )


def test_malformed_token_returns_token_invalid_envelope(minimal_env) -> None:
    client = TestClient(create_app())

    response = client.get(
        "/auth/me",
        headers={"Authorization": "Bearer not-a-valid-jwt"},
    )

    _assert_auth_error_envelope(
        response,
        status_code=401,
        code="token_invalid",
        message="Invalid access token",
    )


def test_auth_validation_returns_validation_error_envelope(minimal_env) -> None:
    client = TestClient(create_app())

    response = client.post(
        "/auth/login",
        json={
            "email": "user@example.com",
            "password": "short",
        },
    )

    body = _assert_auth_error_envelope(
        response,
        status_code=422,
        code="validation_error",
        message="Request validation failed",
    )
    assert "password" in body["error"]["details"]
