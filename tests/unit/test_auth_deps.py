"""Unit tests for auth FastAPI dependencies."""

from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from fastapi.security import HTTPAuthorizationCredentials

from app.api.deps import get_current_user
from app.infrastructure.config import Settings
from app.modules.auth.exceptions import TokenInvalidError, UnauthorizedError
from app.modules.users.models import User


def _settings() -> Settings:
    return Settings(
        DATABASE_URL="postgresql://user:pass@localhost:5432/atlasops",
        REDIS_URL="redis://localhost:6379/0",
        JWT_SECRET_KEY="test-secret-key",
        STORAGE_BACKEND="local",
        LLM_PROVIDER="openai",
        OPENAI_API_KEY="sk-test",
    )


def test_get_current_user_raises_unauthorized_when_credentials_missing(
    minimal_env,
) -> None:
    db = MagicMock()

    with pytest.raises(UnauthorizedError):
        get_current_user(None, db, _settings())


def test_get_current_user_raises_token_invalid_when_user_not_found(
    minimal_env,
) -> None:
    from app.modules.auth.jwt import create_access_token

    settings = _settings()
    user_id = uuid4()
    token, _expires_in = create_access_token(user_id, settings)
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

    db = MagicMock()
    db.get.return_value = None

    with pytest.raises(TokenInvalidError):
        get_current_user(credentials, db, settings)


def test_get_current_user_returns_user_when_token_valid(minimal_env) -> None:
    from app.modules.auth.jwt import create_access_token

    settings = _settings()
    user_id = uuid4()
    token, _expires_in = create_access_token(user_id, settings)
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

    user = User(
        id=user_id,
        email="user@example.com",
        password_hash="hash",
        name="Test User",
    )
    db = MagicMock()
    db.get.return_value = user

    result = get_current_user(credentials, db, settings)

    assert result is user
