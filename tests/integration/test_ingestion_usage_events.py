"""Integration tests for ingestion embedding usage events."""

from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session, sessionmaker

try:
    from testcontainers.postgres import PostgresContainer
except ImportError:  # pragma: no cover - optional dev dependency
    PostgresContainer = None

from app.infrastructure.config import reset_settings_cache
from app.infrastructure.db.enums import UsageEventStatus, UsageOperation
from app.infrastructure.db.session import reset_db_engine
from app.infrastructure.llm.types import EmbeddingResult
from app.modules.auth.repository import AuthRepository
from app.modules.ingestion.chunker import ContentChunk
from app.modules.ingestion.embeddings import EmbeddingError, embed_content_chunks
from app.modules.usage.models import UsageEvent
from app.modules.usage.service import UsageService
from app.modules.workspaces.repository import WorkspaceRepository

REPO_ROOT = Path(__file__).resolve().parents[2]


class MockEmbeddingProvider:
    """Deterministic provider for integration usage tests."""

    def __init__(self, *, tokens_per_text: int = 5) -> None:
        self.tokens_per_text = tokens_per_text
        self.calls: list[list[str]] = []

    @property
    def provider_name(self) -> str:
        return "mock"

    def embed(self, texts: list[str]) -> EmbeddingResult:
        self.calls.append(texts)
        vectors = [[float(index)] * 4 for index in range(len(texts))]
        return EmbeddingResult(
            vectors=vectors,
            embedding_tokens=self.tokens_per_text * len(texts),
            model="mock-embedding",
            latency_ms=10,
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
    reason="Docker is required for ingestion usage integration tests",
)


@pytest.fixture(scope="module")
def postgres_url():
    """Start a pgvector-enabled Postgres container."""
    with PostgresContainer("pgvector/pgvector:pg16") as postgres:
        yield postgres.get_connection_url()


@pytest.fixture
def usage_context(postgres_url, minimal_env, monkeypatch):
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

    try:
        yield {"session": session, "engine": engine}
    finally:
        session.close()
        with engine.begin() as connection:
            connection.execute(text("TRUNCATE users RESTART IDENTITY CASCADE"))
        engine.dispose()
        reset_db_engine()


def _seed_workspace(session: Session):
    auth_repository = AuthRepository(session)
    workspace_repository = WorkspaceRepository(session)

    user = auth_repository.create_user(
        email=f"usage-{uuid4().hex[:8]}@example.com",
        password_hash="hashed-password",
        name="Usage Tester",
    )
    workspace = workspace_repository.create_workspace_with_owner(
        name="Usage Workspace",
        slug=f"usage-{uuid4().hex[:8]}",
        created_by=user.id,
    )
    session.commit()
    return user, workspace


def test_ingestion_embedding_usage_events_aggregate_tokens_per_job(
    usage_context,
) -> None:
    session: Session = usage_context["session"]
    _user, workspace = _seed_workspace(session)

    document_id = uuid4()
    job_id = uuid4()
    chunks = [
        ContentChunk(
            content=f"chunk {index}",
            chunk_index=index,
            metadata={"chunk_index": index},
        )
        for index in range(20)
    ]
    provider = MockEmbeddingProvider(tokens_per_text=3)
    usage_service = UsageService(session)

    result = embed_content_chunks(
        chunks=chunks,
        embedding_provider=provider,
        usage_service=usage_service,
        workspace_id=workspace.id,
        document_id=document_id,
        job_id=job_id,
        batch_size=8,
        embedding_model="text-embedding-3-small",
    )
    session.commit()

    assert not isinstance(result, EmbeddingError)
    assert len(result) == 20
    assert len(provider.calls) == 3

    events = session.scalars(
        select(UsageEvent).where(
            UsageEvent.workspace_id == workspace.id,
            UsageEvent.operation == UsageOperation.EMBEDDING_DOCUMENT,
        )
    ).all()
    assert len(events) == 3
    assert all(event.status == UsageEventStatus.SUCCESS for event in events)
    assert all(event.user_id is None for event in events)
    assert all(event.metadata_["job_id"] == str(job_id) for event in events)
    assert all(event.metadata_["document_id"] == str(document_id) for event in events)

    aggregate_tokens = usage_service.sum_embedding_tokens_for_job(
        workspace_id=workspace.id,
        job_id=job_id,
    )
    assert aggregate_tokens == 60
    assert sum(event.embedding_tokens for event in events) == 60
