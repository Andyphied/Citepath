"""Unit tests for JWT token creation."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt

from app.infrastructure.config import Settings
from app.modules.auth.jwt import create_access_token


def test_create_access_token_includes_sub_exp_iat(minimal_env) -> None:
    settings = Settings(
        DATABASE_URL="postgresql://user:pass@localhost:5432/atlasops",
        REDIS_URL="redis://localhost:6379/0",
        JWT_SECRET_KEY="test-secret-key",
        STORAGE_BACKEND="local",
        LLM_PROVIDER="openai",
        OPENAI_API_KEY="sk-test",
        JWT_EXPIRY_HOURS=24,
    )
    user_id = uuid4()

    token, expires_in = create_access_token(user_id, settings)

    assert expires_in == 86400
    payload = jwt.decode(
        token,
        settings.JWT_SECRET_KEY,
        algorithms=["HS256"],
    )
    assert payload["sub"] == str(user_id)
    assert "exp" in payload
    assert "iat" in payload

    exp = datetime.fromtimestamp(payload["exp"], tz=UTC)
    iat = datetime.fromtimestamp(payload["iat"], tz=UTC)
    assert exp - iat == timedelta(hours=24)
