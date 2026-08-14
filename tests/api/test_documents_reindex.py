"""API tests for document re-index."""

import importlib
from pathlib import Path
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select, text
from sqlalchemy.orm import sessionmaker

try:
    from testcontainers.postgres import PostgresContainer
except ImportError:  # pragma: no cover - optional dev dependency
    PostgresContainer = None

from app.infrastructure.config import reset_settings_cache
from app.infrastructure.db.enums import DocumentStatus, IngestionJobStatus
from app.infrastructure.db.session import reset_db_engine
from app.main import create_app
from app.modules.audit.models import AuditLog
from app.modules.documents.models import Document
from app.modules.documents.repository import DocumentRepository
from app.modules.ingestion.chunker import EmbeddedChunk
from app.modules.ingestion.job_repository import IngestionJobRepository
from app.modules.ingestion.models import DocumentChunk, IngestionJob
from app.modules.ingestion.repository import IngestionRepository

REPO_ROOT = Path(__file__).resolve().parents[2]
EMBEDDING_DIMENSIONS = 1536


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
    reason="Docker is required for document reindex API tests",
)


@pytest.fixture(scope="module")
def postgres_url():
    """Start a pgvector-enabled Postgres container for document reindex tests."""
    with PostgresContainer("pgvector/pgvector:pg16") as postgres:
        yield postgres.get_connection_url()


@pytest.fixture
def document_reindex_context(postgres_url, minimal_env, monkeypatch, tmp_path):
    """Migrated database, API client, storage path, and session with cleanup."""
    storage_path = tmp_path / "uploads"
    storage_path.mkdir()
    monkeypatch.chdir(REPO_ROOT)
    monkeypatch.setenv("DATABASE_URL", postgres_url)
    monkeypatch.setenv("STORAGE_PATH", str(storage_path))
    reset_settings_cache()
    reset_db_engine()

    import app.infrastructure.celery_app as celery_app_module

    importlib.reload(celery_app_module)
    celery_app_module.celery_app.conf.task_always_eager = True
    celery_app_module.celery_app.conf.task_eager_propagates = True
    importlib.reload(importlib.import_module("app.modules.ingestion.tasks"))

    alembic_cfg = Config(str(REPO_ROOT / "alembic.ini"))
    command.upgrade(alembic_cfg, "head")

    engine = create_engine(postgres_url)
    session_factory = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    session = session_factory()

    with TestClient(create_app()) as test_client:
        yield test_client, session, storage_path

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
    owner_token: str,
    workspace_id: str,
    *,
    email: str,
    role: str,
) -> None:
    response = client.post(
        f"/workspaces/{workspace_id}/members",
        json={"email": email, "role": role},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert response.status_code == 201


def _embedding(*, primary: float = 0.5) -> list[float]:
    vector = [0.0] * EMBEDDING_DIMENSIONS
    vector[0] = primary
    return vector


def _seed_indexed_document(
    session,
    *,
    workspace_id: str,
    uploaded_by: str,
    storage_path: Path,
    title: str = "indexed-runbook.md",
) -> tuple[Document, str]:
    document_id = uuid4()
    storage_key = f"{workspace_id}/{document_id}/{title}"
    storage_file = storage_path / storage_key
    storage_file.parent.mkdir(parents=True, exist_ok=True)
    storage_file.write_bytes(b"# Indexed content\n\nRe-index me.")

    document_repo = DocumentRepository(session)
    document = document_repo.create(
        id=document_id,
        workspace_id=workspace_id,
        uploaded_by=uploaded_by,
        title=title,
        source_type="general",
        file_type="md",
        storage_key=storage_key,
        status=DocumentStatus.INDEXED,
    )

    ingestion_repo = IngestionRepository(session)
    for index in range(3):
        ingestion_repo.create_chunk(
            workspace_id=workspace_id,
            document_id=document.id,
            chunk_index=index,
            content=f"old chunk {index}",
            embedding=_embedding(primary=float(index)),
            embedding_model="text-embedding-3-small",
        )

    job_repo = IngestionJobRepository(session)
    job_repo.create(
        workspace_id=workspace_id,
        document_id=document.id,
        status=IngestionJobStatus.COMPLETED,
    )

    return document, storage_key


def test_reindex_indexed_document_returns_202_and_replaces_chunks(
    document_reindex_context,
) -> None:
    client, session, storage_path = document_reindex_context
    user, token = _register_user(
        client,
        email="reindex-member@example.com",
        name="Reindex Member",
    )
    workspace = _create_workspace(
        client,
        token,
        name="Reindex Workspace",
        slug="doc-reindex-workspace",
    )

    document, _storage_key = _seed_indexed_document(
        session,
        workspace_id=workspace["id"],
        uploaded_by=user["id"],
        storage_path=storage_path,
    )
    old_job_id = session.scalar(
        select(IngestionJob.id)
        .where(IngestionJob.document_id == document.id)
        .order_by(IngestionJob.created_at.desc())
        .limit(1)
    )

    embedded_chunk = EmbeddedChunk(
        content="new chunk 0",
        chunk_index=0,
        metadata={},
        embedding=_embedding(primary=0.9),
        embedding_model="text-embedding-3-small",
    )
    content_chunk = MagicMock(chunk_index=0, content="new chunk 0")

    with patch(
        "app.modules.ingestion.tasks.create_embedding_provider",
    ), patch(
        "app.modules.ingestion.tasks.chunk_extraction_result",
        return_value=[content_chunk],
    ), patch(
        "app.modules.ingestion.tasks.embed_content_chunks",
        return_value=[embedded_chunk],
    ):
        response = client.post(
            f"/workspaces/{workspace['id']}/documents/{document.id}/reindex",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 202
    body = response.json()
    assert body["document"]["id"] == str(document.id)
    assert body["document"]["status"] in ("processing", "indexed")
    assert body["ingestion_job"]["document_id"] == str(document.id)
    assert body["ingestion_job"]["status"] in ("pending", "processing", "completed")
    assert body["ingestion_job"]["id"] != str(old_job_id)

    session.expire_all()
    document_row = session.get(Document, document.id)
    assert document_row is not None
    assert document_row.status == DocumentStatus.INDEXED

    latest_job = session.scalar(
        select(IngestionJob)
        .where(IngestionJob.document_id == document.id)
        .order_by(IngestionJob.created_at.desc())
        .limit(1)
    )
    assert latest_job is not None
    assert latest_job.status == IngestionJobStatus.COMPLETED

    session.expire_all()
    chunk_count = session.scalar(
        select(func.count())
        .select_from(DocumentChunk)
        .where(DocumentChunk.document_id == document.id)
    )
    assert chunk_count == 1

    audit_row = session.scalar(
        select(AuditLog).where(
            AuditLog.workspace_id == workspace["id"],
            AuditLog.event_type == "document.reindex_requested",
        )
    )
    assert audit_row is not None
    assert str(audit_row.actor_user_id) == user["id"]
    assert audit_row.metadata_["document_id"] == str(document.id)


def test_reindex_with_pending_job_returns_409(document_reindex_context) -> None:
    client, session, storage_path = document_reindex_context
    user, token = _register_user(
        client,
        email="reindex-conflict@example.com",
        name="Conflict User",
    )
    workspace = _create_workspace(
        client,
        token,
        name="Reindex Conflict Workspace",
        slug="doc-reindex-conflict",
    )

    document, _storage_key = _seed_indexed_document(
        session,
        workspace_id=workspace["id"],
        uploaded_by=user["id"],
        storage_path=storage_path,
    )

    job_repo = IngestionJobRepository(session)
    job_repo.create(
        workspace_id=workspace["id"],
        document_id=document.id,
        status=IngestionJobStatus.PENDING,
    )

    response = client.post(
        f"/workspaces/{workspace['id']}/documents/{document.id}/reindex",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "reindex_in_progress"


def test_viewer_reindex_returns_403(document_reindex_context) -> None:
    client, session, storage_path = document_reindex_context
    owner, owner_token = _register_user(
        client,
        email="reindex-viewer-owner@example.com",
        name="Owner",
    )
    viewer, viewer_token = _register_user(
        client,
        email="reindex-viewer@example.com",
        name="Viewer",
    )
    workspace = _create_workspace(
        client,
        owner_token,
        name="Reindex Viewer Workspace",
        slug="doc-reindex-viewer",
    )
    _invite_member(
        client,
        owner_token,
        workspace["id"],
        email=viewer["email"],
        role="viewer",
    )

    document, _storage_key = _seed_indexed_document(
        session,
        workspace_id=workspace["id"],
        uploaded_by=owner["id"],
        storage_path=storage_path,
    )

    response = client.post(
        f"/workspaces/{workspace['id']}/documents/{document.id}/reindex",
        headers={"Authorization": f"Bearer {viewer_token}"},
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "forbidden"


def test_reindex_document_in_other_workspace_returns_404(
    document_reindex_context,
) -> None:
    client, session, storage_path = document_reindex_context
    user_a, token_a = _register_user(
        client,
        email="reindex-iso-a@example.com",
        name="User A",
    )
    user_b, token_b = _register_user(
        client,
        email="reindex-iso-b@example.com",
        name="User B",
    )
    workspace_a = _create_workspace(
        client,
        token_a,
        name="Workspace A",
        slug="doc-reindex-iso-a",
    )
    workspace_b = _create_workspace(
        client,
        token_b,
        name="Workspace B",
        slug="doc-reindex-iso-b",
    )

    document_b, _storage_key = _seed_indexed_document(
        session,
        workspace_id=workspace_b["id"],
        uploaded_by=user_b["id"],
        storage_path=storage_path,
        title="foreign-doc.md",
    )

    response = client.post(
        f"/workspaces/{workspace_a['id']}/documents/{document_b.id}/reindex",
        headers={"Authorization": f"Bearer {token_a}"},
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"
    session.expire_all()
    assert session.get(Document, document_b.id) is not None
