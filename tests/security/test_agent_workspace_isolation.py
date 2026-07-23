"""Security tests for agent tool workspace isolation."""

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
from app.infrastructure.db.enums import DocumentStatus, WorkspaceRole
from app.infrastructure.db.session import reset_db_engine
from app.infrastructure.llm.types import EmbeddingResult
from app.modules.agents.schemas import SearchKnowledgeBaseArgs
from app.modules.agents.tools.search_knowledge_base import execute_search_knowledge_base
from app.modules.auth.repository import AuthRepository
from app.modules.documents.repository import DocumentRepository
from app.modules.ingestion.chunker import EmbeddedChunk
from app.modules.ingestion.repository import IngestionRepository
from app.modules.retrieval.service import RetrievalService
from app.modules.workspaces.context import WorkspaceContext
from app.modules.workspaces.repository import WorkspaceRepository

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
    reason="Docker is required for agent workspace isolation tests",
)


def _embedding(*, primary: float = 1.0) -> list[float]:
    vector = [0.0] * EMBEDDING_DIMENSIONS
    vector[0] = primary
    return vector


@pytest.fixture(scope="module")
def postgres_url():
    with PostgresContainer("pgvector/pgvector:pg16") as postgres:
        yield postgres.get_connection_url()


@pytest.fixture
def agent_isolation_context(postgres_url, minimal_env, monkeypatch):
    monkeypatch.chdir(REPO_ROOT)
    monkeypatch.setenv("DATABASE_URL", postgres_url)
    reset_settings_cache()
    reset_db_engine()

    alembic_cfg = Config(str(REPO_ROOT / "alembic.ini"))
    command.upgrade(alembic_cfg, "head")

    engine = create_engine(postgres_url)
    session_factory = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    session = session_factory()

    yield session

    session.close()
    with engine.begin() as connection:
        connection.execute(text("TRUNCATE users RESTART IDENTITY CASCADE"))
    engine.dispose()
    reset_db_engine()


def _seed_workspaces(session: Session) -> tuple[UUID, UUID, UUID, UUID, UUID]:
    auth_repo = AuthRepository(session)
    workspace_repo = WorkspaceRepository(session)
    document_repo = DocumentRepository(session)
    ingestion_repo = IngestionRepository(session)

    user = auth_repo.create_user(
        email="agent-iso@example.com",
        password_hash="hash",
        name="Agent Isolation User",
    )
    workspace_a = workspace_repo.create_workspace_with_owner(
        name="Agent Workspace A",
        slug="agent-workspace-a",
        created_by=user.id,
    )
    workspace_b = workspace_repo.create_workspace_with_owner(
        name="Agent Workspace B",
        slug="agent-workspace-b",
        created_by=user.id,
    )

    document_a = document_repo.create(
        workspace_id=workspace_a.id,
        status=DocumentStatus.INDEXED,
        title="Workspace A Runbook",
        source_type="runbook",
        file_type="md",
    )
    document_b = document_repo.create(
        workspace_id=workspace_b.id,
        status=DocumentStatus.INDEXED,
        title="Workspace B Runbook",
        source_type="runbook",
        file_type="md",
    )

    vector = _embedding(primary=1.0)
    ingestion_repo.replace_chunks_for_document(
        workspace_id=workspace_a.id,
        document_id=document_a.id,
        embedded_chunks=[
            EmbeddedChunk(
                content="Workspace A billing 502 restart procedure.",
                chunk_index=0,
                metadata={"section": "502"},
                embedding=vector,
                embedding_model="text-embedding-3-small",
            )
        ],
    )
    ingestion_repo.replace_chunks_for_document(
        workspace_id=workspace_b.id,
        document_id=document_b.id,
        embedded_chunks=[
            EmbeddedChunk(
                content="Workspace B secret incident notes.",
                chunk_index=0,
                metadata={"section": "secret"},
                embedding=vector,
                embedding_model="text-embedding-3-small",
            )
        ],
    )
    return workspace_a.id, workspace_b.id, document_a.id, document_b.id, user.id


def test_search_knowledge_base_rejects_foreign_document_id(
    agent_isolation_context: Session,
) -> None:
    workspace_a_id, _workspace_b_id, _document_a_id, document_b_id, user_id = (
        _seed_workspaces(agent_isolation_context)
    )
    retrieval_service = RetrievalService(
        agent_isolation_context,
        embedding_provider=FixedEmbeddingProvider(_embedding(primary=1.0)),
        settings=StubSettings(),
    )
    context = WorkspaceContext(
        workspace_id=workspace_a_id,
        user_id=user_id,
        role=WorkspaceRole.MEMBER,
    )

    output = execute_search_knowledge_base(
        args=SearchKnowledgeBaseArgs(
            query="billing 502 restart",
            document_id=document_b_id,
        ),
        context=context,
        retrieval_service=retrieval_service,
    )

    assert output["citations"] == []
    assert output["related_documents"] == []
    assert output["insufficient_context"] is True
    assert str(document_b_id) not in str(output)
