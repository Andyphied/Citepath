"""Unit tests for SQLAlchemy model metadata."""

from app.infrastructure.db.base import Base, import_all_models

CORE_TABLES = {
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
}


def test_all_core_tables_registered_in_metadata():
    """ORM metadata includes every table from the data model."""
    import_all_models()
    table_names = set(Base.metadata.tables.keys())
    assert CORE_TABLES == table_names


def test_tenant_tables_have_workspace_id_column():
    """Tenant-owned tables include workspace_id for isolation."""
    import_all_models()
    tenant_tables = CORE_TABLES - {"users", "workspaces"}
    for table_name in tenant_tables:
        table = Base.metadata.tables[table_name]
        assert "workspace_id" in table.columns
