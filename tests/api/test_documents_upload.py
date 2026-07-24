"""API tests for document upload."""

import importlib
import io
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

from sqlalchemy import select

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
    reason="Docker is required for document upload API tests",
)


@pytest.fixture(scope="module")
def postgres_url():
    """Start a pgvector-enabled Postgres container for document upload tests."""
    with PostgresContainer("pgvector/pgvector:pg16") as postgres:
        yield postgres.get_connection_url()


@pytest.fixture
def document_upload_context(postgres_url, minimal_env, monkeypatch, tmp_path):
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


def test_member_upload_markdown_returns_202_with_ingestion_job(
    document_upload_context,
) -> None:
    client, db_session, storage_path = document_upload_context
    owner, owner_token = _register_user(
        client,
        email="doc-owner@example.com",
        name="Document Owner",
    )
    workspace = _create_workspace(
        client,
        owner_token,
        name="Docs Workspace",
        slug="doc-upload-workspace",
    )

    file_content = b"# Billing API Runbook\n\nRestart the service."
    response = client.post(
        f"/workspaces/{workspace['id']}/documents",
        headers={"Authorization": f"Bearer {owner_token}"},
        files={"file": ("billing-api-runbook.md", io.BytesIO(file_content), "text/markdown")},
    )

    assert response.status_code == 202
    body = response.json()
    document = body["document"]
    ingestion_job = body["ingestion_job"]
    assert document["title"] == "billing-api-runbook.md"
    # Eager Celery may advance status to processing/failed before response returns.
    assert document["status"] in ("uploaded", "processing", "failed")
    assert document["file_type"] == "md"
    assert document["workspace_id"] == workspace["id"]
    assert document["uploaded_by"] == owner["id"]
    assert ingestion_job["document_id"] == document["id"]
    assert ingestion_job["workspace_id"] == workspace["id"]
    assert ingestion_job["status"] in ("pending", "processing", "failed")

    db_session.expire_all()
    audit_row = db_session.scalar(
        select(AuditLog).where(
            AuditLog.workspace_id == workspace["id"],
            AuditLog.event_type == "document.uploaded",
        )
    )
    assert audit_row is not None
    assert str(audit_row.actor_user_id) == owner["id"]
    assert audit_row.metadata_["document_id"] == document["id"]
    assert audit_row.metadata_["title"] == "billing-api-runbook.md"
    assert "content" not in (audit_row.metadata_ or {})
    assert "file_content" not in (audit_row.metadata_ or {})

    doc_row = db_session.execute(
        text(
            """
            SELECT status, storage_key, workspace_id
            FROM documents
            WHERE id = :document_id
            """
        ),
        {"document_id": document["id"]},
    ).one()
    assert doc_row.status in ("uploaded", "processing", "failed")
    assert str(doc_row.workspace_id) == workspace["id"]
    assert doc_row.storage_key
    assert (storage_path / doc_row.storage_key).read_bytes() == file_content

    job_row = db_session.execute(
        text(
            """
            SELECT status, document_id, workspace_id
            FROM ingestion_jobs
            WHERE id = :job_id
            """
        ),
        {"job_id": ingestion_job["id"]},
    ).one()
    assert job_row.status in ("pending", "processing", "failed")
    assert str(job_row.document_id) == document["id"]
    assert str(job_row.workspace_id) == workspace["id"]


def test_viewer_upload_returns_403(document_upload_context) -> None:
    client, _db_session, _storage_path = document_upload_context
    _owner, owner_token = _register_user(
        client,
        email="doc-viewer-owner@example.com",
        name="Owner",
    )
    viewer, viewer_token = _register_user(
        client,
        email="doc-viewer@example.com",
        name="Viewer",
    )
    workspace = _create_workspace(
        client,
        owner_token,
        name="Viewer Workspace",
        slug="doc-viewer-workspace",
    )
    _invite_member(
        client,
        owner_token,
        workspace["id"],
        email=viewer["email"],
        role="viewer",
    )

    response = client.post(
        f"/workspaces/{workspace['id']}/documents",
        headers={"Authorization": f"Bearer {viewer_token}"},
        files={"file": ("notes.md", io.BytesIO(b"# Notes"), "text/markdown")},
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "forbidden"


def test_unsupported_exe_upload_returns_422(document_upload_context) -> None:
    client, _db_session, _storage_path = document_upload_context
    _owner, owner_token = _register_user(
        client,
        email="doc-exe-owner@example.com",
        name="Owner",
    )
    workspace = _create_workspace(
        client,
        owner_token,
        name="Exe Workspace",
        slug="doc-exe-workspace",
    )

    response = client.post(
        f"/workspaces/{workspace['id']}/documents",
        headers={"Authorization": f"Bearer {owner_token}"},
        files={"file": ("malware.exe", io.BytesIO(b"MZ"), "application/octet-stream")},
    )

    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "unsupported_file_type"
    assert body["error"]["details"]["extension"] == "exe"
    assert body["error"]["details"]["allowed_types"] == ["json", "md", "pdf", "txt"]


def test_unsupported_docx_upload_returns_422(document_upload_context) -> None:
    client, db_session, storage_path = document_upload_context
    _owner, owner_token = _register_user(
        client,
        email="doc-docx-owner@example.com",
        name="Owner",
    )
    workspace = _create_workspace(
        client,
        owner_token,
        name="Docx Workspace",
        slug="doc-docx-workspace",
    )

    response = client.post(
        f"/workspaces/{workspace['id']}/documents",
        headers={"Authorization": f"Bearer {owner_token}"},
        files={
            "file": (
                "report.docx",
                io.BytesIO(b"PK\x03\x04"),
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
    )

    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "unsupported_file_type"
    assert body["error"]["details"]["extension"] == "docx"
    assert body["error"]["details"]["allowed_types"] == ["json", "md", "pdf", "txt"]

    doc_count = db_session.execute(text("SELECT COUNT(*) FROM documents")).scalar()
    assert doc_count == 0
    assert list(storage_path.rglob("*")) == []


def test_empty_file_upload_returns_422(document_upload_context) -> None:
    client, db_session, storage_path = document_upload_context
    _owner, owner_token = _register_user(
        client,
        email="doc-empty-owner@example.com",
        name="Owner",
    )
    workspace = _create_workspace(
        client,
        owner_token,
        name="Empty Workspace",
        slug="doc-empty-workspace",
    )

    response = client.post(
        f"/workspaces/{workspace['id']}/documents",
        headers={"Authorization": f"Bearer {owner_token}"},
        files={"file": ("empty.md", io.BytesIO(b""), "text/markdown")},
    )

    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "empty_file"

    doc_count = db_session.execute(text("SELECT COUNT(*) FROM documents")).scalar()
    assert doc_count == 0
    assert list(storage_path.rglob("*")) == []


def test_fake_pdf_upload_returns_422(document_upload_context) -> None:
    client, db_session, storage_path = document_upload_context
    _owner, owner_token = _register_user(
        client,
        email="doc-fake-pdf-owner@example.com",
        name="Owner",
    )
    workspace = _create_workspace(
        client,
        owner_token,
        name="Fake PDF Workspace",
        slug="doc-fake-pdf-workspace",
    )

    response = client.post(
        f"/workspaces/{workspace['id']}/documents",
        headers={"Authorization": f"Bearer {owner_token}"},
        files={"file": ("fake.pdf", io.BytesIO(b"not a pdf"), "application/pdf")},
    )

    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "invalid_file_content"
    assert body["error"]["details"]["file_type"] == "pdf"
    assert body["error"]["details"]["reason"] == "invalid_pdf_signature"

    doc_count = db_session.execute(text("SELECT COUNT(*) FROM documents")).scalar()
    assert doc_count == 0
    assert list(storage_path.rglob("*")) == []
