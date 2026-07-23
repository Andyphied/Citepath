"""Integration tests for the Northstar demo seed script."""

from pathlib import Path
from unittest.mock import patch

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

try:
    from testcontainers.postgres import PostgresContainer
except ImportError:  # pragma: no cover - optional dev dependency
    PostgresContainer = None

from app.infrastructure.config import reset_settings_cache
from app.infrastructure.db.enums import DocumentStatus
from app.infrastructure.db.session import reset_db_engine
from app.infrastructure.llm.types import EmbeddingResult
from app.modules.documents.repository import DocumentRepository
from app.modules.retrieval.schemas import RetrievalFilters
from app.modules.retrieval.service import RetrievalService
from scripts.seed_demo import DEMO_DOCUMENTS, seed_demo

EMBEDDING_DIMENSIONS = 1536
REPO_ROOT = Path(__file__).resolve().parents[2]


class DeterministicEmbeddingProvider:
    """Return a stable vector per input text for seed + retrieval tests."""

    @property
    def provider_name(self) -> str:
        return "mock"

    def embed(self, texts: list[str]) -> EmbeddingResult:
        vector = [0.0] * EMBEDDING_DIMENSIONS
        text = texts[0] if texts else ""
        if "502" in text or "billing" in text.lower():
            vector[0] = 1.0
        else:
            vector[0] = 0.3
        return EmbeddingResult(
            vectors=[vector],
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
    reason="Docker is required for demo seed integration tests",
)


@pytest.fixture(scope="module")
def postgres_url():
    with PostgresContainer("pgvector/pgvector:pg16") as postgres:
        yield postgres.get_connection_url()


@pytest.fixture
def seed_context(postgres_url, minimal_env, monkeypatch, tmp_path):
    monkeypatch.chdir(REPO_ROOT)
    monkeypatch.setenv("DATABASE_URL", postgres_url)
    monkeypatch.setenv("STORAGE_PATH", str(tmp_path / "uploads"))
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


def test_seed_demo_is_idempotent_and_supports_billing_query(seed_context, tmp_path) -> None:
    provider = DeterministicEmbeddingProvider()

    with patch(
        "app.modules.ingestion.tasks.create_embedding_provider",
        return_value=provider,
    ):
        first = seed_demo(password="demo-pass")
        second = seed_demo(password="demo-pass")

    assert first["workspace_slug"] == "northstar-cloud"
    assert int(first["indexed_documents"]) == len(DEMO_DOCUMENTS)
    assert int(second["skipped_documents"]) == len(DEMO_DOCUMENTS)
    assert int(second["indexed_documents"]) == 0

    document_repository = DocumentRepository(seed_context)
    workspace_id = _workspace_id_for_slug(seed_context, "northstar-cloud")
    documents = document_repository.list_for_workspace(workspace_id=workspace_id)
    assert len(documents) == len(DEMO_DOCUMENTS)
    for document in documents:
        assert document.status == DocumentStatus.INDEXED

    service = RetrievalService(
        seed_context,
        embedding_provider=provider,
        settings=StubSettings(),
    )
    result = service.search(
        query="What should I check for billing 502 errors after deployment?",
        workspace_id=workspace_id,
        filters=RetrievalFilters(source_type="runbook"),
    )

    assert result.insufficient_context is False
    assert result.chunks
    assert any(
        chunk.document_metadata.source_type in {"runbook", "incident", "process"}
        for chunk in result.chunks
    )


def _workspace_id_for_slug(session, slug: str):
    from sqlalchemy import select

    from app.modules.workspaces.models import Workspace

    workspace = session.scalar(select(Workspace).where(Workspace.slug == slug))
    assert workspace is not None
    return workspace.id
