"""API tests for GET /workspaces/{id}/admin/audit-logs (AUDIT-007)."""

from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID

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
from app.modules.audit.models import AuditLog

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
    reason="Docker is required for admin audit log API tests",
)


@pytest.fixture(scope="module")
def postgres_url():
    """Start a pgvector-enabled Postgres container for admin API tests."""
    with PostgresContainer("pgvector/pgvector:pg16") as postgres:
        yield postgres.get_connection_url()


@pytest.fixture
def audit_api_context(postgres_url, minimal_env, monkeypatch):
    """Migrated database, API client, and session with per-test cleanup."""
    monkeypatch.chdir(REPO_ROOT)
    monkeypatch.setenv("DATABASE_URL", postgres_url)
    reset_settings_cache()
    reset_db_engine()

    alembic_cfg = Config(str(REPO_ROOT / "alembic.ini"))
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


def _invite_member(
    client: TestClient,
    token: str,
    workspace_id: str,
    *,
    email: str,
    role: str,
):
    return client.post(
        f"/workspaces/{workspace_id}/members",
        json={"email": email, "role": role},
        headers={"Authorization": f"Bearer {token}"},
    )


def _add_audit_event(
    session,
    *,
    workspace_id: str,
    actor_user_id: str | None,
    event_type: str,
    metadata: dict | None = None,
    created_at: datetime | None = None,
) -> AuditLog:
    event = AuditLog(
        workspace_id=UUID(workspace_id),
        actor_user_id=UUID(actor_user_id) if actor_user_id else None,
        event_type=event_type,
        metadata_=metadata or {},
        ip_address=None,
    )
    session.add(event)
    session.flush()
    if created_at is not None:
        session.execute(
            text(
                "UPDATE audit_logs SET created_at = :created_at WHERE id = :id"
            ),
            {"created_at": created_at, "id": event.id},
        )
    session.commit()
    session.refresh(event)
    return event


def test_admin_lists_audit_logs_newest_first(audit_api_context) -> None:
    client, session = audit_api_context
    owner, owner_token = _register_user(
        client,
        email="owner-audit-list@example.com",
        name="Owner",
    )
    admin, admin_token = _register_user(
        client,
        email="admin-audit-list@example.com",
        name="Admin",
    )
    workspace = _create_workspace(
        client,
        owner_token,
        name="Audit List WS",
        slug="audit-list-ws",
    )
    invite = _invite_member(
        client,
        owner_token,
        workspace["id"],
        email=admin["email"],
        role="admin",
    )
    assert invite.status_code == 201

    now = datetime.now(UTC)
    _add_audit_event(
        session,
        workspace_id=workspace["id"],
        actor_user_id=owner["id"],
        event_type="document.uploaded",
        metadata={"document_id": "old", "title": "old.md"},
        created_at=now - timedelta(hours=2),
    )
    _add_audit_event(
        session,
        workspace_id=workspace["id"],
        actor_user_id=admin["id"],
        event_type="member.role_changed",
        metadata={
            "target_user_id": admin["id"],
            "old_role": "member",
            "new_role": "admin",
        },
        created_at=now - timedelta(hours=1),
    )
    _add_audit_event(
        session,
        workspace_id=workspace["id"],
        actor_user_id=owner["id"],
        event_type="document.deleted",
        metadata={"document_id": "new", "title": "new.md"},
        created_at=now,
    )

    response = client.get(
        f"/workspaces/{workspace['id']}/admin/audit-logs",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 3
    assert body["page"] == 1
    assert body["page_size"] == 20
    event_types = [item["event_type"] for item in body["items"]]
    assert event_types == [
        "document.deleted",
        "member.role_changed",
        "document.uploaded",
    ]


def test_audit_logs_filter_by_event_type_actor_and_date(
    audit_api_context,
) -> None:
    client, session = audit_api_context
    owner, owner_token = _register_user(
        client,
        email="owner-audit-filter@example.com",
        name="Owner",
    )
    member, _member_token = _register_user(
        client,
        email="member-audit-filter@example.com",
        name="Member",
    )
    workspace = _create_workspace(
        client,
        owner_token,
        name="Audit Filter WS",
        slug="audit-filter-ws",
    )
    invite = _invite_member(
        client,
        owner_token,
        workspace["id"],
        email=member["email"],
        role="member",
    )
    assert invite.status_code == 201

    now = datetime.now(UTC)
    _add_audit_event(
        session,
        workspace_id=workspace["id"],
        actor_user_id=owner["id"],
        event_type="document.uploaded",
        created_at=now - timedelta(days=2),
    )
    _add_audit_event(
        session,
        workspace_id=workspace["id"],
        actor_user_id=member["id"],
        event_type="document.uploaded",
        created_at=now - timedelta(hours=1),
    )
    _add_audit_event(
        session,
        workspace_id=workspace["id"],
        actor_user_id=owner["id"],
        event_type="document.deleted",
        created_at=now - timedelta(hours=1),
    )

    from_bound = (now - timedelta(hours=3)).isoformat()
    to_bound = (now + timedelta(minutes=1)).isoformat()
    response = client.get(
        f"/workspaces/{workspace['id']}/admin/audit-logs",
        params={
            "event_type": "document.uploaded",
            "actor_user_id": member["id"],
            "from": from_bound,
            "to": to_bound,
        },
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert len(body["items"]) == 1
    assert body["items"][0]["event_type"] == "document.uploaded"
    assert body["items"][0]["actor_user_id"] == member["id"]


def test_viewer_cannot_view_audit_logs(audit_api_context) -> None:
    client, _session = audit_api_context
    owner, owner_token = _register_user(
        client,
        email="owner-viewer-audit@example.com",
        name="Owner",
    )
    viewer, viewer_token = _register_user(
        client,
        email="viewer-audit@example.com",
        name="Viewer",
    )
    workspace = _create_workspace(
        client,
        owner_token,
        name="Viewer Audit Denied",
        slug="viewer-audit-denied",
    )
    invite = _invite_member(
        client,
        owner_token,
        workspace["id"],
        email=viewer["email"],
        role="viewer",
    )
    assert invite.status_code == 201

    response = client.get(
        f"/workspaces/{workspace['id']}/admin/audit-logs",
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "forbidden"


def test_member_cannot_view_audit_logs(audit_api_context) -> None:
    client, _session = audit_api_context
    owner, owner_token = _register_user(
        client,
        email="owner-member-audit@example.com",
        name="Owner",
    )
    member, member_token = _register_user(
        client,
        email="member-audit@example.com",
        name="Member",
    )
    workspace = _create_workspace(
        client,
        owner_token,
        name="Member Audit Denied",
        slug="member-audit-denied",
    )
    invite = _invite_member(
        client,
        owner_token,
        workspace["id"],
        email=member["email"],
        role="member",
    )
    assert invite.status_code == 201

    response = client.get(
        f"/workspaces/{workspace['id']}/admin/audit-logs",
        headers={"Authorization": f"Bearer {member_token}"},
    )
    assert response.status_code == 403


def test_audit_logs_workspace_isolation(audit_api_context) -> None:
    client, session = audit_api_context
    owner_a, token_a = _register_user(
        client,
        email="owner-a-audit@example.com",
        name="Owner A",
    )
    owner_b, token_b = _register_user(
        client,
        email="owner-b-audit@example.com",
        name="Owner B",
    )
    workspace_a = _create_workspace(
        client,
        token_a,
        name="WS A",
        slug="audit-iso-a",
    )
    workspace_b = _create_workspace(
        client,
        token_b,
        name="WS B",
        slug="audit-iso-b",
    )
    _add_audit_event(
        session,
        workspace_id=workspace_a["id"],
        actor_user_id=owner_a["id"],
        event_type="document.uploaded",
        metadata={"title": "a.md"},
    )
    _add_audit_event(
        session,
        workspace_id=workspace_b["id"],
        actor_user_id=owner_b["id"],
        event_type="document.uploaded",
        metadata={"title": "b.md"},
    )

    response = client.get(
        f"/workspaces/{workspace_a['id']}/admin/audit-logs",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["metadata"]["title"] == "a.md"
    assert body["items"][0]["workspace_id"] == workspace_a["id"]


def test_audit_logs_invalid_range_returns_422(audit_api_context) -> None:
    client, _session = audit_api_context
    _owner, owner_token = _register_user(
        client,
        email="owner-audit-range@example.com",
        name="Owner",
    )
    workspace = _create_workspace(
        client,
        owner_token,
        name="Audit Range WS",
        slug="audit-range-ws",
    )
    response = client.get(
        f"/workspaces/{workspace['id']}/admin/audit-logs",
        params={
            "from": "2026-07-20T00:00:00Z",
            "to": "2026-07-10T00:00:00Z",
        },
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_audit_range"


def test_audit_logs_pagination(audit_api_context) -> None:
    client, session = audit_api_context
    owner, owner_token = _register_user(
        client,
        email="owner-audit-page@example.com",
        name="Owner",
    )
    workspace = _create_workspace(
        client,
        owner_token,
        name="Audit Page WS",
        slug="audit-page-ws",
    )
    now = datetime.now(UTC)
    for index in range(3):
        _add_audit_event(
            session,
            workspace_id=workspace["id"],
            actor_user_id=owner["id"],
            event_type="document.uploaded",
            metadata={"title": f"doc-{index}.md"},
            created_at=now - timedelta(minutes=index),
        )

    response = client.get(
        f"/workspaces/{workspace['id']}/admin/audit-logs",
        params={"page": 2, "page_size": 2},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 3
    assert body["page"] == 2
    assert body["page_size"] == 2
    assert len(body["items"]) == 1
    assert body["items"][0]["metadata"]["title"] == "doc-2.md"
