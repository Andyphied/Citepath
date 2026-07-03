"""Unit tests for AuthService."""

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from app.infrastructure.config import Settings
from app.modules.auth.exceptions import DuplicateEmailError, InvalidCredentialsError
from app.modules.auth.password import DUMMY_PASSWORD_HASH
from app.modules.auth.service import AuthService
from app.modules.users.models import User


@pytest.fixture
def settings(minimal_env) -> Settings:
    return Settings(
        DATABASE_URL="postgresql://user:pass@localhost:5432/atlasops",
        REDIS_URL="redis://localhost:6379/0",
        JWT_SECRET_KEY="test-secret-key",
        STORAGE_BACKEND="local",
        LLM_PROVIDER="openai",
        OPENAI_API_KEY="sk-test",
    )


@pytest.fixture
def auth_repository() -> MagicMock:
    return MagicMock()


@pytest.fixture
def auth_service(auth_repository: MagicMock, settings: Settings) -> AuthService:
    return AuthService(auth_repository, settings)


def test_register_creates_user_and_returns_token(
    auth_service: AuthService,
    auth_repository: MagicMock,
) -> None:
    auth_repository.find_user_by_email.return_value = None
    user_id = uuid4()
    created_user = User(
        id=user_id,
        email="user@example.com",
        password_hash="hashed",
        name="Jane",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    auth_repository.create_user.return_value = created_user

    response = auth_service.register(
        email="user@example.com",
        password="password123",
        name="Jane",
    )

    assert response.user.email == "user@example.com"
    assert response.user.name == "Jane"
    assert response.user.id == user_id
    assert response.token_type == "bearer"
    assert response.access_token
    assert response.expires_in == 24 * 3600
    auth_repository.create_user.assert_called_once()
    stored_hash = auth_repository.create_user.call_args.kwargs["password_hash"]
    assert stored_hash != "password123"
    assert stored_hash.startswith("$2b$")


def test_register_raises_duplicate_email(
    auth_service: AuthService,
    auth_repository: MagicMock,
) -> None:
    auth_repository.find_user_by_email.return_value = User(
        id=uuid4(),
        email="user@example.com",
        password_hash="existing",
        name=None,
    )

    with pytest.raises(DuplicateEmailError):
        auth_service.register(
            email="user@example.com",
            password="password123",
            name=None,
        )

    auth_repository.create_user.assert_not_called()


def test_login_returns_user_and_token(
    auth_service: AuthService,
    auth_repository: MagicMock,
) -> None:
    user_id = uuid4()
    password_hash = "$2b$12$testhash"
    existing_user = User(
        id=user_id,
        email="user@example.com",
        password_hash=password_hash,
        name="Jane",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    auth_repository.find_user_by_email.return_value = existing_user

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(
            "app.modules.auth.service.verify_password",
            lambda password, stored_hash: password == "password123"
            and stored_hash == password_hash,
        )
        response = auth_service.login(
            email="user@example.com",
            password="password123",
        )

    assert response.user.email == "user@example.com"
    assert response.user.id == user_id
    assert response.token_type == "bearer"
    assert response.access_token
    assert response.expires_in == 24 * 3600


def test_login_raises_invalid_credentials_for_unknown_email(
    auth_service: AuthService,
    auth_repository: MagicMock,
) -> None:
    auth_repository.find_user_by_email.return_value = None

    with patch("app.modules.auth.service.verify_password") as mock_verify:
        mock_verify.return_value = False
        with pytest.raises(InvalidCredentialsError):
            auth_service.login(
                email="missing@example.com",
                password="password123",
            )

        mock_verify.assert_called_once_with("password123", DUMMY_PASSWORD_HASH)


def test_login_raises_invalid_credentials_for_malformed_hash(
    auth_service: AuthService,
    auth_repository: MagicMock,
) -> None:
    auth_repository.find_user_by_email.return_value = User(
        id=uuid4(),
        email="user@example.com",
        password_hash="not-a-valid-bcrypt-hash",
        name=None,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )

    with pytest.raises(InvalidCredentialsError):
        auth_service.login(
            email="user@example.com",
            password="password123",
        )


def test_login_raises_invalid_credentials_for_wrong_password(
    auth_service: AuthService,
    auth_repository: MagicMock,
) -> None:
    auth_repository.find_user_by_email.return_value = User(
        id=uuid4(),
        email="user@example.com",
        password_hash="hashed",
        name=None,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(
            "app.modules.auth.service.verify_password",
            lambda _password, _stored_hash: False,
        )
        with pytest.raises(InvalidCredentialsError):
            auth_service.login(
                email="user@example.com",
                password="wrongpassword",
            )
