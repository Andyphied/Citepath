"""API tests for document detail."""

import importlib
from pathlib import Path
from uuid import uuid4

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
from app.infrastructure.db.enums import DocumentStatus, IngestionJobStatus
from app.infrastructure.db.session import reset_db_engine
from app.main import create_app
from app.modules.documents.repository import DocumentRepository
from app.modules.ingestion.job_repository import IngestionJobRepository
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
    reason="Docker is required for document detail API tests",
)


@pytest.fixture(scope="module")
def postgres_url():
    """Start a pgvector-enabled Postgres container for document detail tests."""
    with PostgresContainer("pgvector/pgvector:pg16") as postgres:
        yield postgres.get_connection_url()


@pytest.fixture
def document_detail_context(postgres_url, minimal_env, monkeypatch, tmp_path):
    """Migrated database, API client, and session with cleanup."""
    storage_path = tmp_path / "uploads"
    storage_path.mkdir()
    monkeypatch.chdir(REPO_ROOT)
    monkeypatch.setenv("DATABASE_URL", postgres_url)
    monkeypatch.setenv("STORAGE_PATH", str(storage_path))
    reset_settings_cache()
    reset_db_engine()

    import app.infrastructure.celery_app as celery_app_module

    importlib.reload(celery_app_module)

    alembic_cfg = Config(str(REPO_ROOT / "alembic.ini"))
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


def _embedding(*, primary: float = 0.5) -> list[float]:
    vector = [0.0] * EMBEDDING_DIMENSIONS
    vector[0] = primary
    return vector


def test_get_document_detail_returns_indexed_document_with_chunk_count(
    document_detail_context,
) -> None:
    client, session = document_detail_context
    user, token = _register_user(
        client,
        email="detail-indexed@example.com",
        name="Indexed User",
    )
    workspace = _create_workspace(
        client,
        token,
        name="Detail Indexed Workspace",
        slug="doc-detail-indexed",
    )

    document_repo = DocumentRepository(session)
    document = document_repo.create(
        workspace_id=workspace["id"],
        uploaded_by=user["id"],
        title="indexed-runbook.md",
        source_type="general",
        file_type="md",
        storage_key=f"{workspace['id']}/doc/indexed-runbook.md",
        status=DocumentStatus.INDEXED,
    )

    ingestion_repo = IngestionRepository(session)
    for index in range(3):
        ingestion_repo.create_chunk(
            workspace_id=workspace["id"],
            document_id=document.id,
            chunk_index=index,
            content=f"chunk {index}",
            embedding=_embedding(primary=float(index)),
            embedding_model="text-embedding-3-small",
        )

    job_repo = IngestionJobRepository(session)
    job_repo.create(
        workspace_id=workspace["id"],
        document_id=document.id,
        status=IngestionJobStatus.COMPLETED,
    )

    response = client.get(
        f"/workspaces/{workspace['id']}/documents/{document.id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["document"]["status"] == "indexed"
    assert body["chunk_count"] == 3
    assert body["error_message"] is None
    assert body["latest_job"] is not None
    assert body["latest_job"]["status"] == "completed"
    assert "storage_key" not in body["document"]


def test_get_document_detail_returns_failed_document_with_error_message(
    document_detail_context,
) -> None:
    client, session = document_detail_context
    user, token = _register_user(
        client,
        email="detail-failed@example.com",
        name="Failed User",
    )
    workspace = _create_workspace(
        client,
        token,
        name="Detail Failed Workspace",
        slug="doc-detail-failed",
    )

    document_repo = DocumentRepository(session)
    document = document_repo.create(
        workspace_id=workspace["id"],
        uploaded_by=user["id"],
        title="failed-runbook.pdf",
        source_type="general",
        file_type="pdf",
        storage_key=f"{workspace['id']}/doc/failed-runbook.pdf",
        status=DocumentStatus.FAILED,
    )

    job_repo = IngestionJobRepository(session)
    job = job_repo.create(
        workspace_id=workspace["id"],
        document_id=document.id,
        status=IngestionJobStatus.FAILED,
    )
    job_repo.update(
        job=job,
        error_message=f"Storage object not found: {workspace['id']}/{document.id}/failed-runbook.pdf",
    )

    response = client.get(
        f"/workspaces/{workspace['id']}/documents/{document.id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["document"]["status"] == "failed"
    assert body["error_message"] == "Stored file could not be read"
    assert body["latest_job"]["error_message"] == "Stored file could not be read"
    assert "failed-runbook.pdf" not in body["error_message"]
    assert body["chunk_count"] is None


def test_get_document_detail_returns_failed_document_with_safe_error_message(
    document_detail_context,
) -> None:
    client, session = document_detail_context
    user, token = _register_user(
        client,
        email="detail-failed-safe@example.com",
        name="Failed Safe User",
    )
    workspace = _create_workspace(
        client,
        token,
        name="Detail Failed Safe Workspace",
        slug="doc-detail-failed-safe",
    )

    document_repo = DocumentRepository(session)
    document = document_repo.create(
        workspace_id=workspace["id"],
        uploaded_by=user["id"],
        title="failed-runbook.pdf",
        source_type="general",
        file_type="pdf",
        storage_key=f"{workspace['id']}/doc/failed-runbook.pdf",
        status=DocumentStatus.FAILED,
    )

    job_repo = IngestionJobRepository(session)
    job = job_repo.create(
        workspace_id=workspace["id"],
        document_id=document.id,
        status=IngestionJobStatus.FAILED,
    )
    job_repo.update(
        job=job,
        error_message="PDF contains no pages",
    )

    response = client.get(
        f"/workspaces/{workspace['id']}/documents/{document.id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["error_message"] == "PDF contains no pages"


def test_get_document_detail_returns_404_for_missing_document(
    document_detail_context,
) -> None:
    client, _session = document_detail_context
    _user, token = _register_user(
        client,
        email="detail-missing@example.com",
        name="Missing User",
    )
    workspace = _create_workspace(
        client,
        token,
        name="Detail Missing Workspace",
        slug="doc-detail-missing",
    )

    response = client.get(
        f"/workspaces/{workspace['id']}/documents/{uuid4()}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_get_document_detail_returns_404_for_cross_workspace_document(
    document_detail_context,
) -> None:
    client, session = document_detail_context
    user_a, token_a = _register_user(
        client,
        email="detail-owner-a@example.com",
        name="Owner A",
    )
    _user_b, token_b = _register_user(
        client,
        email="detail-owner-b@example.com",
        name="Owner B",
    )
    workspace_a = _create_workspace(
        client,
        token_a,
        name="Workspace A",
        slug="doc-detail-workspace-a",
    )
    workspace_b = _create_workspace(
        client,
        token_b,
        name="Workspace B",
        slug="doc-detail-workspace-b",
    )

    document_repo = DocumentRepository(session)
    document = document_repo.create(
        workspace_id=workspace_a["id"],
        uploaded_by=user_a["id"],
        title="private.md",
        source_type="general",
        file_type="md",
        storage_key=f"{workspace_a['id']}/doc/private.md",
        status=DocumentStatus.INDEXED,
    )

    response = client.get(
        f"/workspaces/{workspace_b['id']}/documents/{document.id}",
        headers={"Authorization": f"Bearer {token_b}"},
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"
