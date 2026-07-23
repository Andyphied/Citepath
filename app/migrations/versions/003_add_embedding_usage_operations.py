"""Add granular embedding usage operation enum values.

Revision ID: 003_embedding_usage_ops
Revises: 002_add_workspace_slug
Create Date: 2026-07-16

Note: revision id kept ≤32 chars (alembic_version.version_num VARCHAR(32)).

"""

from typing import Sequence, Union

from alembic import op

revision: str = "003_embedding_usage_ops"
down_revision: Union[str, None] = "002_add_workspace_slug"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # PostgreSQL requires committing new enum values before they can be used in DML.
    with op.get_context().autocommit_block():
        op.execute(
            "ALTER TYPE usage_operation ADD VALUE IF NOT EXISTS 'embedding_document'"
        )
        op.execute(
            "ALTER TYPE usage_operation ADD VALUE IF NOT EXISTS 'embedding_query'"
        )

    op.execute(
        """
        UPDATE usage_events
        SET operation = 'embedding_document'
        WHERE operation = 'embedding'
        """
    )


def downgrade() -> None:
    op.execute(
        """
        UPDATE usage_events
        SET operation = 'embedding'
        WHERE operation IN ('embedding_document', 'embedding_query')
        """
    )
    # PostgreSQL does not support removing enum values; legacy `embedding` remains.
