"""Centralized workspace role permission matrix."""

import enum
from typing import Any
from uuid import UUID

from app.infrastructure.db.enums import WorkspaceRole
from app.modules.audit.repository import AuditRepository
from app.modules.workspaces.context import WorkspaceContext
from app.modules.workspaces.exceptions import WorkspaceForbiddenError

FAILED_AUTHORIZATION_EVENT = "failed_authorization"


class PermissionAction(str, enum.Enum):
    """Protected actions enforced via the workspace permission matrix."""

    DOCUMENT_MUTATE = "document_mutate"
    QUERY_RAG = "query_rag"
    RUN_AGENT = "run_agent"
    MANAGE_MEMBERS = "manage_members"
    VIEW_ADMIN_DASHBOARD = "view_admin_dashboard"
    DELETE_WORKSPACE = "delete_workspace"
    VIEW_DOCUMENTS = "view_documents"


_PERMISSION_MATRIX: dict[WorkspaceRole, frozenset[PermissionAction]] = {
    WorkspaceRole.OWNER: frozenset(
        {
            PermissionAction.DOCUMENT_MUTATE,
            PermissionAction.QUERY_RAG,
            PermissionAction.RUN_AGENT,
            PermissionAction.MANAGE_MEMBERS,
            PermissionAction.VIEW_ADMIN_DASHBOARD,
            PermissionAction.DELETE_WORKSPACE,
            PermissionAction.VIEW_DOCUMENTS,
        }
    ),
    WorkspaceRole.ADMIN: frozenset(
        {
            PermissionAction.DOCUMENT_MUTATE,
            PermissionAction.QUERY_RAG,
            PermissionAction.RUN_AGENT,
            PermissionAction.MANAGE_MEMBERS,
            PermissionAction.VIEW_ADMIN_DASHBOARD,
            PermissionAction.VIEW_DOCUMENTS,
        }
    ),
    WorkspaceRole.MEMBER: frozenset(
        {
            PermissionAction.DOCUMENT_MUTATE,
            PermissionAction.QUERY_RAG,
            PermissionAction.RUN_AGENT,
            PermissionAction.VIEW_DOCUMENTS,
        }
    ),
    WorkspaceRole.VIEWER: frozenset(
        {
            PermissionAction.QUERY_RAG,
            PermissionAction.RUN_AGENT,
            PermissionAction.VIEW_DOCUMENTS,
        }
    ),
}


class PermissionService:
    """Evaluate workspace role permissions and audit denials."""

    def __init__(self, audit_repository: AuditRepository | None = None) -> None:
        self._audit_repository = audit_repository

    def is_allowed(
        self,
        context: WorkspaceContext,
        action: PermissionAction,
    ) -> bool:
        """Return True when the caller's role may perform the action."""
        allowed_actions = _PERMISSION_MATRIX.get(context.role, frozenset())
        return action in allowed_actions

    def require(
        self,
        context: WorkspaceContext,
        action: PermissionAction,
        *,
        ip_address: str | None = None,
    ) -> None:
        """Raise WorkspaceForbiddenError when the action is not permitted."""
        if self.is_allowed(context, action):
            return

        self.record_authorization_failure(
            workspace_id=context.workspace_id,
            user_id=context.user_id,
            action=action,
            role=context.role,
            ip_address=ip_address,
        )
        raise WorkspaceForbiddenError()

    def record_authorization_failure(
        self,
        *,
        workspace_id: UUID,
        user_id: UUID,
        action: PermissionAction,
        role: WorkspaceRole | None = None,
        ip_address: str | None = None,
        reason: str | None = None,
    ) -> None:
        """Persist a failed_authorization audit event for a denied action."""
        if self._audit_repository is None:
            return

        metadata: dict[str, Any] = {"action": action.value}
        if role is not None:
            metadata["role"] = role.value
        if reason is not None:
            metadata["reason"] = reason

        self._audit_repository.create(
            workspace_id=workspace_id,
            actor_user_id=user_id,
            event_type=FAILED_AUTHORIZATION_EVENT,
            metadata=metadata,
            ip_address=ip_address,
        )
