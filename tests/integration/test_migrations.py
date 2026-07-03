"""Integration tests for Alembic migrations."""

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text

try:
    from testcontainers.postgres import PostgresContainer
except ImportError:  # pragma: no cover - optional dev dependency
    PostgresContainer = None

from app.infrastructure.config import reset_settings_cache
from app.infrastructure.db.session import reset_db_engine

EXPECTED_TABLES = {
    "users",
    "workspaces",
    "workspace_members",
    "documents",
    "document_chunks",
    "ingestion_jobs",
    "conversations",
    "messages",
    "agent_runs",
    "agent_tool_calls",
    "usage_events",
    "audit_logs",
    "alembic_version",
}


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
    reason="Docker is required for migration integration tests",
)


@pytest.fixture(scope="module")
def postgres_url():
    """Start a pgvector-enabled Postgres container for migration tests."""
    with PostgresContainer("pgvector/pgvector:pg16") as postgres:
        yield postgres.get_connection_url()


def test_migrations_create_all_core_tables(postgres_url, minimal_env, monkeypatch):
    """Given empty database, migrations create all data-model tables."""
    monkeypatch.setenv("DATABASE_URL", postgres_url)
    reset_settings_cache()
    reset_db_engine()

    alembic_cfg = Config("alembic.ini")
    command.upgrade(alembic_cfg, "head")

    engine = create_engine(postgres_url)
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())

    assert EXPECTED_TABLES.issubset(tables)

    with engine.connect() as connection:
        extension = connection.execute(
            text("SELECT 1 FROM pg_extension WHERE extname = 'vector'")
        ).scalar_one()
        assert extension == 1

        hnsw_index = connection.execute(
            text(
                """
                SELECT 1
                FROM pg_indexes
                WHERE tablename = 'document_chunks'
                  AND indexname = 'ix_document_chunks_embedding_hnsw'
                """
            )
        ).scalar_one()
        assert hnsw_index == 1

        workspace_indexes = {
            index["name"]
            for index in inspector.get_indexes("documents")
            if index["column_names"][0] == "workspace_id"
        }
        assert "ix_documents_workspace_id_status" in workspace_indexes

    engine.dispose()


def test_migrations_downgrade_and_upgrade(postgres_url, minimal_env, monkeypatch):
    """Migrations can downgrade one revision and re-upgrade."""
    monkeypatch.setenv("DATABASE_URL", postgres_url)
    reset_settings_cache()
    reset_db_engine()

    alembic_cfg = Config("alembic.ini")
    command.upgrade(alembic_cfg, "head")
    command.downgrade(alembic_cfg, "base")
    command.upgrade(alembic_cfg, "head")

    engine = create_engine(postgres_url)
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    assert EXPECTED_TABLES.issubset(tables)
    engine.dispose()
