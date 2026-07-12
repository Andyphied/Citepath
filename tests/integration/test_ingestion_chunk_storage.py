"""Integration tests for ingestion chunk persistence."""

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
from app.modules.auth.repository import AuthRepository
from app.modules.documents.repository import DocumentRepository
from app.modules.ingestion.chunker import EmbeddedChunk
from app.modules.ingestion.repository import IngestionRepository
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
    reason="Docker is required for ingestion chunk storage integration tests",
)


def _embedding(*, primary: float, secondary: float = 0.0) -> list[float]:
    vector = [0.0] * EMBEDDING_DIMENSIONS
    vector[0] = primary
    vector[1] = secondary
    return vector


@pytest.fixture(scope="module")
def postgres_url():
    """Start a pgvector-enabled Postgres container."""
    with PostgresContainer("pgvector/pgvector:pg16") as postgres:
        yield postgres.get_connection_url()


@pytest.fixture
def chunk_storage_context(postgres_url, minimal_env, monkeypatch):
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


def _seed_document(session: Session) -> tuple[UUID, UUID]:
    auth_repo = AuthRepository(session)
    workspace_repo = WorkspaceRepository(session)
    document_repo = DocumentRepository(session)

    user = auth_repo.create_user(
        email="ingestion-chunks@example.com",
        password_hash="hash",
        name="Ingestion User",
    )
    workspace = workspace_repo.create_workspace_with_owner(
        name="Chunk Storage Workspace",
        slug="chunk-storage-workspace",
        created_by=user.id,
    )
    document = document_repo.create(
        workspace_id=workspace.id,
        status=DocumentStatus.PROCESSING,
        title="Runbook",
    )
    return workspace.id, document.id


def test_replace_chunks_are_queryable_via_vector_search(
    chunk_storage_context: Session,
) -> None:
    workspace_id, document_id = _seed_document(chunk_storage_context)
    ingestion_repo = IngestionRepository(chunk_storage_context)

    embedded_chunks = [
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
    ]

    ingestion_repo.replace_chunks_for_document(
        workspace_id=workspace_id,
        document_id=document_id,
        embedded_chunks=embedded_chunks,
    )

    stored_chunks = ingestion_repo.list_chunks_for_document(
        workspace_id=workspace_id,
        document_id=document_id,
    )
    assert len(stored_chunks) == 2
    assert stored_chunks[0].chunk_index == 0
    assert stored_chunks[1].chunk_index == 1

    similar_chunks = ingestion_repo.search_similar(
        workspace_id=workspace_id,
        embedding=_embedding(primary=1.0, secondary=0.0),
        top_k=1,
    )
    assert len(similar_chunks) == 1
    assert similar_chunks[0].content == "Restart the API service after deploy."


def test_replace_chunks_deletes_previous_rows_before_insert(
    chunk_storage_context: Session,
) -> None:
    workspace_id, document_id = _seed_document(chunk_storage_context)
    ingestion_repo = IngestionRepository(chunk_storage_context)

    ingestion_repo.replace_chunks_for_document(
        workspace_id=workspace_id,
        document_id=document_id,
        embedded_chunks=[
            EmbeddedChunk(
                content="old chunk",
                chunk_index=0,
                metadata={},
                embedding=_embedding(primary=0.5),
                embedding_model="text-embedding-3-small",
            ),
        ],
    )

    ingestion_repo.replace_chunks_for_document(
        workspace_id=workspace_id,
        document_id=document_id,
        embedded_chunks=[
            EmbeddedChunk(
                content="new chunk",
                chunk_index=0,
                metadata={},
                embedding=_embedding(primary=0.8),
                embedding_model="text-embedding-3-small",
            ),
        ],
    )

    stored_chunks = ingestion_repo.list_chunks_for_document(
        workspace_id=workspace_id,
        document_id=document_id,
    )
    assert len(stored_chunks) == 1
    assert stored_chunks[0].content == "new chunk"
