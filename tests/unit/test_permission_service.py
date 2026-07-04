"""Unit tests for PermissionService role matrix."""

from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from app.infrastructure.db.enums import WorkspaceRole
from app.modules.workspaces.context import WorkspaceContext
from app.modules.workspaces.exceptions import WorkspaceForbiddenError
from app.modules.workspaces.permissions import (
    FAILED_AUTHORIZATION_EVENT,
    PermissionAction,
    PermissionService,
)

_ALL_ACTIONS = tuple(PermissionAction)
_ALL_ROLES = tuple(WorkspaceRole)

_EXPECTED_MATRIX: dict[WorkspaceRole, frozenset[PermissionAction]] = {
    WorkspaceRole.OWNER: frozenset(_ALL_ACTIONS),
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


def _context(role: WorkspaceRole) -> WorkspaceContext:
    return WorkspaceContext(
        workspace_id=uuid4(),
        user_id=uuid4(),
        role=role,
    )


@pytest.mark.parametrize(
    ("role", "action"),
    [
        (role, action)
        for role in _ALL_ROLES
        for action in _ALL_ACTIONS
        if action in _EXPECTED_MATRIX[role]
    ],
)
def test_is_allowed_permitted_role_action_pairs(role, action) -> None:
    service = PermissionService()

    assert service.is_allowed(_context(role), action) is True


@pytest.mark.parametrize(
    ("role", "action"),
    [
        (role, action)
        for role in _ALL_ROLES
        for action in _ALL_ACTIONS
        if action not in _EXPECTED_MATRIX[role]
    ],
)
def test_is_allowed_denied_role_action_pairs(role, action) -> None:
    service = PermissionService()

    assert service.is_allowed(_context(role), action) is False


def test_require_raises_for_viewer_document_mutate() -> None:
    service = PermissionService()

    with pytest.raises(WorkspaceForbiddenError):
        service.require(
            _context(WorkspaceRole.VIEWER),
            PermissionAction.DOCUMENT_MUTATE,
        )


def test_require_allows_member_query_rag() -> None:
    service = PermissionService()

    service.require(_context(WorkspaceRole.MEMBER), PermissionAction.QUERY_RAG)


def test_require_allows_member_run_agent() -> None:
    service = PermissionService()

    service.require(_context(WorkspaceRole.MEMBER), PermissionAction.RUN_AGENT)


def test_require_records_failed_authorization_audit_on_deny() -> None:
    context = _context(WorkspaceRole.MEMBER)
    audit_repository = MagicMock()
    service = PermissionService(audit_repository)

    with pytest.raises(WorkspaceForbiddenError):
        service.require(context, PermissionAction.MANAGE_MEMBERS)

    audit_repository.create.assert_called_once_with(
        workspace_id=context.workspace_id,
        actor_user_id=context.user_id,
        event_type=FAILED_AUTHORIZATION_EVENT,
        metadata={
            "action": PermissionAction.MANAGE_MEMBERS.value,
            "role": WorkspaceRole.MEMBER.value,
        },
        ip_address=None,
    )


def test_require_skips_audit_when_repository_not_configured() -> None:
    service = PermissionService()

    with pytest.raises(WorkspaceForbiddenError):
        service.require(
            _context(WorkspaceRole.VIEWER),
            PermissionAction.DOCUMENT_MUTATE,
        )


def test_record_authorization_failure_supports_non_member_reason() -> None:
    workspace_id = uuid4()
    user_id = uuid4()
    audit_repository = MagicMock()
    service = PermissionService(audit_repository)

    service.record_authorization_failure(
        workspace_id=workspace_id,
        user_id=user_id,
        action=PermissionAction.MANAGE_MEMBERS,
        reason="non_member",
    )

    audit_repository.create.assert_called_once_with(
        workspace_id=workspace_id,
        actor_user_id=user_id,
        event_type=FAILED_AUTHORIZATION_EVENT,
        metadata={
            "action": PermissionAction.MANAGE_MEMBERS.value,
            "reason": "non_member",
        },
        ip_address=None,
    )
