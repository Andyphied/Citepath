"""API tests for workspace creation."""

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
    reason="Docker is required for workspace API tests",
)


@pytest.fixture(scope="module")
def postgres_url():
    """Start a pgvector-enabled Postgres container for workspace API tests."""
    with PostgresContainer("pgvector/pgvector:pg16") as postgres:
        yield postgres.get_connection_url()


@pytest.fixture
def workspace_test_context(postgres_url, minimal_env, monkeypatch):
    """Migrated database, API client, and session with per-test cleanup."""
    monkeypatch.setenv("DATABASE_URL", postgres_url)
    reset_settings_cache()
    reset_db_engine()

    alembic_cfg = Config("alembic.ini")
    command.upgrade(alembic_cfg, "head")

    engine = create_engine(postgres_url)
    session_factory = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    session = session_factory()

    with TestClient(create_app()) as test_client:
        yield test_client, session

    session.close()
    with engine.begin() as connection:
        connection.execute(text("TRUNCATE users RESTART IDENTITY CASCADE"))
    engine.dispose()
    reset_db_engine()


def _register_and_get_token(client: TestClient) -> tuple[dict, str]:
    response = client.post(
        "/auth/register",
        json={
            "email": "workspace-owner@example.com",
            "password": "securepass123",
            "name": "Workspace Owner",
        },
    )
    assert response.status_code == 201
    body = response.json()
    return body["user"], body["access_token"]


def test_create_workspace_success(workspace_test_context) -> None:
    client, db_session = workspace_test_context
    user, token = _register_and_get_token(client)

    response = client.post(
        "/workspaces",
        json={"name": "Northstar Cloud"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Northstar Cloud"
    assert body["slug"] == "northstar-cloud"
    assert body["id"]
    assert body["created_at"]

    membership = db_session.execute(
        text(
            """
            SELECT role
            FROM workspace_members
            WHERE workspace_id = :workspace_id AND user_id = :user_id
            """
        ),
        {"workspace_id": body["id"], "user_id": user["id"]},
    ).one()
    assert membership.role == "owner"

    workspace = db_session.execute(
        text(
            """
            SELECT created_by
            FROM workspaces
            WHERE id = :workspace_id
            """
        ),
        {"workspace_id": body["id"]},
    ).one()
    assert str(workspace.created_by) == user["id"]


def test_create_workspace_with_explicit_slug(workspace_test_context) -> None:
    client, _db_session = workspace_test_context
    _user, token = _register_and_get_token(client)

    response = client.post(
        "/workspaces",
        json={"name": "Platform Team", "slug": "platform-team"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 201
    assert response.json()["slug"] == "platform-team"


def test_create_workspace_duplicate_slug_returns_409(workspace_test_context) -> None:
    client, _db_session = workspace_test_context
    _user, token = _register_and_get_token(client)
    headers = {"Authorization": f"Bearer {token}"}

    first = client.post(
        "/workspaces",
        json={"name": "First", "slug": "shared-slug"},
        headers=headers,
    )
    assert first.status_code == 201

    second = client.post(
        "/workspaces",
        json={"name": "Second", "slug": "shared-slug"},
        headers=headers,
    )

    assert second.status_code == 409
    body = second.json()
    assert body["error"]["code"] == "duplicate_slug"


def test_create_workspace_invalid_slug_returns_422(workspace_test_context) -> None:
    client, _db_session = workspace_test_context
    _user, token = _register_and_get_token(client)

    response = client.post(
        "/workspaces",
        json={"name": "Bad Slug", "slug": "Invalid Slug"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "invalid_slug"


def test_create_workspace_unauthenticated_returns_401(workspace_test_context) -> None:
    client, _db_session = workspace_test_context

    response = client.post(
        "/workspaces",
        json={"name": "Northstar Cloud"},
    )

    assert response.status_code == 401
    body = response.json()
    assert body["error"]["code"] == "unauthorized"
