"""Initial core schema with pgvector.

Revision ID: 001_initial_core_schema
Revises:
Create Date: 2026-07-03

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "001_initial_core_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    workspace_role = postgresql.ENUM(
        "owner",
        "admin",
        "member",
        "viewer",
        name="workspace_role",
        create_type=False,
    )
    document_status = postgresql.ENUM(
        "uploaded",
        "processing",
        "indexed",
        "failed",
        name="document_status",
        create_type=False,
    )
    ingestion_job_status = postgresql.ENUM(
        "pending",
        "processing",
        "completed",
        "failed",
        name="ingestion_job_status",
        create_type=False,
    )
    conversation_mode = postgresql.ENUM(
        "rag",
        "agent",
        name="conversation_mode",
        create_type=False,
    )
    message_role = postgresql.ENUM(
        "user",
        "assistant",
        "system",
        name="message_role",
        create_type=False,
    )
    agent_run_status = postgresql.ENUM(
        "running",
        "completed",
        "failed",
        name="agent_run_status",
        create_type=False,
    )
    agent_tool_call_status = postgresql.ENUM(
        "success",
        "failed",
        name="agent_tool_call_status",
        create_type=False,
    )
    usage_operation = postgresql.ENUM(
        "chat_completion",
        "embedding",
        "agent_step",
        name="usage_operation",
        create_type=False,
    )
    usage_event_status = postgresql.ENUM(
        "success",
        "failed",
        name="usage_event_status",
        create_type=False,
    )

    workspace_role.create(op.get_bind(), checkfirst=True)
    document_status.create(op.get_bind(), checkfirst=True)
    ingestion_job_status.create(op.get_bind(), checkfirst=True)
    conversation_mode.create(op.get_bind(), checkfirst=True)
    message_role.create(op.get_bind(), checkfirst=True)
    agent_run_status.create(op.get_bind(), checkfirst=True)
    agent_tool_call_status.create(op.get_bind(), checkfirst=True)
    usage_operation.create(op.get_bind(), checkfirst=True)
    usage_event_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "users",
        sa.Column(
            "id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )

    op.create_table(
        "workspaces",
        sa.Column(
            "id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("created_by", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_workspaces_created_by", "workspaces", ["created_by"], unique=False)

    op.create_table(
        "workspace_members",
        sa.Column(
            "id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("workspace_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("role", workspace_role, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "workspace_id",
            "user_id",
            name="uq_workspace_members_workspace_user",
        ),
    )
    op.create_index(
        "ix_workspace_members_user_id",
        "workspace_members",
        ["user_id"],
        unique=False,
    )

    op.create_table(
        "documents",
        sa.Column(
            "id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("workspace_id", sa.UUID(), nullable=False),
        sa.Column("uploaded_by", sa.UUID(), nullable=True),
        sa.Column("title", sa.String(length=512), nullable=True),
        sa.Column("source_type", sa.String(length=64), nullable=True),
        sa.Column("file_type", sa.String(length=16), nullable=True),
        sa.Column("storage_key", sa.String(length=1024), nullable=True),
        sa.Column("status", document_status, nullable=False),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["uploaded_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_documents_workspace_id_created_at",
        "documents",
        ["workspace_id", sa.text("created_at DESC")],
        unique=False,
    )
    op.create_index(
        "ix_documents_workspace_id_status",
        "documents",
        ["workspace_id", "status"],
        unique=False,
    )

    op.create_table(
        "document_chunks",
        sa.Column(
            "id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("workspace_id", sa.UUID(), nullable=False),
        sa.Column("document_id", sa.UUID(), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("embedding", Vector(1536), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("embedding_model", sa.String(length=128), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"]),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "workspace_id",
            "document_id",
            "chunk_index",
            name="uq_document_chunks_workspace_document_index",
        ),
    )
    op.create_index(
        "ix_document_chunks_workspace_id_document_id",
        "document_chunks",
        ["workspace_id", "document_id"],
        unique=False,
    )
    op.execute(
        """
        CREATE INDEX ix_document_chunks_embedding_hnsw
        ON document_chunks
        USING hnsw (embedding vector_cosine_ops)
        """
    )

    op.create_table(
        "ingestion_jobs",
        sa.Column(
            "id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("workspace_id", sa.UUID(), nullable=False),
        sa.Column("document_id", sa.UUID(), nullable=False),
        sa.Column("status", ingestion_job_status, nullable=False),
        sa.Column("attempt_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"]),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_ingestion_jobs_document_id",
        "ingestion_jobs",
        ["document_id"],
        unique=False,
    )
    op.create_index(
        "ix_ingestion_jobs_workspace_id_status_created_at",
        "ingestion_jobs",
        ["workspace_id", "status", sa.text("created_at DESC")],
        unique=False,
    )

    op.create_table(
        "conversations",
        sa.Column(
            "id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("workspace_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("title", sa.String(length=512), nullable=True),
        sa.Column("mode", conversation_mode, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_conversations_workspace_id_user_id_created_at",
        "conversations",
        ["workspace_id", "user_id", sa.text("created_at DESC")],
        unique=False,
    )

    op.create_table(
        "messages",
        sa.Column(
            "id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("workspace_id", sa.UUID(), nullable=False),
        sa.Column("conversation_id", sa.UUID(), nullable=False),
        sa.Column("role", message_role, nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"]),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_messages_conversation_id_created_at",
        "messages",
        ["conversation_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_messages_workspace_id_created_at",
        "messages",
        ["workspace_id", sa.text("created_at DESC")],
        unique=False,
    )

    op.create_table(
        "agent_runs",
        sa.Column(
            "id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("workspace_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("objective", sa.Text(), nullable=False),
        sa.Column("status", agent_run_status, nullable=False),
        sa.Column("result", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("step_count", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_agent_runs_workspace_id_created_at",
        "agent_runs",
        ["workspace_id", sa.text("created_at DESC")],
        unique=False,
    )
    op.create_index(
        "ix_agent_runs_workspace_id_status",
        "agent_runs",
        ["workspace_id", "status"],
        unique=False,
    )

    op.create_table(
        "agent_tool_calls",
        sa.Column(
            "id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("workspace_id", sa.UUID(), nullable=False),
        sa.Column("agent_run_id", sa.UUID(), nullable=False),
        sa.Column("tool_name", sa.String(length=128), nullable=False),
        sa.Column("input", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("output", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("status", agent_tool_call_status, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["agent_run_id"], ["agent_runs.id"]),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_agent_tool_calls_agent_run_id_created_at",
        "agent_tool_calls",
        ["agent_run_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_agent_tool_calls_workspace_id_created_at",
        "agent_tool_calls",
        ["workspace_id", sa.text("created_at DESC")],
        unique=False,
    )

    op.create_table(
        "usage_events",
        sa.Column(
            "id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("workspace_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=True),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("model", sa.String(length=128), nullable=False),
        sa.Column("operation", usage_operation, nullable=False),
        sa.Column("prompt_tokens", sa.Integer(), server_default="0", nullable=False),
        sa.Column("completion_tokens", sa.Integer(), server_default="0", nullable=False),
        sa.Column("embedding_tokens", sa.Integer(), server_default="0", nullable=False),
        sa.Column("estimated_cost_usd", sa.Numeric(precision=10, scale=6), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("status", usage_event_status, nullable=False),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_usage_events_workspace_id_created_at",
        "usage_events",
        ["workspace_id", sa.text("created_at DESC")],
        unique=False,
    )
    op.create_index(
        "ix_usage_events_workspace_id_operation_created_at",
        "usage_events",
        ["workspace_id", "operation", sa.text("created_at DESC")],
        unique=False,
    )

    op.create_table(
        "audit_logs",
        sa.Column(
            "id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("workspace_id", sa.UUID(), nullable=False),
        sa.Column("actor_user_id", sa.UUID(), nullable=True),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("ip_address", sa.String(length=45), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_audit_logs_workspace_id_created_at",
        "audit_logs",
        ["workspace_id", sa.text("created_at DESC")],
        unique=False,
    )
    op.create_index(
        "ix_audit_logs_workspace_id_event_type_created_at",
        "audit_logs",
        ["workspace_id", "event_type", sa.text("created_at DESC")],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_audit_logs_workspace_id_event_type_created_at",
        table_name="audit_logs",
    )
    op.drop_index("ix_audit_logs_workspace_id_created_at", table_name="audit_logs")
    op.drop_table("audit_logs")

    op.drop_index(
        "ix_usage_events_workspace_id_operation_created_at",
        table_name="usage_events",
    )
    op.drop_index("ix_usage_events_workspace_id_created_at", table_name="usage_events")
    op.drop_table("usage_events")

    op.drop_index(
        "ix_agent_tool_calls_workspace_id_created_at",
        table_name="agent_tool_calls",
    )
    op.drop_index(
        "ix_agent_tool_calls_agent_run_id_created_at",
        table_name="agent_tool_calls",
    )
    op.drop_table("agent_tool_calls")

    op.drop_index("ix_agent_runs_workspace_id_status", table_name="agent_runs")
    op.drop_index("ix_agent_runs_workspace_id_created_at", table_name="agent_runs")
    op.drop_table("agent_runs")

    op.drop_index("ix_messages_workspace_id_created_at", table_name="messages")
    op.drop_index("ix_messages_conversation_id_created_at", table_name="messages")
    op.drop_table("messages")

    op.drop_index(
        "ix_conversations_workspace_id_user_id_created_at",
        table_name="conversations",
    )
    op.drop_table("conversations")

    op.drop_index(
        "ix_ingestion_jobs_workspace_id_status_created_at",
        table_name="ingestion_jobs",
    )
    op.drop_index("ix_ingestion_jobs_document_id", table_name="ingestion_jobs")
    op.drop_table("ingestion_jobs")

    op.execute("DROP INDEX IF EXISTS ix_document_chunks_embedding_hnsw")
    op.drop_index(
        "ix_document_chunks_workspace_id_document_id",
        table_name="document_chunks",
    )
    op.drop_table("document_chunks")

    op.drop_index("ix_documents_workspace_id_status", table_name="documents")
    op.drop_index("ix_documents_workspace_id_created_at", table_name="documents")
    op.drop_table("documents")

    op.drop_index("ix_workspace_members_user_id", table_name="workspace_members")
    op.drop_table("workspace_members")

    op.drop_index("ix_workspaces_created_by", table_name="workspaces")
    op.drop_table("workspaces")

    op.drop_table("users")

    for enum_name in (
        "usage_event_status",
        "usage_operation",
        "agent_tool_call_status",
        "agent_run_status",
        "message_role",
        "conversation_mode",
        "ingestion_job_status",
        "document_status",
        "workspace_role",
    ):
        op.execute(f"DROP TYPE IF EXISTS {enum_name}")
