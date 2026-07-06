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


def test_workspace_slug_column_matches_migration_expectations():
    """ORM metadata for workspaces.slug stays aligned with migration 002."""
    import_all_models()
    workspaces = Base.metadata.tables["workspaces"]
    slug_column = workspaces.columns["slug"]

    assert slug_column.nullable is False
    assert slug_column.type.length == 128

    slug_indexes = [
        index
        for index in workspaces.indexes
        if index.name == "ix_workspaces_slug"
    ]
    assert len(slug_indexes) == 1
    assert slug_indexes[0].unique is True
    assert list(slug_indexes[0].columns.keys()) == ["slug"]
