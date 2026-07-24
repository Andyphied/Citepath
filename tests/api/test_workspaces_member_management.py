"""API tests for workspace member role change and removal endpoints."""

from pathlib import Path

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


def _patch_member_role(
    client: TestClient,
    token: str,
    workspace_id: str,
    user_id: str,
    *,
    role: str,
):
    return client.patch(
        f"/workspaces/{workspace_id}/members/{user_id}",
        json={"role": role},
        headers={"Authorization": f"Bearer {token}"},
    )


def _delete_member(
    client: TestClient,
    token: str,
    workspace_id: str,
    user_id: str,
):
    return client.delete(
        f"/workspaces/{workspace_id}/members/{user_id}",
        headers={"Authorization": f"Bearer {token}"},
    )


def test_owner_changes_member_to_viewer_updates_permissions(
    workspace_test_context,
) -> None:
    """Acceptance: Owner PATCH member→viewer; invitee sees viewer role."""
    client, db_session = workspace_test_context
    owner, owner_token = _register_user(
        client,
        email="role-change-owner@example.com",
        name="Workspace Owner",
    )
    invitee, invitee_token = _register_user(
        client,
        email="role-change-member@example.com",
        name="Member User",
    )
    workspace = _create_workspace(
        client,
        owner_token,
        name="Role Change Team",
        slug="role-change-team",
    )

    invite_response = _invite_member(
        client,
        owner_token,
        workspace["id"],
        email="role-change-member@example.com",
        role="member",
    )
    assert invite_response.status_code == 201

    patch_response = _patch_member_role(
        client,
        owner_token,
        workspace["id"],
        invitee["id"],
        role="viewer",
    )
    assert patch_response.status_code == 200
    body = patch_response.json()
    assert body["user_id"] == invitee["id"]
    assert body["role"] == "viewer"

    list_response = client.get(
        "/workspaces",
        headers={"Authorization": f"Bearer {invitee_token}"},
    )
    assert list_response.status_code == 200
    items = list_response.json()["items"]
    assert len(items) == 1
    assert items[0]["role"] == "viewer"

    db_session.expire_all()
    audit_row = db_session.scalar(
        select(AuditLog).where(
            AuditLog.workspace_id == workspace["id"],
            AuditLog.event_type == "member.role_changed",
        )
    )
    assert audit_row is not None
    assert str(audit_row.actor_user_id) == owner["id"]
    assert audit_row.metadata_["target_user_id"] == invitee["id"]
    assert audit_row.metadata_["old_role"] == "member"
    assert audit_row.metadata_["new_role"] == "viewer"


def test_sole_owner_cannot_remove_self(workspace_test_context) -> None:
    """Acceptance: sole Owner DELETE self returns 400 with clear message."""
    client, _db_session = workspace_test_context
    owner, owner_token = _register_user(
        client,
        email="sole-owner-remove@example.com",
        name="Sole Owner",
    )
    workspace = _create_workspace(
        client,
        owner_token,
        name="Sole Owner Team",
        slug="sole-owner-remove-team",
    )

    response = _delete_member(
        client,
        owner_token,
        workspace["id"],
        owner["id"],
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "last_owner"
    assert "last owner" in response.json()["error"]["message"].lower()


def test_sole_owner_cannot_demote_self(workspace_test_context) -> None:
    """Acceptance: sole Owner PATCH self demotion returns 400."""
    client, _db_session = workspace_test_context
    owner, owner_token = _register_user(
        client,
        email="sole-owner-demote@example.com",
        name="Sole Owner",
    )
    workspace = _create_workspace(
        client,
        owner_token,
        name="Sole Owner Demote Team",
        slug="sole-owner-demote-team",
    )

    response = _patch_member_role(
        client,
        owner_token,
        workspace["id"],
        owner["id"],
        role="admin",
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "last_owner"


def test_admin_cannot_modify_owner_role(workspace_test_context) -> None:
    """Acceptance: Admin PATCH on Owner target returns 403."""
    client, _db_session = workspace_test_context
    owner, owner_token = _register_user(
        client,
        email="admin-mod-owner@example.com",
        name="Owner",
    )
    admin, admin_token = _register_user(
        client,
        email="admin-mod-admin@example.com",
        name="Admin",
    )
    co_owner, _co_owner_token = _register_user(
        client,
        email="admin-mod-coowner@example.com",
        name="Co Owner",
    )
    workspace = _create_workspace(
        client,
        owner_token,
        name="Admin Mod Owner Team",
        slug="admin-mod-owner-team",
    )

    assert _invite_member(
        client,
        owner_token,
        workspace["id"],
        email="admin-mod-admin@example.com",
        role="admin",
    ).status_code == 201
    assert _invite_member(
        client,
        owner_token,
        workspace["id"],
        email="admin-mod-coowner@example.com",
        role="owner",
    ).status_code == 201

    response = _patch_member_role(
        client,
        admin_token,
        workspace["id"],
        co_owner["id"],
        role="admin",
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "forbidden"


def test_viewer_cannot_manage_members(workspace_test_context) -> None:
    """Acceptance: Viewer PATCH member returns 403."""
    client, _db_session = workspace_test_context
    owner, owner_token = _register_user(
        client,
        email="viewer-manage-owner@example.com",
        name="Owner",
    )
    viewer, viewer_token = _register_user(
        client,
        email="viewer-manage-viewer@example.com",
        name="Viewer",
    )
    member, _member_token = _register_user(
        client,
        email="viewer-manage-target@example.com",
        name="Target Member",
    )
    workspace = _create_workspace(
        client,
        owner_token,
        name="Viewer Manage Team",
        slug="viewer-manage-team",
    )

    assert _invite_member(
        client,
        owner_token,
        workspace["id"],
        email="viewer-manage-viewer@example.com",
        role="viewer",
    ).status_code == 201
    assert _invite_member(
        client,
        owner_token,
        workspace["id"],
        email="viewer-manage-target@example.com",
        role="member",
    ).status_code == 201

    patch_response = _patch_member_role(
        client,
        viewer_token,
        workspace["id"],
        member["id"],
        role="viewer",
    )
    delete_response = _delete_member(
        client,
        viewer_token,
        workspace["id"],
        member["id"],
    )

    assert patch_response.status_code == 403
    assert delete_response.status_code == 403
    assert patch_response.json()["error"]["code"] == "forbidden"


def test_member_cannot_manage_members(workspace_test_context) -> None:
    """Acceptance: Member PATCH/DELETE member returns 403."""
    client, _db_session = workspace_test_context
    owner, owner_token = _register_user(
        client,
        email="member-manage-owner@example.com",
        name="Owner",
    )
    member_caller, member_token = _register_user(
        client,
        email="member-manage-caller@example.com",
        name="Member Caller",
    )
    target, _target_token = _register_user(
        client,
        email="member-manage-target@example.com",
        name="Target",
    )
    workspace = _create_workspace(
        client,
        owner_token,
        name="Member Manage Team",
        slug="member-manage-team",
    )

    assert _invite_member(
        client,
        owner_token,
        workspace["id"],
        email="member-manage-caller@example.com",
        role="member",
    ).status_code == 201
    assert _invite_member(
        client,
        owner_token,
        workspace["id"],
        email="member-manage-target@example.com",
        role="viewer",
    ).status_code == 201

    patch_response = _patch_member_role(
        client,
        member_token,
        workspace["id"],
        target["id"],
        role="member",
    )
    delete_response = _delete_member(
        client,
        member_token,
        workspace["id"],
        target["id"],
    )

    assert patch_response.status_code == 403
    assert delete_response.status_code == 403


def test_non_member_cannot_manage_members(workspace_test_context) -> None:
    """Acceptance: non-member PATCH/DELETE returns 403."""
    client, _db_session = workspace_test_context
    owner, owner_token = _register_user(
        client,
        email="nonmember-manage-owner@example.com",
        name="Owner",
    )
    _outsider, outsider_token = _register_user(
        client,
        email="nonmember-outsider@example.com",
        name="Outsider",
    )
    target, _target_token = _register_user(
        client,
        email="nonmember-target@example.com",
        name="Target",
    )
    workspace = _create_workspace(
        client,
        owner_token,
        name="Non Member Manage Team",
        slug="nonmember-manage-team",
    )

    assert _invite_member(
        client,
        owner_token,
        workspace["id"],
        email="nonmember-target@example.com",
        role="member",
    ).status_code == 201

    patch_response = _patch_member_role(
        client,
        outsider_token,
        workspace["id"],
        target["id"],
        role="viewer",
    )
    delete_response = _delete_member(
        client,
        outsider_token,
        workspace["id"],
        target["id"],
    )

    assert patch_response.status_code == 403
    assert delete_response.status_code == 403


def test_target_not_in_workspace_returns_404(workspace_test_context) -> None:
    """Acceptance: PATCH/DELETE on non-member user_id returns 404."""
    client, _db_session = workspace_test_context
    owner, owner_token = _register_user(
        client,
        email="404-manage-owner@example.com",
        name="Owner",
    )
    outsider, _outsider_token = _register_user(
        client,
        email="404-outsider@example.com",
        name="Outsider",
    )
    workspace = _create_workspace(
        client,
        owner_token,
        name="404 Manage Team",
        slug="404-manage-team",
    )

    patch_response = _patch_member_role(
        client,
        owner_token,
        workspace["id"],
        outsider["id"],
        role="viewer",
    )
    delete_response = _delete_member(
        client,
        owner_token,
        workspace["id"],
        outsider["id"],
    )

    assert patch_response.status_code == 404
    assert delete_response.status_code == 404
    assert patch_response.json()["error"]["code"] == "member_not_found"


def test_owner_self_removal_with_co_owner(workspace_test_context) -> None:
    """Self-removal allowed when another Owner exists."""
    client, db_session = workspace_test_context
    owner, owner_token = _register_user(
        client,
        email="coowner-remove-a@example.com",
        name="Owner A",
    )
    co_owner, _co_owner_token = _register_user(
        client,
        email="coowner-remove-b@example.com",
        name="Owner B",
    )
    workspace = _create_workspace(
        client,
        owner_token,
        name="Co Owner Remove Team",
        slug="coowner-remove-team",
    )

    assert _invite_member(
        client,
        owner_token,
        workspace["id"],
        email="coowner-remove-b@example.com",
        role="owner",
    ).status_code == 201

    response = _delete_member(
        client,
        owner_token,
        workspace["id"],
        owner["id"],
    )
    assert response.status_code == 204

    remaining = db_session.execute(
        text(
            """
            SELECT COUNT(*)
            FROM workspace_members
            WHERE workspace_id = :workspace_id
            """
        ),
        {"workspace_id": workspace["id"]},
    ).scalar_one()
    assert remaining == 1
