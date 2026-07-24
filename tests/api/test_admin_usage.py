"""API tests for GET /workspaces/{id}/admin/usage (USAGE-004)."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
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
from app.infrastructure.db.enums import UsageEventStatus, UsageOperation
from app.infrastructure.db.session import reset_db_engine
from app.main import create_app
from app.modules.usage.models import UsageEvent


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
    reason="Docker is required for admin usage API tests",
)


@pytest.fixture(scope="module")
def postgres_url():
    """Start a pgvector-enabled Postgres container for admin API tests."""
    with PostgresContainer("pgvector/pgvector:pg16") as postgres:
        yield postgres.get_connection_url()


@pytest.fixture
def usage_api_context(postgres_url, minimal_env, monkeypatch):
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


def _add_usage_event(
    session,
    *,
    workspace_id: str,
    user_id: str | None,
    operation: UsageOperation,
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
    embedding_tokens: int = 0,
    estimated_cost_usd: Decimal | None = None,
    created_at: datetime | None = None,
) -> None:
    event = UsageEvent(
        workspace_id=UUID(workspace_id),
        user_id=UUID(user_id) if user_id else None,
        provider="openai",
        model="gpt-4o-mini",
        operation=operation,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        embedding_tokens=embedding_tokens,
        estimated_cost_usd=estimated_cost_usd,
        status=UsageEventStatus.SUCCESS,
        metadata_=None,
    )
    session.add(event)
    session.flush()
    if created_at is not None:
        session.execute(
            text(
                "UPDATE usage_events SET created_at = :created_at WHERE id = :id"
            ),
            {"created_at": created_at, "id": event.id},
        )
    session.commit()


def test_owner_gets_usage_summary_for_default_seven_day_window(
    usage_api_context,
) -> None:
    client, session = usage_api_context
    owner, owner_token = _register_user(
        client,
        email="owner-usage@example.com",
        name="Owner",
    )
    workspace = _create_workspace(
        client,
        owner_token,
        name="Usage WS",
        slug="usage-ws",
    )

    now = datetime.now(UTC)
    for _ in range(10):
        _add_usage_event(
            session,
            workspace_id=workspace["id"],
            user_id=owner["id"],
            operation=UsageOperation.CHAT_COMPLETION,
            prompt_tokens=100,
            completion_tokens=50,
            estimated_cost_usd=Decimal("0.000150"),
            created_at=now - timedelta(hours=1),
        )
    _add_usage_event(
        session,
        workspace_id=workspace["id"],
        user_id=owner["id"],
        operation=UsageOperation.EMBEDDING_QUERY,
        embedding_tokens=500,
        estimated_cost_usd=Decimal("0.000010"),
        created_at=now - timedelta(hours=2),
    )
    # Outside default window — must not count.
    _add_usage_event(
        session,
        workspace_id=workspace["id"],
        user_id=owner["id"],
        operation=UsageOperation.CHAT_COMPLETION,
        prompt_tokens=999,
        completion_tokens=999,
        estimated_cost_usd=Decimal("1.000000"),
        created_at=now - timedelta(days=10),
    )

    response = client.get(
        f"/workspaces/{workspace['id']}/admin/usage",
        headers={"Authorization": f"Bearer {owner_token}"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["workspace_id"] == workspace["id"]
    assert "from" in body
    assert "to" in body
    assert body["totals"]["prompt_tokens"] == 1000
    assert body["totals"]["completion_tokens"] == 500
    assert body["totals"]["embedding_tokens"] == 500
    assert body["totals"]["call_count"] == 11
    assert Decimal(body["totals"]["estimated_cost_usd"]) == Decimal("0.001510")
    assert any(item["operation"] == "chat_completion" for item in body["by_operation"])
    assert any(item["operation"] == "embedding_query" for item in body["by_operation"])


def test_admin_can_view_usage_summary(usage_api_context) -> None:
    client, session = usage_api_context
    owner, owner_token = _register_user(
        client,
        email="owner-admin-usage@example.com",
        name="Owner",
    )
    admin, admin_token = _register_user(
        client,
        email="admin-usage@example.com",
        name="Admin",
    )
    workspace = _create_workspace(
        client,
        owner_token,
        name="Admin Usage WS",
        slug="admin-usage-ws",
    )
    invite = _invite_member(
        client,
        owner_token,
        workspace["id"],
        email=admin["email"],
        role="admin",
    )
    assert invite.status_code == 201

    _add_usage_event(
        session,
        workspace_id=workspace["id"],
        user_id=owner["id"],
        operation=UsageOperation.CHAT_COMPLETION,
        prompt_tokens=10,
        completion_tokens=5,
        estimated_cost_usd=Decimal("0.000015"),
    )

    response = client.get(
        f"/workspaces/{workspace['id']}/admin/usage",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    assert response.json()["totals"]["call_count"] == 1


def test_viewer_cannot_view_usage_summary(usage_api_context) -> None:
    client, _session = usage_api_context
    owner, owner_token = _register_user(
        client,
        email="owner-viewer-usage@example.com",
        name="Owner",
    )
    viewer, viewer_token = _register_user(
        client,
        email="viewer-usage@example.com",
        name="Viewer",
    )
    workspace = _create_workspace(
        client,
        owner_token,
        name="Viewer Denied WS",
        slug="viewer-denied-ws",
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
        f"/workspaces/{workspace['id']}/admin/usage",
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "workspace_forbidden"


def test_member_cannot_view_usage_summary(usage_api_context) -> None:
    client, _session = usage_api_context
    owner, owner_token = _register_user(
        client,
        email="owner-member-usage@example.com",
        name="Owner",
    )
    member, member_token = _register_user(
        client,
        email="member-usage@example.com",
        name="Member",
    )
    workspace = _create_workspace(
        client,
        owner_token,
        name="Member Denied WS",
        slug="member-denied-ws",
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
        f"/workspaces/{workspace['id']}/admin/usage",
        headers={"Authorization": f"Bearer {member_token}"},
    )
    assert response.status_code == 403


def test_usage_summary_isolates_workspaces(usage_api_context) -> None:
    client, session = usage_api_context
    owner_a, token_a = _register_user(
        client,
        email="owner-a-usage@example.com",
        name="Owner A",
    )
    owner_b, token_b = _register_user(
        client,
        email="owner-b-usage@example.com",
        name="Owner B",
    )
    workspace_a = _create_workspace(
        client,
        token_a,
        name="Workspace A",
        slug="usage-ws-a",
    )
    workspace_b = _create_workspace(
        client,
        token_b,
        name="Workspace B",
        slug="usage-ws-b",
    )

    _add_usage_event(
        session,
        workspace_id=workspace_a["id"],
        user_id=owner_a["id"],
        operation=UsageOperation.CHAT_COMPLETION,
        prompt_tokens=100,
        completion_tokens=10,
        estimated_cost_usd=Decimal("0.000100"),
    )
    _add_usage_event(
        session,
        workspace_id=workspace_b["id"],
        user_id=owner_b["id"],
        operation=UsageOperation.CHAT_COMPLETION,
        prompt_tokens=999,
        completion_tokens=999,
        estimated_cost_usd=Decimal("9.999999"),
    )

    response = client.get(
        f"/workspaces/{workspace_a['id']}/admin/usage",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert response.status_code == 200
    totals = response.json()["totals"]
    assert totals["prompt_tokens"] == 100
    assert totals["completion_tokens"] == 10
    assert totals["call_count"] == 1
    assert Decimal(totals["estimated_cost_usd"]) == Decimal("0.000100")


def test_usage_summary_invalid_range_returns_422(usage_api_context) -> None:
    client, _session = usage_api_context
    _owner, owner_token = _register_user(
        client,
        email="owner-range-usage@example.com",
        name="Owner",
    )
    workspace = _create_workspace(
        client,
        owner_token,
        name="Range WS",
        slug="range-ws",
    )

    response = client.get(
        f"/workspaces/{workspace['id']}/admin/usage",
        params={
            "from": "2026-07-20T00:00:00Z",
            "to": "2026-07-10T00:00:00Z",
        },
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_usage_range"
