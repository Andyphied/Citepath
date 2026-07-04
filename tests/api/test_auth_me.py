"""API tests for GET /auth/me."""

from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import jwt
import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

try:
    from testcontainers.postgres import PostgresContainer
except ImportError:  # pragma: no cover - optional dev dependency
    PostgresContainer = None

from app.infrastructure.config import reset_settings_cache
from app.infrastructure.db.session import reset_db_engine
from app.main import create_app

REPO_ROOT = Path(__file__).resolve().parents[2]


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
    reason="Docker is required for auth me API tests",
)


@pytest.fixture(scope="module")
def postgres_url():
    """Start a pgvector-enabled Postgres container for auth API tests."""
    with PostgresContainer("pgvector/pgvector:pg16") as postgres:
        yield postgres.get_connection_url()


@pytest.fixture
def auth_test_context(postgres_url, minimal_env, monkeypatch):
    """Migrated database and API client with per-test cleanup."""
    monkeypatch.chdir(REPO_ROOT)
    monkeypatch.setenv("DATABASE_URL", postgres_url)
    reset_settings_cache()
    reset_db_engine()

    alembic_cfg = Config(str(REPO_ROOT / "alembic.ini"))
    command.upgrade(alembic_cfg, "head")

    engine = create_engine(postgres_url)

    with TestClient(create_app()) as test_client:
        yield test_client

    with engine.begin() as connection:
        connection.execute(text("TRUNCATE users RESTART IDENTITY CASCADE"))
    engine.dispose()
    reset_db_engine()


def _register_user(client: TestClient) -> dict:
    response = client.post(
        "/auth/register",
        json={
            "email": "me-user@example.com",
            "password": "securepass123",
            "name": "Me User",
        },
    )
    assert response.status_code == 201
    return response.json()


def test_me_returns_user_profile_with_valid_token(auth_test_context) -> None:
    client = auth_test_context
    registered = _register_user(client)
    token = registered["access_token"]

    response = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == registered["user"]["id"]
    assert body["email"] == registered["user"]["email"]
    assert body["name"] == registered["user"]["name"]
    assert body["created_at"] == registered["user"]["created_at"]
    assert "password_hash" not in body
    assert "password" not in body
    assert "updated_at" not in body


def test_me_returns_401_without_authorization_header(
    auth_test_context,
) -> None:
    client = auth_test_context

    response = client.get("/auth/me")

    assert response.status_code == 401
    body = response.json()
    assert body["error"]["code"] == "unauthorized"
    assert body["error"]["message"] == "Authentication required"


def test_me_returns_401_for_expired_token(auth_test_context) -> None:
    client = auth_test_context
    registered = _register_user(client)
    user_id = registered["user"]["id"]
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
        "/auth/me",
        headers={"Authorization": f"Bearer {expired_token}"},
    )

    assert response.status_code == 401
    body = response.json()
    assert body["error"]["code"] == "token_expired"
    assert body["error"]["message"] == "Access token has expired"


def test_me_returns_401_for_invalid_token(auth_test_context) -> None:
    client = auth_test_context

    response = client.get(
        "/auth/me",
        headers={"Authorization": "Bearer not-a-valid-jwt"},
    )

    assert response.status_code == 401
    body = response.json()
    assert body["error"]["code"] == "token_invalid"
    assert body["error"]["message"] == "Invalid access token"


def test_me_returns_401_for_unknown_user_id(auth_test_context) -> None:
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
        "/auth/me",
        headers={"Authorization": f"Bearer {unknown_user_token}"},
    )

    assert response.status_code == 401
    body = response.json()
    assert body["error"]["code"] == "token_invalid"
    assert body["error"]["message"] == "Invalid access token"
