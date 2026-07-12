"""API tests for document list."""

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
    reason="Docker is required for document list API tests",
)


@pytest.fixture(scope="module")
def postgres_url():
    """Start a pgvector-enabled Postgres container for document list tests."""
    with PostgresContainer("pgvector/pgvector:pg16") as postgres:
        yield postgres.get_connection_url()


@pytest.fixture
def document_list_context(postgres_url, minimal_env, monkeypatch, tmp_path):
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


def _upload_document(
    client: TestClient,
    token: str,
    workspace_id: str,
    *,
    filename: str,
    content: bytes,
) -> dict:
    response = client.post(
        f"/workspaces/{workspace_id}/documents",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": (filename, io.BytesIO(content), "text/markdown")},
    )
    assert response.status_code == 202
    return response.json()["document"]


def test_list_documents_returns_all_workspace_documents(document_list_context) -> None:
    client, _session = document_list_context
    _owner, owner_token = _register_user(
        client,
        email="list-owner@example.com",
        name="List Owner",
    )
    workspace = _create_workspace(
        client,
        owner_token,
        name="List Workspace",
        slug="doc-list-workspace",
    )

    uploaded_ids = []
    for index in range(5):
        document = _upload_document(
            client,
            owner_token,
            workspace["id"],
            filename=f"runbook-{index}.md",
            content=f"# Runbook {index}".encode(),
        )
        uploaded_ids.append(document["id"])

    response = client.get(
        f"/workspaces/{workspace['id']}/documents",
        headers={"Authorization": f"Bearer {owner_token}"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 5
    assert body["page"] == 1
    assert body["page_size"] == 20
    assert len(body["items"]) == 5
    returned_ids = {item["id"] for item in body["items"]}
    assert returned_ids == set(uploaded_ids)
    for item in body["items"]:
        assert item["workspace_id"] == workspace["id"]
        assert item["file_type"] == "md"
        assert "status" in item
        assert "uploaded_by" in item
        assert "created_at" in item
        assert "updated_at" in item


def test_list_documents_supports_pagination(document_list_context) -> None:
    client, _session = document_list_context
    _owner, owner_token = _register_user(
        client,
        email="list-page-owner@example.com",
        name="Page Owner",
    )
    workspace = _create_workspace(
        client,
        owner_token,
        name="Page Workspace",
        slug="doc-page-workspace",
    )

    for index in range(5):
        _upload_document(
            client,
            owner_token,
            workspace["id"],
            filename=f"page-{index}.md",
            content=f"# Page {index}".encode(),
        )

    page_one = client.get(
        f"/workspaces/{workspace['id']}/documents",
        params={"page": 1, "page_size": 2},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    page_two = client.get(
        f"/workspaces/{workspace['id']}/documents",
        params={"page": 2, "page_size": 2},
        headers={"Authorization": f"Bearer {owner_token}"},
    )

    assert page_one.status_code == 200
    assert page_two.status_code == 200
    page_one_body = page_one.json()
    page_two_body = page_two.json()
    assert page_one_body["total"] == 5
    assert page_two_body["total"] == 5
    assert len(page_one_body["items"]) == 2
    assert len(page_two_body["items"]) == 2
    page_one_ids = {item["id"] for item in page_one_body["items"]}
    page_two_ids = {item["id"] for item in page_two_body["items"]}
    assert page_one_ids.isdisjoint(page_two_ids)


def test_viewer_can_list_documents(document_list_context) -> None:
    client, _session = document_list_context
    _owner, owner_token = _register_user(
        client,
        email="list-viewer-owner@example.com",
        name="Owner",
    )
    viewer, viewer_token = _register_user(
        client,
        email="list-viewer@example.com",
        name="Viewer",
    )
    workspace = _create_workspace(
        client,
        owner_token,
        name="Viewer List Workspace",
        slug="doc-viewer-list-workspace",
    )
    _invite_member(
        client,
        owner_token,
        workspace["id"],
        email=viewer["email"],
        role="viewer",
    )
    _upload_document(
        client,
        owner_token,
        workspace["id"],
        filename="viewer-visible.md",
        content=b"# Visible",
    )

    response = client.get(
        f"/workspaces/{workspace['id']}/documents",
        headers={"Authorization": f"Bearer {viewer_token}"},
    )

    assert response.status_code == 200
    assert response.json()["total"] == 1


def test_list_documents_for_non_member_returns_403(document_list_context) -> None:
    client, _session = document_list_context
    _owner, owner_token = _register_user(
        client,
        email="list-outsider-owner@example.com",
        name="Owner",
    )
    _outsider, outsider_token = _register_user(
        client,
        email="list-outsider@example.com",
        name="Outsider",
    )
    workspace = _create_workspace(
        client,
        owner_token,
        name="Private Workspace",
        slug="doc-private-workspace",
    )

    response = client.get(
        f"/workspaces/{workspace['id']}/documents",
        headers={"Authorization": f"Bearer {outsider_token}"},
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "forbidden"
