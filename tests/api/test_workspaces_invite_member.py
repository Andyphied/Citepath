"""API tests for workspace member invite endpoint."""

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


def test_invite_member_invitee_sees_workspace_in_list(
    workspace_test_context,
) -> None:
    """Acceptance: invited user sees workspace with assigned role via GET /workspaces."""
    client, _db_session = workspace_test_context
    _owner, owner_token = _register_user(
        client,
        email="list-invite-owner@example.com",
        name="Workspace Owner",
    )
    _invitee, invitee_token = _register_user(
        client,
        email="engineer@example.com",
        name="Engineer",
    )
    workspace = _create_workspace(
        client,
        owner_token,
        name="Platform Team",
        slug="platform-team-list",
    )

    invite_response = _invite_member(
        client,
        owner_token,
        workspace["id"],
        email="engineer@example.com",
        role="member",
    )
    assert invite_response.status_code == 201

    list_response = client.get(
        "/workspaces",
        headers={"Authorization": f"Bearer {invitee_token}"},
    )

    assert list_response.status_code == 200
    items = list_response.json()["items"]
    assert len(items) == 1
    assert items[0]["id"] == workspace["id"]
    assert items[0]["name"] == "Platform Team"
    assert items[0]["role"] == "member"
    assert items[0]["created_at"]


def test_invite_member_as_owner_success(workspace_test_context) -> None:
    client, db_session = workspace_test_context
    _owner, owner_token = _register_user(
        client,
        email="owner@example.com",
        name="Workspace Owner",
    )
    invitee, _invitee_token = _register_user(
        client,
        email="engineer@example.com",
        name="Engineer",
    )
    workspace = _create_workspace(
        client,
        owner_token,
        name="Platform Team",
        slug="platform-team",
    )

    response = _invite_member(
        client,
        owner_token,
        workspace["id"],
        email="engineer@example.com",
        role="member",
    )

    assert response.status_code == 201
    body = response.json()
    assert body["user_id"] == invitee["id"]
    assert body["email"] == "engineer@example.com"
    assert body["role"] == "member"
    assert body["created_at"]

    membership = db_session.execute(
        text(
            """
            SELECT role
            FROM workspace_members
            WHERE workspace_id = :workspace_id AND user_id = :user_id
            """
        ),
        {"workspace_id": workspace["id"], "user_id": invitee["id"]},
    ).one()
    assert membership.role == "member"

    detail = client.get(
        f"/workspaces/{workspace['id']}",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert detail.status_code == 200
    assert detail.json()["member_count"] == 2


def test_invite_member_as_admin_success(workspace_test_context) -> None:
    client, _db_session = workspace_test_context
    _owner, owner_token = _register_user(
        client,
        email="admin-test-owner@example.com",
        name="Owner",
    )
    admin, admin_token = _register_user(
        client,
        email="admin@example.com",
        name="Admin User",
    )
    invitee, _invitee_token = _register_user(
        client,
        email="new-viewer@example.com",
        name="New Viewer",
    )
    workspace = _create_workspace(
        client,
        owner_token,
        name="Admin Invite Team",
        slug="admin-invite-team",
    )

    admin_invite = _invite_member(
        client,
        owner_token,
        workspace["id"],
        email="admin@example.com",
        role="admin",
    )
    assert admin_invite.status_code == 201

    response = _invite_member(
        client,
        admin_token,
        workspace["id"],
        email="new-viewer@example.com",
        role="viewer",
    )

    assert response.status_code == 201
    assert response.json()["user_id"] == invitee["id"]
    assert response.json()["role"] == "viewer"


def test_invite_member_viewer_returns_403(workspace_test_context) -> None:
    client, _db_session = workspace_test_context
    _owner, owner_token = _register_user(
        client,
        email="viewer-test-owner@example.com",
        name="Owner",
    )
    viewer, viewer_token = _register_user(
        client,
        email="viewer@example.com",
        name="Viewer User",
    )
    _register_user(
        client,
        email="target@example.com",
        name="Target User",
    )
    workspace = _create_workspace(
        client,
        owner_token,
        name="Viewer Test Team",
        slug="viewer-test-team",
    )

    viewer_invite = _invite_member(
        client,
        owner_token,
        workspace["id"],
        email="viewer@example.com",
        role="viewer",
    )
    assert viewer_invite.status_code == 201

    response = _invite_member(
        client,
        viewer_token,
        workspace["id"],
        email="target@example.com",
        role="member",
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "forbidden"


def test_invite_member_viewer_records_failed_authorization_audit(
    workspace_test_context,
) -> None:
    client, db_session = workspace_test_context
    _owner, owner_token = _register_user(
        client,
        email="audit-viewer-owner@example.com",
        name="Owner",
    )
    viewer, viewer_token = _register_user(
        client,
        email="audit-viewer@example.com",
        name="Viewer User",
    )
    _register_user(
        client,
        email="audit-target@example.com",
        name="Target User",
    )
    workspace = _create_workspace(
        client,
        owner_token,
        name="Audit Viewer Team",
        slug="audit-viewer-team",
    )

    viewer_invite = _invite_member(
        client,
        owner_token,
        workspace["id"],
        email="audit-viewer@example.com",
        role="viewer",
    )
    assert viewer_invite.status_code == 201

    response = _invite_member(
        client,
        viewer_token,
        workspace["id"],
        email="audit-target@example.com",
        role="member",
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
    assert str(audit_rows[0].actor_user_id) == viewer["id"]
    assert audit_rows[0].metadata_["action"] == "manage_members"
    assert audit_rows[0].metadata_["role"] == "viewer"


def test_invite_member_non_member_records_failed_authorization_audit(
    workspace_test_context,
) -> None:
    client, db_session = workspace_test_context
    _owner_a, owner_a_token = _register_user(
        client,
        email="audit-owner-a@example.com",
        name="Owner A",
    )
    owner_b, owner_b_token = _register_user(
        client,
        email="audit-owner-b@example.com",
        name="Owner B",
    )
    _register_user(
        client,
        email="audit-isolated-target@example.com",
        name="Isolated Target",
    )
    workspace_a = _create_workspace(
        client,
        owner_a_token,
        name="Audit Workspace A",
        slug="audit-workspace-a",
    )

    response = _invite_member(
        client,
        owner_b_token,
        workspace_a["id"],
        email="audit-isolated-target@example.com",
        role="member",
    )

    assert response.status_code == 403

    db_session.expire_all()
    audit_rows = db_session.scalars(
        select(AuditLog).where(
            AuditLog.workspace_id == workspace_a["id"],
            AuditLog.event_type == FAILED_AUTHORIZATION_EVENT,
        )
    ).all()
    assert len(audit_rows) == 1
    assert str(audit_rows[0].actor_user_id) == owner_b["id"]
    assert audit_rows[0].metadata_["action"] == "manage_members"
    assert audit_rows[0].metadata_["reason"] == "non_member"


def test_invite_member_member_returns_403(workspace_test_context) -> None:
    client, _db_session = workspace_test_context
    _owner, owner_token = _register_user(
        client,
        email="member-test-owner@example.com",
        name="Owner",
    )
    member, member_token = _register_user(
        client,
        email="member@example.com",
        name="Member User",
    )
    _register_user(
        client,
        email="blocked-target@example.com",
        name="Blocked Target",
    )
    workspace = _create_workspace(
        client,
        owner_token,
        name="Member Test Team",
        slug="member-test-team",
    )

    member_invite = _invite_member(
        client,
        owner_token,
        workspace["id"],
        email="member@example.com",
        role="member",
    )
    assert member_invite.status_code == 201

    response = _invite_member(
        client,
        member_token,
        workspace["id"],
        email="blocked-target@example.com",
        role="viewer",
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "forbidden"


def test_invite_member_unknown_email_returns_404(workspace_test_context) -> None:
    client, _db_session = workspace_test_context
    _owner, owner_token = _register_user(
        client,
        email="404-owner@example.com",
        name="Owner",
    )
    workspace = _create_workspace(
        client,
        owner_token,
        name="404 Test Team",
        slug="404-test-team",
    )

    response = _invite_member(
        client,
        owner_token,
        workspace["id"],
        email="nobody@example.com",
        role="member",
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "user_not_found"


def test_invite_member_duplicate_returns_409(workspace_test_context) -> None:
    client, _db_session = workspace_test_context
    _owner, owner_token = _register_user(
        client,
        email="409-owner@example.com",
        name="Owner",
    )
    _register_user(
        client,
        email="duplicate@example.com",
        name="Duplicate User",
    )
    workspace = _create_workspace(
        client,
        owner_token,
        name="409 Test Team",
        slug="409-test-team",
    )

    first = _invite_member(
        client,
        owner_token,
        workspace["id"],
        email="duplicate@example.com",
        role="member",
    )
    assert first.status_code == 201

    second = _invite_member(
        client,
        owner_token,
        workspace["id"],
        email="duplicate@example.com",
        role="viewer",
    )

    assert second.status_code == 409
    assert second.json()["error"]["code"] == "already_member"


def test_invite_member_non_member_workspace_returns_403(
    workspace_test_context,
) -> None:
    client, _db_session = workspace_test_context
    _owner_a, owner_a_token = _register_user(
        client,
        email="owner-a@example.com",
        name="Owner A",
    )
    _owner_b, owner_b_token = _register_user(
        client,
        email="owner-b@example.com",
        name="Owner B",
    )
    _register_user(
        client,
        email="isolated-target@example.com",
        name="Isolated Target",
    )
    workspace_a = _create_workspace(
        client,
        owner_a_token,
        name="Workspace A",
        slug="workspace-a-isolated",
    )

    response = _invite_member(
        client,
        owner_b_token,
        workspace_a["id"],
        email="isolated-target@example.com",
        role="member",
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "forbidden"


def test_invite_member_admin_cannot_assign_owner(workspace_test_context) -> None:
    client, _db_session = workspace_test_context
    _owner, owner_token = _register_user(
        client,
        email="owner-role-owner@example.com",
        name="Owner",
    )
    admin, admin_token = _register_user(
        client,
        email="owner-role-admin@example.com",
        name="Admin",
    )
    _register_user(
        client,
        email="would-be-owner@example.com",
        name="Would Be Owner",
    )
    workspace = _create_workspace(
        client,
        owner_token,
        name="Owner Role Team",
        slug="owner-role-team",
    )

    admin_invite = _invite_member(
        client,
        owner_token,
        workspace["id"],
        email="owner-role-admin@example.com",
        role="admin",
    )
    assert admin_invite.status_code == 201

    response = _invite_member(
        client,
        admin_token,
        workspace["id"],
        email="would-be-owner@example.com",
        role="owner",
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "forbidden"


def test_invite_member_invalid_role_returns_422(
    workspace_test_context,
) -> None:
    client, _db_session = workspace_test_context
    _owner, owner_token = _register_user(
        client,
        email="invalid-role-owner@example.com",
        name="Owner",
    )
    _register_user(
        client,
        email="invalid-role-target@example.com",
        name="Target User",
    )
    workspace = _create_workspace(
        client,
        owner_token,
        name="Invalid Role Team",
        slug="invalid-role-team",
    )

    response = _invite_member(
        client,
        owner_token,
        workspace["id"],
        email="invalid-role-target@example.com",
        role="superadmin",
    )

    assert response.status_code == 422


def test_invite_member_unauthenticated_returns_401(workspace_test_context) -> None:
    client, _db_session = workspace_test_context
    _owner, owner_token = _register_user(
        client,
        email="unauth-owner@example.com",
        name="Owner",
    )
    workspace = _create_workspace(
        client,
        owner_token,
        name="Unauth Team",
        slug="unauth-team",
    )

    response = client.post(
        f"/workspaces/{workspace['id']}/members",
        json={"email": "someone@example.com", "role": "member"},
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"
