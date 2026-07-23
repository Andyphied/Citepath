"""Add document metadata filter indexes for retrieval.

Revision ID: 004_add_document_filter_indexes
Revises: 003_embedding_usage_ops
Create Date: 2026-07-23

"""

from typing import Sequence, Union

from alembic import op

revision: str = "004_add_document_filter_indexes"
down_revision: Union[str, None] = "003_embedding_usage_ops"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "ix_documents_workspace_id_file_type",
        "documents",
        ["workspace_id", "file_type"],
    )
    op.create_index(
        "ix_documents_workspace_id_source_type",
        "documents",
        ["workspace_id", "source_type"],
    )


def downgrade() -> None:
    op.drop_index("ix_documents_workspace_id_source_type", table_name="documents")
    op.drop_index("ix_documents_workspace_id_file_type", table_name="documents")
