"""Security tests for workspace-scoped repository isolation."""

from dataclasses import dataclass
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
from app.infrastructure.db.enums import (
    AgentRunStatus,
    ConversationMode,
    DocumentStatus,
)
from app.infrastructure.db.session import reset_db_engine
from app.modules.agents.repository import AgentRepository
from app.modules.auth.repository import AuthRepository
from app.modules.documents.repository import DocumentRepository
from app.modules.ingestion.repository import IngestionRepository
from app.modules.rag.repository import RAGRepository
from app.modules.workspaces.repository import WorkspaceRepository

EMBEDDING_DIMENSIONS = 1536
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
    reason="Docker is required for workspace isolation tests",
)


@dataclass(frozen=True)
class IsolationFixtures:
    workspace_a_id: UUID
    workspace_b_id: UUID
    document_a_id: UUID
    document_b_id: UUID
    chunk_a_id: UUID
    chunk_b_id: UUID
    conversation_a_id: UUID
    conversation_b_id: UUID
    agent_run_a_id: UUID
    agent_run_b_id: UUID


def _embedding(*, primary: float, secondary: float = 0.0) -> list[float]:
    vector = [0.0] * EMBEDDING_DIMENSIONS
    vector[0] = primary
    vector[1] = secondary
    return vector


@pytest.fixture(scope="module")
def postgres_url():
    """Start a pgvector-enabled Postgres container for isolation tests."""
    with PostgresContainer("pgvector/pgvector:pg16") as postgres:
        yield postgres.get_connection_url()


@pytest.fixture
def isolation_context(postgres_url, minimal_env, monkeypatch):
    """Migrated database and session with per-test cleanup."""
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


def _seed_isolation_data(session: Session) -> IsolationFixtures:
    auth_repo = AuthRepository(session)
    workspace_repo = WorkspaceRepository(session)
    document_repo = DocumentRepository(session)
    ingestion_repo = IngestionRepository(session)
    rag_repo = RAGRepository(session)
    agent_repo = AgentRepository(session)

    user_a = auth_repo.create_user(
        email="iso-a@example.com",
        password_hash="hash-a",
        name="User A",
    )
    user_b = auth_repo.create_user(
        email="iso-b@example.com",
        password_hash="hash-b",
        name="User B",
    )

    workspace_a = workspace_repo.create_workspace_with_owner(
        name="Workspace A",
        slug="iso-workspace-a",
        created_by=user_a.id,
    )
    workspace_b = workspace_repo.create_workspace_with_owner(
        name="Workspace B",
        slug="iso-workspace-b",
        created_by=user_b.id,
    )

    document_a = document_repo.create(
        workspace_id=workspace_a.id,
        status=DocumentStatus.INDEXED,
        title="Document A",
    )
    document_b = document_repo.create(
        workspace_id=workspace_b.id,
        status=DocumentStatus.INDEXED,
        title="Document B",
    )

    chunk_a = ingestion_repo.create_chunk(
        workspace_id=workspace_a.id,
        document_id=document_a.id,
        chunk_index=0,
        content="Chunk A content",
        embedding=_embedding(primary=1.0),
    )
    chunk_b = ingestion_repo.create_chunk(
        workspace_id=workspace_b.id,
        document_id=document_b.id,
        chunk_index=0,
        content="Chunk B content",
        embedding=_embedding(primary=0.0, secondary=1.0),
    )

    conversation_a = rag_repo.create_conversation(
        workspace_id=workspace_a.id,
        user_id=user_a.id,
        mode=ConversationMode.RAG,
        title="Conversation A",
    )
    conversation_b = rag_repo.create_conversation(
        workspace_id=workspace_b.id,
        user_id=user_b.id,
        mode=ConversationMode.RAG,
        title="Conversation B",
    )

    agent_run_a = agent_repo.create_run(
        workspace_id=workspace_a.id,
        user_id=user_a.id,
        objective="Run A",
        status=AgentRunStatus.RUNNING,
    )
    agent_run_b = agent_repo.create_run(
        workspace_id=workspace_b.id,
        user_id=user_b.id,
        objective="Run B",
        status=AgentRunStatus.RUNNING,
    )

    return IsolationFixtures(
        workspace_a_id=workspace_a.id,
        workspace_b_id=workspace_b.id,
        document_a_id=document_a.id,
        document_b_id=document_b.id,
        chunk_a_id=chunk_a.id,
        chunk_b_id=chunk_b.id,
        conversation_a_id=conversation_a.id,
        conversation_b_id=conversation_b.id,
        agent_run_a_id=agent_run_a.id,
        agent_run_b_id=agent_run_b.id,
    )


def test_document_get_by_id_cross_workspace_returns_none(
    isolation_context: Session,
) -> None:
    fixtures = _seed_isolation_data(isolation_context)
    repository = DocumentRepository(isolation_context)

    result = repository.get_by_id(
        workspace_id=fixtures.workspace_a_id,
        id=fixtures.document_b_id,
    )

    assert result is None


def test_document_list_for_workspace_excludes_other_workspace(
    isolation_context: Session,
) -> None:
    fixtures = _seed_isolation_data(isolation_context)
    repository = DocumentRepository(isolation_context)

    documents = repository.list_for_workspace(
        workspace_id=fixtures.workspace_a_id,
    )

    assert len(documents) == 1
    assert documents[0].id == fixtures.document_a_id


def test_list_chunks_for_document_excludes_other_workspace(
    isolation_context: Session,
) -> None:
    fixtures = _seed_isolation_data(isolation_context)
    repository = IngestionRepository(isolation_context)

    own_chunks = repository.list_chunks_for_document(
        workspace_id=fixtures.workspace_a_id,
        document_id=fixtures.document_a_id,
    )
    cross_workspace_chunks = repository.list_chunks_for_document(
        workspace_id=fixtures.workspace_a_id,
        document_id=fixtures.document_b_id,
    )

    assert len(own_chunks) == 1
    assert own_chunks[0].id == fixtures.chunk_a_id
    assert cross_workspace_chunks == []


def test_search_similar_excludes_other_workspace_chunks(
    isolation_context: Session,
) -> None:
    fixtures = _seed_isolation_data(isolation_context)
    repository = IngestionRepository(isolation_context)

    results = repository.search_similar(
        workspace_id=fixtures.workspace_a_id,
        embedding=_embedding(primary=1.0),
        top_k=5,
    )

    assert len(results) == 1
    assert results[0].id == fixtures.chunk_a_id
    assert all(
        chunk.workspace_id == fixtures.workspace_a_id for chunk in results
    )


def test_chunk_get_by_id_wrong_workspace_returns_none(
    isolation_context: Session,
) -> None:
    fixtures = _seed_isolation_data(isolation_context)
    repository = IngestionRepository(isolation_context)

    result = repository.get_chunk_by_id(
        workspace_id=fixtures.workspace_a_id,
        id=fixtures.chunk_b_id,
    )

    assert result is None


def test_conversation_get_by_id_cross_workspace_returns_none(
    isolation_context: Session,
) -> None:
    fixtures = _seed_isolation_data(isolation_context)
    repository = RAGRepository(isolation_context)

    result = repository.get_conversation_by_id(
        workspace_id=fixtures.workspace_a_id,
        id=fixtures.conversation_b_id,
    )

    assert result is None


def test_agent_run_get_by_id_cross_workspace_returns_none(
    isolation_context: Session,
) -> None:
    fixtures = _seed_isolation_data(isolation_context)
    repository = AgentRepository(isolation_context)

    result = repository.get_run_by_id(
        workspace_id=fixtures.workspace_a_id,
        id=fixtures.agent_run_b_id,
    )

    assert result is None
