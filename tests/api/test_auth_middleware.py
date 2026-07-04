"""API integration tests for JWT authentication middleware."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt
import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

try:
    from testcontainers.postgres import PostgresContainer
except ImportError:  # pragma: no cover - optional dev dependency
    PostgresContainer = None

from app.infrastructure.config import reset_settings_cache
from app.infrastructure.db.session import reset_db_engine
from app.main import create_app


def _docker_available() -> bool:
    if PostgresContainer is None:
        return False
    try:
        import docker

        client = docker.from_env()
        client.ping()
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _docker_available(),
    reason="Docker is required for auth middleware API tests",
)


@pytest.fixture(scope="module")
def postgres_url():
    """Start a pgvector-enabled Postgres container for auth API tests."""
    with PostgresContainer("pgvector/pgvector:pg16") as postgres:
        yield postgres.get_connection_url()


@pytest.fixture
def auth_test_context(postgres_url, minimal_env, monkeypatch):
    """Migrated database and API client with per-test cleanup."""
    monkeypatch.setenv("DATABASE_URL", postgres_url)
    reset_settings_cache()
    reset_db_engine()

    alembic_cfg = Config("alembic.ini")
    command.upgrade(alembic_cfg, "head")

    engine = create_engine(postgres_url)

    with TestClient(create_app()) as test_client:
        yield test_client

    with engine.begin() as connection:
        connection.execute(text("TRUNCATE users RESTART IDENTITY CASCADE"))
    engine.dispose()
    reset_db_engine()


def _register_and_get_token(client: TestClient) -> tuple[str, str]:
    response = client.post(
        "/auth/register",
        json={
            "email": "middleware-user@example.com",
            "password": "securepass123",
            "name": "Middleware User",
        },
    )
    assert response.status_code == 201
    body = response.json()
    return body["access_token"], body["user"]["id"]


def test_session_check_success_with_valid_token(auth_test_context) -> None:
    client = auth_test_context
    token, user_id = _register_and_get_token(client)

    response = client.get(
        "/auth/session-check",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["authenticated"] is True
    assert body["user_id"] == user_id


def test_session_check_returns_401_without_authorization_header(
    auth_test_context,
) -> None:
    client = auth_test_context

    response = client.get("/auth/session-check")

    assert response.status_code == 401
    body = response.json()
    assert body["error"]["code"] == "unauthorized"
    assert body["error"]["message"] == "Authentication required"
    assert body["error"]["details"] == {}


def test_session_check_returns_401_for_expired_token(auth_test_context) -> None:
    client = auth_test_context
    _token, user_id = _register_and_get_token(client)
    now = datetime.now(UTC)
    expired_token = jwt.encode(
        {
            "sub": user_id,
            "iat": now - timedelta(hours=2),
            "exp": now - timedelta(hours=1),
        },
        "test-secret-key",
        algorithm="HS256",
    )

    response = client.get(
        "/auth/session-check",
        headers={"Authorization": f"Bearer {expired_token}"},
    )

    assert response.status_code == 401
    body = response.json()
    assert body["error"]["code"] == "token_expired"
    assert body["error"]["message"] == "Access token has expired"
    assert body["error"]["details"] == {}


def test_session_check_returns_401_for_token_without_exp(auth_test_context) -> None:
    client = auth_test_context
    _token, user_id = _register_and_get_token(client)
    now = datetime.now(UTC)
    token_without_exp = jwt.encode(
        {
            "sub": user_id,
            "iat": now,
        },
        "test-secret-key",
        algorithm="HS256",
    )

    response = client.get(
        "/auth/session-check",
        headers={"Authorization": f"Bearer {token_without_exp}"},
    )

    assert response.status_code == 401
    body = response.json()
    assert body["error"]["code"] == "token_invalid"
    assert body["error"]["message"] == "Invalid access token"
    assert body["error"]["details"] == {}


def test_session_check_returns_401_for_malformed_token(auth_test_context) -> None:
    client = auth_test_context

    response = client.get(
        "/auth/session-check",
        headers={"Authorization": "Bearer not-a-valid-jwt"},
    )

    assert response.status_code == 401
    body = response.json()
    assert body["error"]["code"] == "token_invalid"
    assert body["error"]["message"] == "Invalid access token"
    assert body["error"]["details"] == {}


def test_session_check_returns_401_for_token_with_wrong_secret(
    auth_test_context,
) -> None:
    client = auth_test_context
    _token, user_id = _register_and_get_token(client)
    now = datetime.now(UTC)
    wrong_secret_token = jwt.encode(
        {
            "sub": user_id,
            "iat": now,
            "exp": now + timedelta(hours=1),
        },
        "wrong-secret-key",
        algorithm="HS256",
    )

    response = client.get(
        "/auth/session-check",
        headers={"Authorization": f"Bearer {wrong_secret_token}"},
    )

    assert response.status_code == 401
    body = response.json()
    assert body["error"]["code"] == "token_invalid"


def test_session_check_returns_401_for_unknown_user_id(auth_test_context) -> None:
    client = auth_test_context
    now = datetime.now(UTC)
    unknown_user_token = jwt.encode(
        {
            "sub": str(uuid4()),
            "iat": now,
            "exp": now + timedelta(hours=1),
        },
        "test-secret-key",
        algorithm="HS256",
    )

    response = client.get(
        "/auth/session-check",
        headers={"Authorization": f"Bearer {unknown_user_token}"},
    )

    assert response.status_code == 401
    body = response.json()
    assert body["error"]["code"] == "token_invalid"
