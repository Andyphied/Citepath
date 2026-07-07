"""API tests for document upload."""

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

from app.infrastructure.config import reset_settings_cache
from app.infrastructure.db.session import reset_db_engine
from app.main import create_app

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


def test_member_upload_markdown_returns_201_uploaded(document_upload_context) -> None:
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

    assert response.status_code == 201
    body = response.json()
    assert body["title"] == "billing-api-runbook.md"
    assert body["status"] == "uploaded"
    assert body["file_type"] == "md"
    assert body["workspace_id"] == workspace["id"]
    assert body["uploaded_by"] == owner["id"]

    row = db_session.execute(
        text(
            """
            SELECT status, storage_key, workspace_id
            FROM documents
            WHERE id = :document_id
            """
        ),
        {"document_id": body["id"]},
    ).one()
    assert row.status == "uploaded"
    assert str(row.workspace_id) == workspace["id"]
    assert row.storage_key
    assert (storage_path / row.storage_key).read_bytes() == file_content


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
