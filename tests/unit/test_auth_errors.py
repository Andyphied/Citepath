"""Unit tests for AUTH-006 auth exception handlers."""

import asyncio
from unittest.mock import MagicMock

from app.api.auth_errors import (
    duplicate_email_handler,
    invalid_credentials_handler,
    rate_limited_handler,
    token_expired_handler,
    token_invalid_handler,
    unauthorized_handler,
)
from app.infrastructure.rate_limit import RateLimitedError
from app.modules.auth.exceptions import (
    DuplicateEmailError,
    InvalidCredentialsError,
    TokenExpiredError,
    TokenInvalidError,
    UnauthorizedError,
)


def _mock_request() -> MagicMock:
    request = MagicMock()
    request.state.request_id = "auth-006-request-id"
    return request


def test_invalid_credentials_handler_returns_401_envelope() -> None:
    response = asyncio.run(
        invalid_credentials_handler(_mock_request(), InvalidCredentialsError())
    )

    assert response.status_code == 401
    body = response.body.decode()
    assert '"code":"invalid_credentials"' in body.replace(" ", "")
    assert "Invalid email or password" in body
    assert "auth-006-request-id" in body
    assert '"details":{}' in body.replace(" ", "")


def test_unauthorized_handler_returns_401_envelope() -> None:
    response = asyncio.run(
        unauthorized_handler(_mock_request(), UnauthorizedError())
    )

    assert response.status_code == 401
    body = response.body.decode()
    assert '"code":"unauthorized"' in body.replace(" ", "")
    assert "Authentication required" in body


def test_token_expired_handler_returns_401_envelope() -> None:
    response = asyncio.run(
        token_expired_handler(_mock_request(), TokenExpiredError())
    )

    assert response.status_code == 401
    body = response.body.decode()
    assert '"code":"token_expired"' in body.replace(" ", "")
    assert "Access token has expired" in body


def test_token_invalid_handler_returns_401_envelope() -> None:
    response = asyncio.run(
        token_invalid_handler(_mock_request(), TokenInvalidError())
    )

    assert response.status_code == 401
    body = response.body.decode()
    assert '"code":"token_invalid"' in body.replace(" ", "")
    assert "Invalid access token" in body


def test_duplicate_email_handler_returns_409_envelope() -> None:
    response = asyncio.run(
        duplicate_email_handler(_mock_request(), DuplicateEmailError())
    )

    assert response.status_code == 409
    body = response.body.decode()
    assert '"code":"duplicate_email"' in body.replace(" ", "")


def test_rate_limited_handler_returns_429_envelope_with_retry_after() -> None:
    response = asyncio.run(
        rate_limited_handler(_mock_request(), RateLimitedError(retry_after=42))
    )

    assert response.status_code == 429
    assert response.headers["Retry-After"] == "42"
    body = response.body.decode()
    assert '"code":"rate_limited"' in body.replace(" ", "")
