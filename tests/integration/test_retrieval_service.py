"""Integration tests for RetrievalService with pgvector."""

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
from app.modules.retrieval.schemas import RetrievalFilters
from app.modules.retrieval.service import RetrievalService
from app.modules.workspaces.repository import WorkspaceRepository

EMBEDDING_DIMENSIONS = 1536
REPO_ROOT = Path(__file__).resolve().parents[2]


class FixedEmbeddingProvider:
    """Return a deterministic embedding vector for integration tests."""

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
    reason="Docker is required for retrieval integration tests",
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
def retrieval_context(postgres_url, minimal_env, monkeypatch):
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


def _seed_chunks(session: Session) -> tuple[UUID, UUID]:
    auth_repo = AuthRepository(session)
    workspace_repo = WorkspaceRepository(session)
    document_repo = DocumentRepository(session)
    ingestion_repo = IngestionRepository(session)

    user = auth_repo.create_user(
        email="retrieval-int@example.com",
        password_hash="hash",
        name="Retrieval User",
    )
    workspace = workspace_repo.create_workspace_with_owner(
        name="Retrieval Workspace",
        slug="retrieval-workspace",
        created_by=user.id,
    )
    document = document_repo.create(
        workspace_id=workspace.id,
        status=DocumentStatus.INDEXED,
        title="Runbook",
        source_type="runbook",
        file_type="md",
    )

    ingestion_repo.replace_chunks_for_document(
        workspace_id=workspace.id,
        document_id=document.id,
        embedded_chunks=[
            EmbeddedChunk(
                content="Restart the API service after deploy.",
                chunk_index=0,
                metadata={"section": "deploy"},
                embedding=_embedding(primary=1.0, secondary=0.0),
                embedding_model="text-embedding-3-small",
            ),
            EmbeddedChunk(
                content="Check Redis connectivity before scaling workers.",
                chunk_index=1,
                metadata={"section": "infra"},
                embedding=_embedding(primary=0.2, secondary=0.9),
                embedding_model="text-embedding-3-small",
            ),
        ],
    )

    return workspace.id, document.id


def test_retrieval_service_returns_top_k_chunks_with_scores(
    retrieval_context: Session,
) -> None:
    workspace_id, document_id = _seed_chunks(retrieval_context)
    query_vector = _embedding(primary=1.0, secondary=0.0)

    service = RetrievalService(
        retrieval_context,
        embedding_provider=FixedEmbeddingProvider(query_vector),
        settings=StubSettings(),
    )

    result = service.search(
        query="How do I restart the API?",
        workspace_id=workspace_id,
        top_k=8,
    )

    assert result.insufficient_context is False
    assert len(result.chunks) == 2
    assert result.chunks[0].score >= result.chunks[1].score
    assert result.chunks[0].content_preview.startswith("Restart the API")
    assert result.chunks[0].citation_id == result.chunks[0].chunk_id
    assert result.chunks[0].document_metadata.document_id == document_id
    assert result.chunks[0].document_metadata.title == "Runbook"
    assert result.chunks[0].document_metadata.source_type == "runbook"


def test_retrieval_service_filters_by_file_type(
    retrieval_context: Session,
    three_page_pdf_bytes: bytes,
) -> None:
    auth_repo = AuthRepository(retrieval_context)
    workspace_repo = WorkspaceRepository(retrieval_context)
    document_repo = DocumentRepository(retrieval_context)
    ingestion_repo = IngestionRepository(retrieval_context)

    user = auth_repo.create_user(
        email="filter-int@example.com",
        password_hash="hash",
        name="Filter User",
    )
    workspace = workspace_repo.create_workspace_with_owner(
        name="Filter Workspace",
        slug="filter-workspace",
        created_by=user.id,
    )
    md_document = document_repo.create(
        workspace_id=workspace.id,
        status=DocumentStatus.INDEXED,
        title="Markdown Runbook",
        source_type="runbook",
        file_type="md",
    )
    pdf_document = document_repo.create(
        workspace_id=workspace.id,
        status=DocumentStatus.INDEXED,
        title="PDF Runbook",
        source_type="runbook",
        file_type="pdf",
    )

    query_vector = _embedding(primary=1.0, secondary=0.0)
    pdf_vector = _embedding(primary=0.95, secondary=0.1)
    md_vector = _embedding(primary=0.9, secondary=0.2)

    ingestion_repo.replace_chunks_for_document(
        workspace_id=workspace.id,
        document_id=md_document.id,
        embedded_chunks=[
            EmbeddedChunk(
                content="Markdown restart steps for billing-api.",
                chunk_index=0,
                metadata={"section": "md"},
                embedding=md_vector,
                embedding_model="text-embedding-3-small",
            ),
        ],
    )
    ingestion_repo.replace_chunks_for_document(
        workspace_id=workspace.id,
        document_id=pdf_document.id,
        embedded_chunks=[
            EmbeddedChunk(
                content="PDF restart steps for billing-api.",
                chunk_index=0,
                metadata={"section": "pdf"},
                embedding=pdf_vector,
                embedding_model="text-embedding-3-small",
            ),
        ],
    )

    service = RetrievalService(
        retrieval_context,
        embedding_provider=FixedEmbeddingProvider(query_vector),
        settings=StubSettings(),
    )

    filtered = service.search(
        query="How do I restart billing-api?",
        workspace_id=workspace.id,
        top_k=8,
        filters=RetrievalFilters(file_type="pdf"),
    )

    assert filtered.insufficient_context is False
    assert len(filtered.chunks) == 1
    assert filtered.chunks[0].document_metadata.file_type == "pdf"
    assert filtered.chunks[0].document_metadata.document_id == pdf_document.id
    assert "PDF restart" in filtered.chunks[0].content_preview
