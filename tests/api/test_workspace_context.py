"""API tests for active workspace context dependency chain."""

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import sessionmaker

try:
    from testcontainers.postgres import PostgresContainer
except ImportError:  # pragma: no cover - optional dev dependency
    PostgresContainer = None

from app.infrastructure.config import reset_settings_cache
from app.infrastructure.db.session import reset_db_engine
from app.main import create_app
from app.modules.audit.models import AuditLog
from app.modules.workspaces.permissions import FAILED_AUTHORIZATION_EVENT

TEST_CLIENT_IP = "203.0.113.50"


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
    reason="Docker is required for workspace context API tests",
)


@pytest.fixture(scope="module")
def postgres_url():
    """Start a pgvector-enabled Postgres container for workspace context tests."""
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
    slug: str,
) -> dict:
    response = client.post(
        "/workspaces",
        json={"name": name, "slug": slug},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    return response.json()


def test_get_workspace_non_member_returns_403(workspace_test_context) -> None:
    client, _db_session = workspace_test_context
    _owner, owner_token = _register_user(
        client,
        email="ctx-owner@example.com",
        name="Workspace Owner",
    )
    _other_user, other_token = _register_user(
        client,
        email="ctx-other@example.com",
        name="Other User",
    )
    workspace = _create_workspace(
        client,
        owner_token,
        name="Private Workspace",
        slug="ctx-private-workspace",
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
        email="ctx-unknown@example.com",
        name="Unknown ID User",
    )

    response = client.get(
        "/workspaces/00000000-0000-0000-0000-000000000001",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "forbidden"


def test_get_workspace_member_succeeds(workspace_test_context) -> None:
    client, _db_session = workspace_test_context
    _user, token = _register_user(
        client,
        email="ctx-member@example.com",
        name="Member User",
    )
    headers = {"Authorization": f"Bearer {token}"}
    workspace = _create_workspace(
        client,
        token,
        name="Member Workspace",
        slug="ctx-member-workspace",
    )

    response = client.get(f"/workspaces/{workspace['id']}", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == workspace["id"]
    assert body["name"] == "Member Workspace"
    assert body["member_count"] == 1


def test_non_member_denial_records_audit_with_ip_address(
    workspace_test_context,
) -> None:
    client, db_session = workspace_test_context
    _owner, owner_token = _register_user(
        client,
        email="ctx-audit-owner@example.com",
        name="Audit Owner",
    )
    outsider, outsider_token = _register_user(
        client,
        email="ctx-audit-outsider@example.com",
        name="Audit Outsider",
    )
    workspace = _create_workspace(
        client,
        owner_token,
        name="Audit Workspace",
        slug="ctx-audit-workspace",
    )

    response = client.get(
        f"/workspaces/{workspace['id']}",
        headers={
            "Authorization": f"Bearer {outsider_token}",
            "X-Forwarded-For": TEST_CLIENT_IP,
        },
    )

    assert response.status_code == 403

    db_session.expire_all()
    audit_rows = db_session.scalars(
        select(AuditLog).where(
            AuditLog.workspace_id == workspace["id"],
            AuditLog.event_type == FAILED_AUTHORIZATION_EVENT,
        )
    ).all()
    assert len(audit_rows) == 1
    assert str(audit_rows[0].actor_user_id) == outsider["id"]
    assert audit_rows[0].metadata_["reason"] == "non_member"
    assert audit_rows[0].metadata_["action"] == "view_documents"
    assert audit_rows[0].ip_address == "testclient"
