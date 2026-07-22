"""Security tests for retrieval workspace isolation."""

from pathlib import Path
from uuid import UUID

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

try:
    from testcontainers.postgres import PostgresContainer
except ImportError:  # pragma: no cover - optional dev dependency
    PostgresContainer = None

from app.infrastructure.config import reset_settings_cache
from app.infrastructure.db.enums import DocumentStatus
from app.infrastructure.db.session import reset_db_engine
from app.infrastructure.llm.types import EmbeddingResult
from app.modules.auth.repository import AuthRepository
from app.modules.documents.repository import DocumentRepository
from app.modules.ingestion.chunker import EmbeddedChunk
from app.modules.ingestion.repository import IngestionRepository
from app.modules.retrieval.service import RetrievalService
from app.modules.workspaces.repository import WorkspaceRepository

EMBEDDING_DIMENSIONS = 1536
REPO_ROOT = Path(__file__).resolve().parents[2]


class FixedEmbeddingProvider:
    """Return a deterministic embedding vector for isolation tests."""

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


class StubSettings:
    RETRIEVAL_MIN_SCORE = 0.0


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
    reason="Docker is required for retrieval workspace isolation tests",
)


def _embedding(*, primary: float, secondary: float = 0.0) -> list[float]:
    vector = [0.0] * EMBEDDING_DIMENSIONS
    vector[0] = primary
    vector[1] = secondary
    return vector


@pytest.fixture(scope="module")
def postgres_url():
    with PostgresContainer("pgvector/pgvector:pg16") as postgres:
        yield postgres.get_connection_url()


@pytest.fixture
def retrieval_isolation_context(postgres_url, minimal_env, monkeypatch):
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

    yield session

    session.close()
    with engine.begin() as connection:
        connection.execute(text("TRUNCATE users RESTART IDENTITY CASCADE"))
    engine.dispose()
    reset_db_engine()


def _seed_identical_content_across_workspaces(
    session: Session,
) -> tuple[UUID, UUID, UUID, UUID]:
    auth_repo = AuthRepository(session)
    workspace_repo = WorkspaceRepository(session)
    document_repo = DocumentRepository(session)
    ingestion_repo = IngestionRepository(session)

    user = auth_repo.create_user(
        email="retrieval-iso@example.com",
        password_hash="hash",
        name="Retrieval User",
    )
    workspace_a = workspace_repo.create_workspace_with_owner(
        name="Workspace A",
        slug="workspace-a-retrieval",
        created_by=user.id,
    )
    workspace_b = workspace_repo.create_workspace_with_owner(
        name="Workspace B",
        slug="workspace-b-retrieval",
        created_by=user.id,
    )

    document_a = document_repo.create(
        workspace_id=workspace_a.id,
        status=DocumentStatus.INDEXED,
        title="Shared Runbook",
    )
    document_b = document_repo.create(
        workspace_id=workspace_b.id,
        status=DocumentStatus.INDEXED,
        title="Shared Runbook",
    )

    shared_content = "Restart the API service after deploy."
    shared_embedding = _embedding(primary=1.0, secondary=0.0)
    embedded_chunk = EmbeddedChunk(
        content=shared_content,
        chunk_index=0,
        metadata={"section": "deploy"},
        embedding=shared_embedding,
        embedding_model="text-embedding-3-small",
    )

    ingestion_repo.replace_chunks_for_document(
        workspace_id=workspace_a.id,
        document_id=document_a.id,
        embedded_chunks=[embedded_chunk],
    )
    ingestion_repo.replace_chunks_for_document(
        workspace_id=workspace_b.id,
        document_id=document_b.id,
        embedded_chunks=[embedded_chunk],
    )

    return workspace_a.id, workspace_b.id, document_a.id, document_b.id


def test_retrieval_service_returns_only_workspace_a_chunks(
    retrieval_isolation_context: Session,
) -> None:
    workspace_a_id, workspace_b_id, document_a_id, _ = (
        _seed_identical_content_across_workspaces(retrieval_isolation_context)
    )
    query_vector = _embedding(primary=1.0, secondary=0.0)

    service = RetrievalService(
        retrieval_isolation_context,
        embedding_provider=FixedEmbeddingProvider(query_vector),
        settings=StubSettings(),
    )

    result = service.search(
        query="How do I restart the API?",
        workspace_id=workspace_a_id,
    )

    assert result.insufficient_context is False
    assert len(result.chunks) == 1
    assert result.chunks[0].document_metadata.document_id == document_a_id
    assert result.chunks[0].content_preview == "Restart the API service after deploy."

    workspace_b_result = service.search(
        query="How do I restart the API?",
        workspace_id=workspace_b_id,
    )
    assert len(workspace_b_result.chunks) == 1
    assert (
        workspace_b_result.chunks[0].document_metadata.document_id != document_a_id
    )
