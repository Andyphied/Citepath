"""API tests for ingestion job status."""

import importlib
from datetime import UTC, datetime
from pathlib import Path

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
    reason="Docker is required for ingestion job API tests",
)


@pytest.fixture(scope="module")
def postgres_url():
    """Start a pgvector-enabled Postgres container for ingestion job tests."""
    with PostgresContainer("pgvector/pgvector:pg16") as postgres:
        yield postgres.get_connection_url()


@pytest.fixture
def ingestion_job_context(postgres_url, minimal_env, monkeypatch, tmp_path):
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


def test_get_ingestion_job_returns_processing_status(
    ingestion_job_context,
) -> None:
    client, session = ingestion_job_context
    user, token = _register_user(
        client,
        email="job-processing@example.com",
        name="Processing User",
    )
    workspace = _create_workspace(
        client,
        token,
        name="Job Processing Workspace",
        slug="ing-job-processing",
    )

    document_repo = DocumentRepository(session)
    document = document_repo.create(
        workspace_id=workspace["id"],
        uploaded_by=user["id"],
        title="processing-runbook.md",
        source_type="general",
        file_type="md",
        storage_key=f"{workspace['id']}/doc/processing-runbook.md",
        status=DocumentStatus.PROCESSING,
    )

    job_repo = IngestionJobRepository(session)
    job = job_repo.create(
        workspace_id=workspace["id"],
        document_id=document.id,
        status=IngestionJobStatus.PROCESSING,
    )
    started_at = datetime(2026, 7, 12, 12, 0, tzinfo=UTC)
    job_repo.update(
        job=job,
        attempt_count=1,
        started_at=started_at,
    )

    response = client.get(
        f"/workspaces/{workspace['id']}/ingestion-jobs/{job.id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "processing"
    assert body["document_id"] == str(document.id)
    assert body["workspace_id"] == workspace["id"]
    assert body["attempt_count"] == 1
    assert body["started_at"] is not None
    assert body["completed_at"] is None
    assert body["error_message"] is None


def test_get_ingestion_job_returns_completed_and_document_is_indexed(
    ingestion_job_context,
) -> None:
    client, session = ingestion_job_context
    user, token = _register_user(
        client,
        email="job-completed@example.com",
        name="Completed User",
    )
    workspace = _create_workspace(
        client,
        token,
        name="Job Completed Workspace",
        slug="ing-job-completed",
    )

    document_repo = DocumentRepository(session)
    document = document_repo.create(
        workspace_id=workspace["id"],
        uploaded_by=user["id"],
        title="completed-runbook.md",
        source_type="general",
        file_type="md",
        storage_key=f"{workspace['id']}/doc/completed-runbook.md",
        status=DocumentStatus.INDEXED,
    )

    job_repo = IngestionJobRepository(session)
    job = job_repo.create(
        workspace_id=workspace["id"],
        document_id=document.id,
        status=IngestionJobStatus.COMPLETED,
    )
    completed_at = datetime(2026, 7, 12, 13, 0, tzinfo=UTC)
    job_repo.update(
        job=job,
        started_at=datetime(2026, 7, 12, 12, 0, tzinfo=UTC),
        completed_at=completed_at,
    )

    job_response = client.get(
        f"/workspaces/{workspace['id']}/ingestion-jobs/{job.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    detail_response = client.get(
        f"/workspaces/{workspace['id']}/documents/{document.id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert job_response.status_code == 200
    job_body = job_response.json()
    assert job_body["status"] == "completed"
    assert job_body["completed_at"] is not None
    assert job_body["error_message"] is None

    assert detail_response.status_code == 200
    detail_body = detail_response.json()
    assert detail_body["document"]["status"] == "indexed"
    assert detail_body["latest_job"]["id"] == job_body["id"]
    assert detail_body["latest_job"]["status"] == "completed"


def test_get_ingestion_job_returns_failed_with_sanitized_error(
    ingestion_job_context,
) -> None:
    client, session = ingestion_job_context
    user, token = _register_user(
        client,
        email="job-failed@example.com",
        name="Failed User",
    )
    workspace = _create_workspace(
        client,
        token,
        name="Job Failed Workspace",
        slug="ing-job-failed",
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
        completed_at=datetime(2026, 7, 12, 14, 0, tzinfo=UTC),
    )

    response = client.get(
        f"/workspaces/{workspace['id']}/ingestion-jobs/{job.id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "failed"
    assert body["error_message"] == "Stored file could not be read"
    assert "failed-runbook.pdf" not in body["error_message"]


def test_get_ingestion_job_returns_404_for_cross_workspace_job(
    ingestion_job_context,
) -> None:
    client, session = ingestion_job_context
    user_a, token_a = _register_user(
        client,
        email="job-owner-a@example.com",
        name="Owner A",
    )
    _user_b, token_b = _register_user(
        client,
        email="job-owner-b@example.com",
        name="Owner B",
    )
    workspace_a = _create_workspace(
        client,
        token_a,
        name="Workspace A",
        slug="ing-job-workspace-a",
    )
    workspace_b = _create_workspace(
        client,
        token_b,
        name="Workspace B",
        slug="ing-job-workspace-b",
    )

    document_repo = DocumentRepository(session)
    document = document_repo.create(
        workspace_id=workspace_a["id"],
        uploaded_by=user_a["id"],
        title="private.md",
        source_type="general",
        file_type="md",
        storage_key=f"{workspace_a['id']}/doc/private.md",
        status=DocumentStatus.PROCESSING,
    )

    job_repo = IngestionJobRepository(session)
    job = job_repo.create(
        workspace_id=workspace_a["id"],
        document_id=document.id,
        status=IngestionJobStatus.PROCESSING,
    )

    response = client.get(
        f"/workspaces/{workspace_b['id']}/ingestion-jobs/{job.id}",
        headers={"Authorization": f"Bearer {token_b}"},
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"
