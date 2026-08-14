"""Unit tests for JWT token verification."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt
import pytest

from app.infrastructure.config import Settings
from app.modules.auth.exceptions import TokenExpiredError, TokenInvalidError
from app.modules.auth.jwt import create_access_token, decode_access_token


def _settings() -> Settings:
    return Settings(
        DATABASE_URL="postgresql://user:pass@localhost:5432/citepath",
        REDIS_URL="redis://localhost:6379/0",
        JWT_SECRET_KEY="test-secret-key",
        STORAGE_BACKEND="local",
        LLM_PROVIDER="openai",
        OPENAI_API_KEY="sk-test",
        JWT_EXPIRY_HOURS=24,
    )


def test_decode_access_token_returns_user_id(minimal_env) -> None:
    settings = _settings()
    user_id = uuid4()
    token, _expires_in = create_access_token(user_id, settings)

    decoded_id = decode_access_token(token, settings)

    assert decoded_id == user_id


def test_decode_access_token_raises_token_expired(minimal_env) -> None:
    settings = _settings()
    user_id = uuid4()
    now = datetime.now(UTC)
    token = jwt.encode(
        {
            "sub": str(user_id),
            "iat": now - timedelta(hours=2),
            "exp": now - timedelta(hours=1),
        },
        settings.JWT_SECRET_KEY,
        algorithm="HS256",
    )

    with pytest.raises(TokenExpiredError):
        decode_access_token(token, settings)


def test_decode_access_token_raises_token_invalid_for_malformed_token(
    minimal_env,
) -> None:
    settings = _settings()

    with pytest.raises(TokenInvalidError):
        decode_access_token("not-a-jwt", settings)


def test_decode_access_token_raises_token_invalid_for_wrong_secret(
    minimal_env,
) -> None:
    settings = _settings()
    user_id = uuid4()
    token, _expires_in = create_access_token(user_id, settings)
    other_settings = settings.model_copy(update={"JWT_SECRET_KEY": "other-secret"})

    with pytest.raises(TokenInvalidError):
        decode_access_token(token, other_settings)


def test_decode_access_token_raises_token_invalid_when_exp_missing(
    minimal_env,
) -> None:
    settings = _settings()
    user_id = uuid4()
    now = datetime.now(UTC)
    token = jwt.encode(
        {
            "sub": str(user_id),
            "iat": now,
        },
        settings.JWT_SECRET_KEY,
        algorithm="HS256",
    )

    with pytest.raises(TokenInvalidError):
        decode_access_token(token, settings)


def test_decode_access_token_raises_token_invalid_when_sub_missing(
    minimal_env,
) -> None:
    settings = _settings()
    now = datetime.now(UTC)
    token = jwt.encode(
        {
            "iat": now,
            "exp": now + timedelta(hours=1),
        },
        settings.JWT_SECRET_KEY,
        algorithm="HS256",
    )

    with pytest.raises(TokenInvalidError):
        decode_access_token(token, settings)


def test_decode_access_token_raises_token_invalid_when_sub_not_uuid(
    minimal_env,
) -> None:
    settings = _settings()
    now = datetime.now(UTC)
    token = jwt.encode(
        {
            "sub": "not-a-uuid",
            "iat": now,
            "exp": now + timedelta(hours=1),
        },
        settings.JWT_SECRET_KEY,
        algorithm="HS256",
    )

    with pytest.raises(TokenInvalidError):
        decode_access_token(token, settings)
