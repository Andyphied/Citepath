"""Add unique slug column to workspaces.

Revision ID: 002_add_workspace_slug
Revises: 001_initial_core_schema
Create Date: 2026-07-04

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002_add_workspace_slug"
down_revision: Union[str, None] = "001_initial_core_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "workspaces",
        sa.Column("slug", sa.String(length=128), nullable=True),
    )
    op.execute(
        """
        UPDATE workspaces
        SET slug = lower(
            regexp_replace(
                regexp_replace(trim(name), '[^a-zA-Z0-9]+', '-', 'g'),
                '(^-|-$)',
                '',
                'g'
            )
        )
        WHERE slug IS NULL
        """
    )
    op.execute(
        """
        UPDATE workspaces
        SET slug = 'workspace-' || replace(cast(id AS text), '-', '')
        WHERE slug IS NULL OR slug = ''
        """
    )
    op.alter_column("workspaces", "slug", nullable=False)
    op.create_index("ix_workspaces_slug", "workspaces", ["slug"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_workspaces_slug", table_name="workspaces")
    op.drop_column("workspaces", "slug")
