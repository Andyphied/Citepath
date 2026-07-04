"""API tests for workspace list and get endpoints."""

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
    session_factory = sessionmaker(
        bind=engine,
        autocommit=False,
        autoflush=False,
    )
    session = session_factory()

    with TestClient(create_app()) as test_client:
        yield test_client, session

    session.close()
    with engine.begin() as connection:
        connection.execute(text("TRUNCATE users RESTART IDENTITY CASCADE"))
    engine.dispose()
    reset_db_engine()


def _register_user(
    client: TestClient,
    *,
    email: str,
    name: str,
) -> tuple[dict, str]:
    response = client.post(
        "/auth/register",
        json={
            "email": email,
            "password": "securepass123",
            "name": name,
        },
    )
    assert response.status_code == 201
    body = response.json()
    return body["user"], body["access_token"]


def _create_workspace(
    client: TestClient,
    token: str,
    *,
    name: str,
    slug: str | None = None,
) -> dict:
    payload = {"name": name}
    if slug is not None:
        payload["slug"] = slug
    response = client.post(
        "/workspaces",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    return response.json()


def test_list_workspaces_returns_memberships_with_roles(
    workspace_test_context,
) -> None:
    client, _db_session = workspace_test_context
    _user, token = _register_user(
        client,
        email="list-owner@example.com",
        name="List Owner",
    )
    headers = {"Authorization": f"Bearer {token}"}

    workspace_a = _create_workspace(
        client, token, name="Workspace A", slug="workspace-a"
    )
    workspace_b = _create_workspace(
        client, token, name="Workspace B", slug="workspace-b"
    )

    response = client.get("/workspaces", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert len(body["items"]) == 2
    by_id = {item["id"]: item for item in body["items"]}
    assert by_id[workspace_a["id"]]["name"] == "Workspace A"
    assert by_id[workspace_a["id"]]["role"] == "owner"
    assert by_id[workspace_b["id"]]["name"] == "Workspace B"
    assert by_id[workspace_b["id"]]["role"] == "owner"
    assert by_id[workspace_a["id"]]["created_at"]
    assert by_id[workspace_b["id"]]["created_at"]


def test_list_workspaces_isolated_between_users(
    workspace_test_context,
) -> None:
    client, _db_session = workspace_test_context
    user_a, token_a = _register_user(
        client,
        email="user-a@example.com",
        name="User A",
    )
    _user_b, token_b = _register_user(
        client,
        email="user-b@example.com",
        name="User B",
    )

    workspace_a = _create_workspace(
        client,
        token_a,
        name="User A Workspace",
        slug="user-a-workspace",
    )
    _create_workspace(
        client,
        token_b,
        name="User B Workspace",
        slug="user-b-workspace",
    )

    response = client.get(
        "/workspaces",
        headers={"Authorization": f"Bearer {token_a}"},
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body["items"]) == 1
    assert body["items"][0]["id"] == workspace_a["id"]
    assert body["items"][0]["role"] == "owner"


def test_list_workspaces_unauthenticated_returns_401(
    workspace_test_context,
) -> None:
    client, _db_session = workspace_test_context

    response = client.get("/workspaces")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


def test_get_workspace_returns_detail_for_member(
    workspace_test_context,
) -> None:
    client, _db_session = workspace_test_context
    _user, token = _register_user(
        client,
        email="detail-owner@example.com",
        name="Detail Owner",
    )
    headers = {"Authorization": f"Bearer {token}"}
    workspace = _create_workspace(
        client,
        token,
        name="Detail Workspace",
        slug="detail-workspace",
    )

    response = client.get(f"/workspaces/{workspace['id']}", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == workspace["id"]
    assert body["name"] == "Detail Workspace"
    assert body["member_count"] == 1
    assert body["created_at"]


def test_get_workspace_non_member_returns_403(workspace_test_context) -> None:
    client, _db_session = workspace_test_context
    _owner, owner_token = _register_user(
        client,
        email="owner@example.com",
        name="Workspace Owner",
    )
    _other_user, other_token = _register_user(
        client,
        email="other@example.com",
        name="Other User",
    )

    workspace = _create_workspace(
        client,
        owner_token,
        name="Private Workspace",
        slug="private-workspace",
    )

    response = client.get(
        f"/workspaces/{workspace['id']}",
        headers={"Authorization": f"Bearer {other_token}"},
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "forbidden"


def test_get_workspace_unknown_id_returns_403(workspace_test_context) -> None:
    client, _db_session = workspace_test_context
    _user, token = _register_user(
        client,
        email="unknown-id@example.com",
        name="Unknown ID User",
    )

    response = client.get(
        "/workspaces/00000000-0000-0000-0000-000000000001",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "forbidden"


def test_get_workspace_unauthenticated_returns_401(
    workspace_test_context,
) -> None:
    client, _db_session = workspace_test_context
    _user, token = _register_user(
        client,
        email="unauth-get@example.com",
        name="Unauth Get User",
    )
    workspace = _create_workspace(
        client,
        token,
        name="Auth Required",
        slug="auth-required",
    )

    response = client.get(f"/workspaces/{workspace['id']}")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"
