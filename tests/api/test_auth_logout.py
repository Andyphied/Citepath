"""API tests for POST /auth/logout (AUTH-003)."""

from pathlib import Path

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
    reason="Docker is required for auth logout API tests",
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
            "email": "logout-user@example.com",
            "password": "securepass123",
            "name": "Logout User",
        },
    )
    assert response.status_code == 201
    return response.json()


def test_logout_returns_204_when_authenticated(auth_test_context) -> None:
    client = auth_test_context
    registered = _register_user(client)
    token = registered["access_token"]

    response = client.post(
        "/auth/logout",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 204
    assert response.content == b""


def test_logout_requires_authentication(auth_test_context) -> None:
    client = auth_test_context

    response = client.post("/auth/logout")

    assert response.status_code == 401
    body = response.json()
    assert body["error"]["code"] == "unauthorized"


def test_logout_does_not_blocklist_token_in_mvp(auth_test_context) -> None:
    """MVP has no Redis blocklist; the same JWT still works on /auth/me after logout."""
    client = auth_test_context
    registered = _register_user(client)
    token = registered["access_token"]

    logout_response = client.post(
        "/auth/logout",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert logout_response.status_code == 204

    me_response = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me_response.status_code == 200
    assert me_response.json()["email"] == "logout-user@example.com"
