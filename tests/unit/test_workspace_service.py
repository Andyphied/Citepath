"""Unit tests for WorkspaceService."""

from datetime import UTC, datetime
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from app.infrastructure.db.enums import WorkspaceRole
from app.modules.users.models import User
from app.modules.workspaces.exceptions import (
    DuplicateSlugError,
    InvalidSlugError,
    WorkspaceForbiddenError,
)
from app.modules.workspaces.models import Workspace, WorkspaceMember
from app.modules.workspaces.service import WorkspaceService


def _user() -> User:
    return User(
        id=uuid4(),
        email="owner@example.com",
        password_hash="hash",
        name="Owner",
    )


def _workspace(**overrides) -> Workspace:
    defaults = {
        "id": uuid4(),
        "name": "Northstar Cloud",
        "slug": "northstar-cloud",
        "created_by": uuid4(),
        "created_at": datetime.now(UTC),
    }
    defaults.update(overrides)
    return Workspace(**defaults)


def test_create_workspace_auto_generates_slug() -> None:
    user = _user()
    workspace = _workspace(created_by=user.id)
    repository = MagicMock()
    repository.slug_exists.return_value = False
    repository.create_workspace_with_owner.return_value = workspace

    result = WorkspaceService(repository).create_workspace(
        user=user,
        name="Northstar Cloud",
        slug=None,
    )

    repository.create_workspace_with_owner.assert_called_once_with(
        name="Northstar Cloud",
        slug="northstar-cloud",
        created_by=user.id,
    )
    assert result.slug == "northstar-cloud"
    assert result.name == "Northstar Cloud"


def test_create_workspace_uses_provided_slug() -> None:
    user = _user()
    workspace = _workspace(
        name="Platform Team",
        slug="platform-team",
        created_by=user.id,
    )
    repository = MagicMock()
    repository.slug_exists.return_value = False
    repository.create_workspace_with_owner.return_value = workspace

    result = WorkspaceService(repository).create_workspace(
        user=user,
        name="Platform Team",
        slug="platform-team",
    )

    assert result.slug == "platform-team"


def test_create_workspace_raises_duplicate_slug_for_explicit_slug() -> None:
    user = _user()
    repository = MagicMock()
    repository.slug_exists.return_value = True

    with pytest.raises(DuplicateSlugError):
        WorkspaceService(repository).create_workspace(
            user=user,
            name="Platform Team",
            slug="platform-team",
        )


def test_create_workspace_raises_invalid_slug() -> None:
    user = _user()
    repository = MagicMock()

    with pytest.raises(InvalidSlugError):
        WorkspaceService(repository).create_workspace(
            user=user,
            name="Platform Team",
            slug="Invalid Slug",
        )


def test_create_workspace_appends_suffix_for_generated_slug_collision() -> None:
    user = _user()
    workspace = _workspace(
        slug="northstar-cloud-2",
        created_by=user.id,
    )
    repository = MagicMock()
    repository.slug_exists.side_effect = [True, False]
    repository.create_workspace_with_owner.return_value = workspace

    result = WorkspaceService(repository).create_workspace(
        user=user,
        name="Northstar Cloud",
        slug=None,
    )

    assert result.slug == "northstar-cloud-2"
    repository.create_workspace_with_owner.assert_called_once_with(
        name="Northstar Cloud",
        slug="northstar-cloud-2",
        created_by=user.id,
    )


def test_create_workspace_assigns_owner_role_via_repository() -> None:
    """Owner membership is created atomically in the repository layer."""
    user = _user()
    workspace = _workspace(created_by=user.id)
    repository = MagicMock()
    repository.slug_exists.return_value = False
    repository.create_workspace_with_owner.return_value = workspace

    WorkspaceService(repository).create_workspace(
        user=user,
        name="Northstar Cloud",
        slug=None,
    )

    repository.create_workspace_with_owner.assert_called_once()
    assert repository.create_workspace_with_owner.call_args.kwargs["created_by"] == user.id


def test_list_workspaces_returns_memberships_with_roles() -> None:
    user = _user()
    workspace_a = _workspace(name="Team A", slug="team-a", created_by=user.id)
    workspace_b = _workspace(name="Team B", slug="team-b", created_by=user.id)
    repository = MagicMock()
    repository.list_for_user.return_value = [
        (workspace_a, WorkspaceRole.OWNER),
        (workspace_b, WorkspaceRole.MEMBER),
    ]

    result = WorkspaceService(repository).list_workspaces(user=user)

    repository.list_for_user.assert_called_once_with(user.id)
    assert len(result.items) == 2
    assert result.items[0].id == workspace_a.id
    assert result.items[0].name == "Team A"
    assert result.items[0].role == "owner"
    assert result.items[1].role == "member"


def test_list_workspaces_returns_empty_list_when_no_memberships() -> None:
    user = _user()
    repository = MagicMock()
    repository.list_for_user.return_value = []

    result = WorkspaceService(repository).list_workspaces(user=user)

    assert result.items == []


def test_get_workspace_returns_detail_for_member() -> None:
    user = _user()
    workspace = _workspace(created_by=user.id)
    membership = WorkspaceMember(
        workspace_id=workspace.id,
        user_id=user.id,
        role=WorkspaceRole.OWNER,
    )
    repository = MagicMock()
    repository.get_member.return_value = membership
    repository.get_by_id.return_value = workspace
    repository.count_members.return_value = 3

    result = WorkspaceService(repository).get_workspace(
        user=user,
        workspace_id=workspace.id,
    )

    assert result.id == workspace.id
    assert result.name == workspace.name
    assert result.member_count == 3
    assert result.created_at == workspace.created_at


def test_get_workspace_raises_forbidden_when_not_member() -> None:
    user = _user()
    repository = MagicMock()
    repository.get_member.return_value = None

    with pytest.raises(WorkspaceForbiddenError):
        WorkspaceService(repository).get_workspace(
            user=user,
            workspace_id=uuid4(),
        )


def test_get_workspace_raises_forbidden_when_workspace_missing() -> None:
    user = _user()
    membership = WorkspaceMember(
        workspace_id=uuid4(),
        user_id=user.id,
        role=WorkspaceRole.MEMBER,
    )
    repository = MagicMock()
    repository.get_member.return_value = membership
    repository.get_by_id.return_value = None

    with pytest.raises(WorkspaceForbiddenError):
        WorkspaceService(repository).get_workspace(
            user=user,
            workspace_id=membership.workspace_id,
        )
