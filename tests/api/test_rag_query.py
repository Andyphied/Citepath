"""API tests for RAG query endpoint."""

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
                '{"answer":"Restart billing-api for billing 502 errors.",'
                '"facts":["502 requires restart"],'
                '"recommendations":["Check upstream health"],'
                '"cited_chunk_ids":[],'
                '"suggested_followups":["What logs?","Who owns billing?"]}'
            ),
            prompt_tokens=100,
            completion_tokens=40,
            model="mock-chat",
            latency_ms=8,
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
    reason="Docker is required for RAG query API tests",
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
def rag_api_context(postgres_url, minimal_env, monkeypatch):
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


def _register(client: TestClient) -> tuple[dict, str]:
    response = client.post(
        "/auth/register",
        json={
            "email": "rag-api@example.com",
            "password": "securepass123",
            "name": "RAG API",
        },
    )
    assert response.status_code == 201
    body = response.json()
    return body["user"], body["access_token"]


def _create_workspace(client: TestClient, token: str) -> dict:
    response = client.post(
        "/workspaces",
        json={"name": "RAG API Workspace", "slug": "rag-api-workspace"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    return response.json()


def _seed_chunk(session, *, workspace_id, document_id) -> None:
    ingestion_repo = IngestionRepository(session)
    ingestion_repo.replace_chunks_for_document(
        workspace_id=workspace_id,
        document_id=document_id,
        embedded_chunks=[
            EmbeddedChunk(
                content="For billing 502 errors restart billing-api.",
                chunk_index=0,
                metadata={"section": "502"},
                embedding=_embedding(primary=1.0),
                embedding_model="text-embedding-3-small",
            )
        ],
    )


def _seed_document(session, *, workspace_id):
    from app.modules.documents.repository import DocumentRepository

    return DocumentRepository(session).create(
        workspace_id=workspace_id,
        status=DocumentStatus.INDEXED,
        title="Billing Runbook",
        source_type="runbook",
        file_type="md",
    )


def test_query_endpoint_returns_answer_with_citations(
    rag_api_context,
) -> None:
    client, session = rag_api_context
    _user, token = _register(client)
    workspace = _create_workspace(client, token)
    document = _seed_document(session, workspace_id=workspace["id"])
    _seed_chunk(
        session,
        workspace_id=workspace["id"],
        document_id=document.id,
    )

    response = client.post(
        f"/workspaces/{workspace['id']}/query",
        json={"question": "What should I check for billing 502 errors?"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["insufficient_context"] is False
    assert body["confidence"] in {"high", "medium"}
    assert body["answer"]
    assert len(body["citations"]) >= 1
    assert body["citations"][0]["document_title"] == "Billing Runbook"
    assert body["conversation_id"]
    assert body["message_id"]


def test_query_endpoint_returns_insufficient_context_without_docs(
    rag_api_context,
) -> None:
    client, _session = rag_api_context
    _user, token = _register(client)
    workspace = _create_workspace(client, token)

    response = client.post(
        f"/workspaces/{workspace['id']}/query",
        json={"question": "What should I check for billing 502 errors?"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["insufficient_context"] is True
    assert body["confidence"] == "low"
    assert body["citations"] == []


def test_query_endpoint_requires_auth(rag_api_context) -> None:
    client, _session = rag_api_context
    response = client.post(
        f"/workspaces/{uuid4()}/query",
        json={"question": "billing 502"},
    )
    assert response.status_code == 401


def test_query_endpoint_sanitizes_embedding_failure(
    rag_api_context,
    monkeypatch,
) -> None:
    client, session = rag_api_context
    _user, token = _register(client)
    workspace = _create_workspace(client, token)

    class FailingEmbeddingProvider:
        provider_name = "mock"

        def embed(self, texts):
            raise RuntimeError("provider secret failure details")

    import app.api.deps as deps_module
    import app.infrastructure.llm.factory as factory_module

    monkeypatch.setattr(
        factory_module,
        "create_embedding_provider",
        lambda settings: FailingEmbeddingProvider(),
    )
    monkeypatch.setattr(
        deps_module,
        "create_embedding_provider",
        lambda settings: FailingEmbeddingProvider(),
    )

    response = client.post(
        f"/workspaces/{workspace['id']}/query",
        json={"question": "billing 502"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 502
    body = response.json()
    assert body["error"]["code"] == "embedding_failed"
    assert "secret failure" not in body["error"]["message"]
