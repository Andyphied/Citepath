"""Security tests for RAG query workspace isolation."""

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
from app.infrastructure.db.enums import DocumentStatus
from app.infrastructure.db.session import reset_db_engine
from app.infrastructure.llm.types import CompletionResult, EmbeddingResult
from app.main import create_app
from app.modules.ingestion.chunker import EmbeddedChunk
from app.modules.ingestion.repository import IngestionRepository

EMBEDDING_DIMENSIONS = 1536
REPO_ROOT = Path(__file__).resolve().parents[2]


class FixedEmbeddingProvider:
    def __init__(self, vector: list[float]) -> None:
        self._vector = vector

    @property
    def provider_name(self) -> str:
        return "mock"

    def embed(self, texts: list[str]) -> EmbeddingResult:
        return EmbeddingResult(
            vectors=[self._vector],
            embedding_tokens=8,
            model="mock-embedding",
            latency_ms=5,
        )


class StubCompletionProvider:
    provider_name = "mock"

    def complete(self, *, messages, response_format=None):
        return CompletionResult(
            content=(
                '{"answer":"Workspace-specific answer.",'
                '"cited_chunk_ids":[],'
                '"suggested_followups":["Next?","Another?"]}'
            ),
            prompt_tokens=50,
            completion_tokens=20,
            model="mock-chat",
            latency_ms=5,
        )


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
    reason="Docker is required for RAG security tests",
)


def _embedding(*, primary: float) -> list[float]:
    vector = [0.0] * EMBEDDING_DIMENSIONS
    vector[0] = primary
    return vector


@pytest.fixture(scope="module")
def postgres_url():
    with PostgresContainer("pgvector/pgvector:pg16") as postgres:
        yield postgres.get_connection_url()


@pytest.fixture
def rag_security_context(postgres_url, minimal_env, monkeypatch):
    monkeypatch.chdir(REPO_ROOT)
    monkeypatch.setenv("DATABASE_URL", postgres_url)
    reset_settings_cache()
    reset_db_engine()

    alembic_cfg = Config(str(REPO_ROOT / "alembic.ini"))
    command.upgrade(alembic_cfg, "head")

    engine = create_engine(postgres_url)
    session_factory = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    session = session_factory()

    import app.api.deps as deps_module
    import app.infrastructure.llm.factory as factory_module

    monkeypatch.setattr(
        factory_module,
        "create_embedding_provider",
        lambda settings: FixedEmbeddingProvider(_embedding(primary=1.0)),
    )
    monkeypatch.setattr(
        factory_module,
        "create_completion_provider",
        lambda settings: StubCompletionProvider(),
    )
    monkeypatch.setattr(
        deps_module,
        "create_embedding_provider",
        lambda settings: FixedEmbeddingProvider(_embedding(primary=1.0)),
    )
    monkeypatch.setattr(
        deps_module,
        "create_completion_provider",
        lambda settings: StubCompletionProvider(),
    )

    with TestClient(create_app()) as client:
        yield client, session

    session.close()
    with engine.begin() as connection:
        connection.execute(text("TRUNCATE users RESTART IDENTITY CASCADE"))
    engine.dispose()
    reset_db_engine()


def _register(client: TestClient, *, email: str) -> tuple[dict, str]:
    response = client.post(
        "/auth/register",
        json={
            "email": email,
            "password": "securepass123",
            "name": email.split("@")[0],
        },
    )
    assert response.status_code == 201
    body = response.json()
    return body["user"], body["access_token"]


def _create_workspace(client: TestClient, token: str, *, slug: str) -> dict:
    response = client.post(
        "/workspaces",
        json={"name": slug, "slug": slug},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    return response.json()


def _seed_workspace_document(
    session,
    *,
    workspace_id: UUID,
    content: str,
) -> UUID:
    from app.modules.documents.repository import DocumentRepository

    document_repo = DocumentRepository(session)
    ingestion_repo = IngestionRepository(session)
    document = document_repo.create(
        workspace_id=workspace_id,
        status=DocumentStatus.INDEXED,
        title="Shared Runbook",
        source_type="runbook",
        file_type="md",
    )
    ingestion_repo.replace_chunks_for_document(
        workspace_id=workspace_id,
        document_id=document.id,
        embedded_chunks=[
            EmbeddedChunk(
                content=content,
                chunk_index=0,
                metadata={"section": "deploy"},
                embedding=_embedding(primary=1.0),
                embedding_model="text-embedding-3-small",
            )
        ],
    )
    return document.id


def test_query_endpoint_only_uses_callers_workspace_documents(
    rag_security_context,
) -> None:
    client, session = rag_security_context
    _user_a, token_a = _register(client, email="rag-iso-a@example.com")
    _user_b, token_b = _register(client, email="rag-iso-b@example.com")
    workspace_a = _create_workspace(client, token_a, slug="rag-iso-a")
    workspace_b = _create_workspace(client, token_b, slug="rag-iso-b")

    doc_a = _seed_workspace_document(
        session,
        workspace_id=workspace_a["id"],
        content="Workspace A billing 502 restart procedure.",
    )
    _seed_workspace_document(
        session,
        workspace_id=workspace_b["id"],
        content="Workspace B unrelated content.",
    )

    response = client.post(
        f"/workspaces/{workspace_a['id']}/query",
        json={"question": "billing 502 restart"},
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["insufficient_context"] is False
    assert len(body["citations"]) == 1
    assert body["citations"][0]["document_id"] == str(doc_a)

    empty_workspace_response = client.post(
        f"/workspaces/{workspace_b['id']}/query",
        json={"question": "billing 502 restart"},
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert empty_workspace_response.status_code == 200
    empty_body = empty_workspace_response.json()
    assert empty_body["citations"]
    assert empty_body["citations"][0]["document_id"] != str(doc_a)
