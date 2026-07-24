"""API tests for ADMIN-BATCH-002 dashboard endpoints."""

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
from app.infrastructure.db.enums import (
    ConversationMode,
    DocumentStatus,
    IngestionJobStatus,
    MessageRole,
)
from app.infrastructure.db.session import reset_db_engine
from app.main import create_app
from app.modules.documents.models import Document
from app.modules.ingestion.models import IngestionJob
from app.modules.rag.models import Conversation, Message

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
    reason="Docker is required for admin dashboard API tests",
)


@pytest.fixture(scope="module")
def postgres_url():
    """Start a pgvector-enabled Postgres container for admin API tests."""
    with PostgresContainer("pgvector/pgvector:pg16") as postgres:
        yield postgres.get_connection_url()


@pytest.fixture
def admin_api_context(postgres_url, minimal_env, monkeypatch):
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


def _add_document(
    session,
    *,
    workspace_id: str,
    uploaded_by: str,
    title: str,
    status: DocumentStatus,
    created_at: datetime | None = None,
) -> Document:
    document = Document(
        workspace_id=UUID(workspace_id),
        uploaded_by=UUID(uploaded_by),
        title=title,
        source_type="upload",
        file_type="md",
        storage_key=f"docs/{title}",
        status=status,
    )
    session.add(document)
    session.flush()
    if created_at is not None:
        session.execute(
            text("UPDATE documents SET created_at = :created_at WHERE id = :id"),
            {"created_at": created_at, "id": document.id},
        )
    session.commit()
    session.refresh(document)
    return document


def _add_ingestion_job(
    session,
    *,
    workspace_id: str,
    document_id: UUID,
    status: IngestionJobStatus,
    error_message: str | None = None,
    created_at: datetime | None = None,
) -> IngestionJob:
    job = IngestionJob(
        workspace_id=UUID(workspace_id),
        document_id=document_id,
        status=status,
        attempt_count=1 if status == IngestionJobStatus.FAILED else 0,
        error_message=error_message,
    )
    session.add(job)
    session.flush()
    if created_at is not None:
        session.execute(
            text(
                "UPDATE ingestion_jobs SET created_at = :created_at WHERE id = :id"
            ),
            {"created_at": created_at, "id": job.id},
        )
    session.commit()
    session.refresh(job)
    return job


def _add_user_question(
    session,
    *,
    workspace_id: str,
    user_id: str,
    content: str,
    created_at: datetime | None = None,
) -> Message:
    conversation = Conversation(
        workspace_id=UUID(workspace_id),
        user_id=UUID(user_id),
        mode=ConversationMode.RAG,
        title="Q",
    )
    session.add(conversation)
    session.flush()
    message = Message(
        workspace_id=UUID(workspace_id),
        conversation_id=conversation.id,
        role=MessageRole.USER,
        content=content,
    )
    session.add(message)
    # Assistant message should not appear in recent-questions.
    session.add(
        Message(
            workspace_id=UUID(workspace_id),
            conversation_id=conversation.id,
            role=MessageRole.ASSISTANT,
            content="assistant reply should be hidden",
        )
    )
    session.flush()
    if created_at is not None:
        session.execute(
            text("UPDATE messages SET created_at = :created_at WHERE id = :id"),
            {"created_at": created_at, "id": message.id},
        )
    session.commit()
    session.refresh(message)
    return message


def test_documents_overview_counts_by_status(admin_api_context) -> None:
    client, session = admin_api_context
    owner, owner_token = _register_user(
        client,
        email="owner-docs-overview@example.com",
        name="Owner",
    )
    workspace = _create_workspace(
        client,
        owner_token,
        name="Docs Overview WS",
        slug="docs-overview-ws",
    )
    now = datetime.now(UTC)
    _add_document(
        session,
        workspace_id=workspace["id"],
        uploaded_by=owner["id"],
        title="a.md",
        status=DocumentStatus.INDEXED,
        created_at=now - timedelta(hours=2),
    )
    _add_document(
        session,
        workspace_id=workspace["id"],
        uploaded_by=owner["id"],
        title="b.md",
        status=DocumentStatus.FAILED,
        created_at=now - timedelta(hours=1),
    )
    _add_document(
        session,
        workspace_id=workspace["id"],
        uploaded_by=owner["id"],
        title="c.md",
        status=DocumentStatus.UPLOADED,
        created_at=now,
    )

    response = client.get(
        f"/workspaces/{workspace['id']}/admin/documents-overview",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["workspace_id"] == workspace["id"]
    assert body["total"] == 3
    assert body["by_status"] == {
        "uploaded": 1,
        "processing": 0,
        "indexed": 1,
        "failed": 1,
    }
    assert [item["title"] for item in body["recent_uploads"]] == [
        "c.md",
        "b.md",
        "a.md",
    ]


def test_ingestion_jobs_list_failed_with_error_and_title(admin_api_context) -> None:
    client, session = admin_api_context
    owner, owner_token = _register_user(
        client,
        email="owner-ing-jobs@example.com",
        name="Owner",
    )
    workspace = _create_workspace(
        client,
        owner_token,
        name="Ingestion Jobs WS",
        slug="ingestion-jobs-ws",
    )
    doc = _add_document(
        session,
        workspace_id=workspace["id"],
        uploaded_by=owner["id"],
        title="broken-runbook.md",
        status=DocumentStatus.FAILED,
    )
    ok_doc = _add_document(
        session,
        workspace_id=workspace["id"],
        uploaded_by=owner["id"],
        title="ok.md",
        status=DocumentStatus.INDEXED,
    )
    _add_ingestion_job(
        session,
        workspace_id=workspace["id"],
        document_id=doc.id,
        status=IngestionJobStatus.FAILED,
        error_message="extract failed: corrupt pdf",
    )
    _add_ingestion_job(
        session,
        workspace_id=workspace["id"],
        document_id=ok_doc.id,
        status=IngestionJobStatus.COMPLETED,
    )

    response = client.get(
        f"/workspaces/{workspace['id']}/admin/ingestion-jobs",
        params={"status": "failed"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert len(body["items"]) == 1
    item = body["items"][0]
    assert item["status"] == "failed"
    assert item["document_title"] == "broken-runbook.md"
    assert item["error_message"] == "extract failed: corrupt pdf"


def test_recent_questions_lists_user_messages_with_timestamps(
    admin_api_context,
) -> None:
    client, session = admin_api_context
    owner, owner_token = _register_user(
        client,
        email="owner-recent-q@example.com",
        name="Owner",
    )
    member, _member_token = _register_user(
        client,
        email="member-recent-q@example.com",
        name="Member Eng",
    )
    workspace = _create_workspace(
        client,
        owner_token,
        name="Recent Q WS",
        slug="recent-q-ws",
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
    _add_user_question(
        session,
        workspace_id=workspace["id"],
        user_id=member["id"],
        content="How do we restart the API?",
        created_at=now - timedelta(hours=2),
    )
    _add_user_question(
        session,
        workspace_id=workspace["id"],
        user_id=member["id"],
        content="Where is the staging kubeconfig?",
        created_at=now - timedelta(hours=1),
    )
    _add_user_question(
        session,
        workspace_id=workspace["id"],
        user_id=owner["id"],
        content="What failed last night?",
        created_at=now,
    )

    response = client.get(
        f"/workspaces/{workspace['id']}/admin/recent-questions",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 3
    assert body["page_size"] == 50
    previews = [item["question_preview"] for item in body["items"]]
    assert previews == [
        "What failed last night?",
        "Where is the staging kubeconfig?",
        "How do we restart the API?",
    ]
    assert all("assistant" not in item["question_preview"].lower() for item in body["items"])
    assert body["items"][0]["user_email"] == owner["email"]
    assert body["items"][1]["user_name"] == "Member Eng"


def test_failed_jobs_widget_counts_and_empty_state(admin_api_context) -> None:
    client, session = admin_api_context
    owner, owner_token = _register_user(
        client,
        email="owner-failed-widget@example.com",
        name="Owner",
    )
    workspace = _create_workspace(
        client,
        owner_token,
        name="Failed Widget WS",
        slug="failed-widget-ws",
    )

    empty = client.get(
        f"/workspaces/{workspace['id']}/admin/failed-jobs",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert empty.status_code == 200
    empty_body = empty.json()
    assert empty_body["failed_last_24h"] == 0
    assert empty_body["failed_last_7d"] == 0
    assert empty_body["empty_message"] == "No failed jobs."
    assert empty_body["items"] == []

    now = datetime.now(UTC)
    doc = _add_document(
        session,
        workspace_id=workspace["id"],
        uploaded_by=owner["id"],
        title="fail-a.md",
        status=DocumentStatus.FAILED,
    )
    doc_b = _add_document(
        session,
        workspace_id=workspace["id"],
        uploaded_by=owner["id"],
        title="fail-b.md",
        status=DocumentStatus.FAILED,
    )
    old_doc = _add_document(
        session,
        workspace_id=workspace["id"],
        uploaded_by=owner["id"],
        title="old-fail.md",
        status=DocumentStatus.FAILED,
    )
    _add_ingestion_job(
        session,
        workspace_id=workspace["id"],
        document_id=doc.id,
        status=IngestionJobStatus.FAILED,
        error_message="boom a",
        created_at=now - timedelta(hours=1),
    )
    _add_ingestion_job(
        session,
        workspace_id=workspace["id"],
        document_id=doc_b.id,
        status=IngestionJobStatus.FAILED,
        error_message="boom b",
        created_at=now - timedelta(hours=2),
    )
    _add_ingestion_job(
        session,
        workspace_id=workspace["id"],
        document_id=old_doc.id,
        status=IngestionJobStatus.FAILED,
        error_message="old boom",
        created_at=now - timedelta(days=3),
    )

    response = client.get(
        f"/workspaces/{workspace['id']}/admin/failed-jobs",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["failed_last_24h"] == 2
    assert body["failed_last_7d"] == 3
    assert body["empty_message"] is None
    assert len(body["items"]) == 3
    assert {item["document_title"] for item in body["items"]} == {
        "fail-a.md",
        "fail-b.md",
        "old-fail.md",
    }


@pytest.mark.parametrize(
    ("role", "path"),
    [
        ("viewer", "documents-overview"),
        ("member", "documents-overview"),
        ("viewer", "ingestion-jobs"),
        ("member", "ingestion-jobs"),
        ("viewer", "recent-questions"),
        ("member", "recent-questions"),
        ("viewer", "failed-jobs"),
        ("member", "failed-jobs"),
    ],
)
def test_viewer_and_member_forbidden_on_admin_dashboard(
    admin_api_context,
    role: str,
    path: str,
) -> None:
    client, _session = admin_api_context
    owner, owner_token = _register_user(
        client,
        email=f"owner-{role}-{path}@example.com",
        name="Owner",
    )
    other, other_token = _register_user(
        client,
        email=f"{role}-{path}@example.com",
        name=role.title(),
    )
    workspace = _create_workspace(
        client,
        owner_token,
        name=f"RBAC {role} {path}",
        slug=f"rbac-{role}-{path}"[:48],
    )
    invite = _invite_member(
        client,
        owner_token,
        workspace["id"],
        email=other["email"],
        role=role,
    )
    assert invite.status_code == 201

    response = client.get(
        f"/workspaces/{workspace['id']}/admin/{path}",
        headers={"Authorization": f"Bearer {other_token}"},
    )
    assert response.status_code == 403


def test_admin_role_can_access_dashboard_endpoints(admin_api_context) -> None:
    client, _session = admin_api_context
    owner, owner_token = _register_user(
        client,
        email="owner-admin-ok@example.com",
        name="Owner",
    )
    admin, admin_token = _register_user(
        client,
        email="admin-ok@example.com",
        name="Admin",
    )
    workspace = _create_workspace(
        client,
        owner_token,
        name="Admin OK WS",
        slug="admin-ok-ws",
    )
    invite = _invite_member(
        client,
        owner_token,
        workspace["id"],
        email=admin["email"],
        role="admin",
    )
    assert invite.status_code == 201

    for path in (
        "documents-overview",
        "ingestion-jobs",
        "recent-questions",
        "failed-jobs",
        "usage",
    ):
        response = client.get(
            f"/workspaces/{workspace['id']}/admin/{path}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200, path


def test_admin_dashboard_workspace_isolation(admin_api_context) -> None:
    client, session = admin_api_context
    owner_a, token_a = _register_user(
        client,
        email="owner-a-iso@example.com",
        name="Owner A",
    )
    owner_b, token_b = _register_user(
        client,
        email="owner-b-iso@example.com",
        name="Owner B",
    )
    workspace_a = _create_workspace(
        client,
        token_a,
        name="Iso A",
        slug="iso-a-admin",
    )
    workspace_b = _create_workspace(
        client,
        token_b,
        name="Iso B",
        slug="iso-b-admin",
    )
    doc_a = _add_document(
        session,
        workspace_id=workspace_a["id"],
        uploaded_by=owner_a["id"],
        title="only-a.md",
        status=DocumentStatus.INDEXED,
    )
    _add_ingestion_job(
        session,
        workspace_id=workspace_a["id"],
        document_id=doc_a.id,
        status=IngestionJobStatus.FAILED,
        error_message="a only",
    )
    _add_user_question(
        session,
        workspace_id=workspace_a["id"],
        user_id=owner_a["id"],
        content="secret question in A",
    )

    # Owner B must not see workspace A data via B's token on A's id → 403 (not member).
    forbidden = client.get(
        f"/workspaces/{workspace_a['id']}/admin/documents-overview",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert forbidden.status_code == 403

    # Owner B's own overview is empty / isolated.
    overview_b = client.get(
        f"/workspaces/{workspace_b['id']}/admin/documents-overview",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert overview_b.status_code == 200
    assert overview_b.json()["total"] == 0

    jobs_b = client.get(
        f"/workspaces/{workspace_b['id']}/admin/ingestion-jobs",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert jobs_b.status_code == 200
    assert jobs_b.json()["total"] == 0

    questions_b = client.get(
        f"/workspaces/{workspace_b['id']}/admin/recent-questions",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert questions_b.status_code == 200
    assert questions_b.json()["total"] == 0

    failed_b = client.get(
        f"/workspaces/{workspace_b['id']}/admin/failed-jobs",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert failed_b.status_code == 200
    assert failed_b.json()["failed_last_7d"] == 0
