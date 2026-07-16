"""API tests for document status display and worker-driven transitions."""

import importlib
import io
from pathlib import Path
from unittest.mock import MagicMock, patch

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
from app.infrastructure.db.enums import DocumentStatus
from app.infrastructure.db.session import reset_db_engine
from app.main import create_app
from app.modules.ingestion.chunker import EmbeddedChunk
from app.modules.ingestion.embeddings import EmbeddingError

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
    reason="Docker is required for document status API tests",
)


@pytest.fixture(scope="module")
def postgres_url():
    """Start a pgvector-enabled Postgres container for document status tests."""
    with PostgresContainer("pgvector/pgvector:pg16") as postgres:
        yield postgres.get_connection_url()


@pytest.fixture
def document_status_context(postgres_url, minimal_env, monkeypatch, tmp_path):
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


def _embedding(*, primary: float = 0.5) -> list[float]:
    vector = [0.0] * EMBEDDING_DIMENSIONS
    vector[0] = primary
    return vector


def test_upload_ingestion_success_exposes_indexed_status_labels(
    document_status_context,
) -> None:
    client, session, _storage_path = document_status_context
    _user, token = _register_user(
        client,
        email="status-indexed@example.com",
        name="Status Indexed User",
    )
    workspace = _create_workspace(
        client,
        token,
        name="Status Indexed Workspace",
        slug="doc-status-indexed",
    )

    embedded_chunk = EmbeddedChunk(
        content="chunk 0",
        chunk_index=0,
        metadata={},
        embedding=_embedding(primary=0.9),
        embedding_model="text-embedding-3-small",
    )
    content_chunk = MagicMock(chunk_index=0, content="chunk 0")

    with patch(
        "app.modules.ingestion.tasks.create_embedding_provider",
    ), patch(
        "app.modules.ingestion.tasks.chunk_extraction_result",
        return_value=[content_chunk],
    ), patch(
        "app.modules.ingestion.tasks.embed_content_chunks",
        return_value=[embedded_chunk],
    ):
        upload_response = client.post(
            f"/workspaces/{workspace['id']}/documents",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": ("runbook.md", io.BytesIO(b"# Runbook\n"), "text/markdown")},
        )

    assert upload_response.status_code == 202
    upload_body = upload_response.json()
    document = upload_body["document"]
    assert document["status_label"] in ("Uploaded", "Processing", "Indexed")
    assert "status_label" in document

    session.expire_all()
    document_row = session.execute(
        text("SELECT status FROM documents WHERE id = :document_id"),
        {"document_id": document["id"]},
    ).one()
    assert document_row.status == DocumentStatus.INDEXED.value

    list_response = client.get(
        f"/workspaces/{workspace['id']}/documents",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert list_response.status_code == 200
    list_item = list_response.json()["items"][0]
    assert list_item["status"] == "indexed"
    assert list_item["status_label"] == "Indexed"

    detail_response = client.get(
        f"/workspaces/{workspace['id']}/documents/{document['id']}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert detail_response.status_code == 200
    detail_document = detail_response.json()["document"]
    assert detail_document["status"] == "indexed"
    assert detail_document["status_label"] == "Indexed"


def test_upload_ingestion_failure_exposes_failed_status_labels(
    document_status_context,
) -> None:
    client, session, _storage_path = document_status_context
    _user, token = _register_user(
        client,
        email="status-failed@example.com",
        name="Status Failed User",
    )
    workspace = _create_workspace(
        client,
        token,
        name="Status Failed Workspace",
        slug="doc-status-failed",
    )

    content_chunk = MagicMock(chunk_index=0, content="chunk 0")

    with patch(
        "app.modules.ingestion.tasks.create_embedding_provider",
    ), patch(
        "app.modules.ingestion.tasks.chunk_extraction_result",
        return_value=[content_chunk],
    ), patch(
        "app.modules.ingestion.tasks.embed_content_chunks",
        return_value=EmbeddingError(message="provider timeout"),
    ):
        upload_response = client.post(
            f"/workspaces/{workspace['id']}/documents",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": ("broken.md", io.BytesIO(b"# Broken\n"), "text/markdown")},
        )

    assert upload_response.status_code == 202
    upload_body = upload_response.json()
    document = upload_body["document"]
    assert "status_label" in document

    session.expire_all()
    document_row = session.execute(
        text("SELECT status FROM documents WHERE id = :document_id"),
        {"document_id": document["id"]},
    ).one()
    assert document_row.status == DocumentStatus.FAILED.value

    detail_response = client.get(
        f"/workspaces/{workspace['id']}/documents/{document['id']}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert detail_response.status_code == 200
    detail_body = detail_response.json()
    assert detail_body["document"]["status"] == "failed"
    assert detail_body["document"]["status_label"] == "Failed"
    assert detail_body["error_message"] is not None


def test_upload_transitions_through_processing_before_terminal_state(
    document_status_context,
) -> None:
    """Acceptance: worker sets processing when ingestion starts."""
    client, session, _storage_path = document_status_context
    _user, token = _register_user(
        client,
        email="status-processing@example.com",
        name="Status Processing User",
    )
    workspace = _create_workspace(
        client,
        token,
        name="Status Processing Workspace",
        slug="doc-status-processing",
    )

    observed_statuses: list[str] = []
    original_update_status = None

    from app.modules.documents import repository as document_repository_module

    original_update_status = document_repository_module.DocumentRepository.update_status

    def capture_update_status(self, *, document, status):
        observed_statuses.append(status.value)
        return original_update_status(self, document=document, status=status)

    content_chunk = MagicMock(chunk_index=0, content="chunk 0")
    embedded_chunk = EmbeddedChunk(
        content="chunk 0",
        chunk_index=0,
        metadata={},
        embedding=_embedding(primary=0.9),
        embedding_model="text-embedding-3-small",
    )

    with patch.object(
        document_repository_module.DocumentRepository,
        "update_status",
        capture_update_status,
    ), patch(
        "app.modules.ingestion.tasks.create_embedding_provider",
    ), patch(
        "app.modules.ingestion.tasks.chunk_extraction_result",
        return_value=[content_chunk],
    ), patch(
        "app.modules.ingestion.tasks.embed_content_chunks",
        return_value=[embedded_chunk],
    ):
        upload_response = client.post(
            f"/workspaces/{workspace['id']}/documents",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": ("processing.md", io.BytesIO(b"# Processing\n"), "text/markdown")},
        )

    assert upload_response.status_code == 202
    assert "processing" in observed_statuses
    assert observed_statuses[-1] == "indexed"

    document_id = upload_response.json()["document"]["id"]
    session.expire_all()
    document_row = session.execute(
        text("SELECT status FROM documents WHERE id = :document_id"),
        {"document_id": document_id},
    ).one()
    assert document_row.status == DocumentStatus.INDEXED.value
