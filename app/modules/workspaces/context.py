"""Workspace request context for RBAC enforcement."""

from dataclasses import dataclass
from uuid import UUID

from app.infrastructure.db.enums import WorkspaceRole


@dataclass(frozen=True, slots=True)
class WorkspaceContext:
    """Authenticated user's membership context within a workspace."""

    workspace_id: UUID
    user_id: UUID
    role: WorkspaceRole
