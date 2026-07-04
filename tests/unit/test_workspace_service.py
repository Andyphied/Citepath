"""Unit tests for WorkspaceService."""

from datetime import UTC, datetime
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from app.infrastructure.db.enums import WorkspaceRole
from app.modules.users.models import User
from app.modules.workspaces.exceptions import (
    AlreadyMemberError,
    DuplicateSlugError,
    InvalidSlugError,
    LastOwnerError,
    MemberNotFoundError,
    UserNotFoundError,
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


def _service(repository: MagicMock) -> WorkspaceService:
    return WorkspaceService(repository, MagicMock())


def test_create_workspace_auto_generates_slug() -> None:
    user = _user()
    workspace = _workspace(created_by=user.id)
    repository = MagicMock()
    repository.slug_exists.return_value = False
    repository.create_workspace_with_owner.return_value = workspace

    result = _service(repository).create_workspace(
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

    result = _service(repository).create_workspace(
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
        _service(repository).create_workspace(
            user=user,
            name="Platform Team",
            slug="platform-team",
        )


def test_create_workspace_raises_invalid_slug() -> None:
    user = _user()
    repository = MagicMock()

    with pytest.raises(InvalidSlugError):
        _service(repository).create_workspace(
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

    result = _service(repository).create_workspace(
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

    WorkspaceService(repository, MagicMock()).create_workspace(
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

    result = _service(repository).list_workspaces(user=user)

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

    result = _service(repository).list_workspaces(user=user)

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

    result = _service(repository).get_workspace(
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
        _service(repository).get_workspace(
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
        _service(repository).get_workspace(
            user=user,
            workspace_id=membership.workspace_id,
        )


def test_invite_member_success_as_owner() -> None:
    owner = _user()
    invitee = User(
        id=uuid4(),
        email="engineer@example.com",
        password_hash="hash",
        name="Engineer",
    )
    workspace_id = uuid4()
    created_at = datetime.now(UTC)
    membership = WorkspaceMember(
        workspace_id=workspace_id,
        user_id=owner.id,
        role=WorkspaceRole.OWNER,
    )
    added_member = WorkspaceMember(
        workspace_id=workspace_id,
        user_id=invitee.id,
        role=WorkspaceRole.MEMBER,
        created_at=created_at,
    )
    workspace_repository = MagicMock()
    workspace_repository.get_member.side_effect = [membership, None]
    workspace_repository.add_member.return_value = added_member
    user_repository = MagicMock()
    user_repository.get_by_email.return_value = invitee

    result = WorkspaceService(workspace_repository, user_repository).invite_member(
        user=owner,
        workspace_id=workspace_id,
        email="engineer@example.com",
        role="member",
    )

    assert result.user_id == invitee.id
    assert result.email == "engineer@example.com"
    assert result.role == "member"
    assert result.created_at == created_at
    workspace_repository.add_member.assert_called_once_with(
        workspace_id=workspace_id,
        user_id=invitee.id,
        role=WorkspaceRole.MEMBER,
    )


def test_invite_member_success_as_admin() -> None:
    admin = _user()
    invitee = User(
        id=uuid4(),
        email="viewer@example.com",
        password_hash="hash",
        name="Viewer",
    )
    workspace_id = uuid4()
    admin_membership = WorkspaceMember(
        workspace_id=workspace_id,
        user_id=admin.id,
        role=WorkspaceRole.ADMIN,
    )
    added_member = WorkspaceMember(
        workspace_id=workspace_id,
        user_id=invitee.id,
        role=WorkspaceRole.VIEWER,
        created_at=datetime.now(UTC),
    )
    workspace_repository = MagicMock()
    workspace_repository.get_member.side_effect = [admin_membership, None]
    workspace_repository.add_member.return_value = added_member
    user_repository = MagicMock()
    user_repository.get_by_email.return_value = invitee

    result = WorkspaceService(workspace_repository, user_repository).invite_member(
        user=admin,
        workspace_id=workspace_id,
        email="viewer@example.com",
        role="viewer",
    )

    assert result.role == "viewer"


def test_invite_member_raises_forbidden_for_viewer() -> None:
    viewer = _user()
    workspace_id = uuid4()
    membership = WorkspaceMember(
        workspace_id=workspace_id,
        user_id=viewer.id,
        role=WorkspaceRole.VIEWER,
    )
    workspace_repository = MagicMock()
    workspace_repository.get_member.return_value = membership
    user_repository = MagicMock()

    with pytest.raises(WorkspaceForbiddenError):
        WorkspaceService(workspace_repository, user_repository).invite_member(
            user=viewer,
            workspace_id=workspace_id,
            email="engineer@example.com",
            role="member",
        )


def test_invite_member_raises_forbidden_for_member() -> None:
    member_user = _user()
    workspace_id = uuid4()
    membership = WorkspaceMember(
        workspace_id=workspace_id,
        user_id=member_user.id,
        role=WorkspaceRole.MEMBER,
    )
    workspace_repository = MagicMock()
    workspace_repository.get_member.return_value = membership
    user_repository = MagicMock()

    with pytest.raises(WorkspaceForbiddenError):
        WorkspaceService(workspace_repository, user_repository).invite_member(
            user=member_user,
            workspace_id=workspace_id,
            email="engineer@example.com",
            role="member",
        )


def test_invite_member_raises_forbidden_when_not_member() -> None:
    user = _user()
    workspace_repository = MagicMock()
    workspace_repository.get_member.return_value = None
    user_repository = MagicMock()

    with pytest.raises(WorkspaceForbiddenError):
        WorkspaceService(workspace_repository, user_repository).invite_member(
            user=user,
            workspace_id=uuid4(),
            email="engineer@example.com",
            role="member",
        )


def test_invite_member_raises_forbidden_when_admin_assigns_owner() -> None:
    admin = _user()
    workspace_id = uuid4()
    admin_membership = WorkspaceMember(
        workspace_id=workspace_id,
        user_id=admin.id,
        role=WorkspaceRole.ADMIN,
    )
    workspace_repository = MagicMock()
    workspace_repository.get_member.return_value = admin_membership
    user_repository = MagicMock()

    with pytest.raises(WorkspaceForbiddenError):
        WorkspaceService(workspace_repository, user_repository).invite_member(
            user=admin,
            workspace_id=workspace_id,
            email="engineer@example.com",
            role="owner",
        )


def test_invite_member_raises_user_not_found() -> None:
    owner = _user()
    workspace_id = uuid4()
    membership = WorkspaceMember(
        workspace_id=workspace_id,
        user_id=owner.id,
        role=WorkspaceRole.OWNER,
    )
    workspace_repository = MagicMock()
    workspace_repository.get_member.return_value = membership
    user_repository = MagicMock()
    user_repository.get_by_email.return_value = None

    with pytest.raises(UserNotFoundError):
        WorkspaceService(workspace_repository, user_repository).invite_member(
            user=owner,
            workspace_id=workspace_id,
            email="unknown@example.com",
            role="member",
        )


def test_invite_member_raises_already_member() -> None:
    owner = _user()
    invitee = User(
        id=uuid4(),
        email="engineer@example.com",
        password_hash="hash",
        name="Engineer",
    )
    workspace_id = uuid4()
    owner_membership = WorkspaceMember(
        workspace_id=workspace_id,
        user_id=owner.id,
        role=WorkspaceRole.OWNER,
    )
    existing_membership = WorkspaceMember(
        workspace_id=workspace_id,
        user_id=invitee.id,
        role=WorkspaceRole.MEMBER,
    )
    workspace_repository = MagicMock()
    workspace_repository.get_member.side_effect = [owner_membership, existing_membership]
    user_repository = MagicMock()
    user_repository.get_by_email.return_value = invitee

    with pytest.raises(AlreadyMemberError):
        WorkspaceService(workspace_repository, user_repository).invite_member(
            user=owner,
            workspace_id=workspace_id,
            email="engineer@example.com",
            role="member",
        )


def test_update_member_role_success_as_owner() -> None:
    owner = _user()
    target = User(
        id=uuid4(),
        email="member@example.com",
        password_hash="hash",
        name="Member",
    )
    workspace_id = uuid4()
    created_at = datetime.now(UTC)
    owner_membership = WorkspaceMember(
        workspace_id=workspace_id,
        user_id=owner.id,
        role=WorkspaceRole.OWNER,
    )
    target_membership = WorkspaceMember(
        workspace_id=workspace_id,
        user_id=target.id,
        role=WorkspaceRole.MEMBER,
        created_at=created_at,
    )
    updated_member = WorkspaceMember(
        workspace_id=workspace_id,
        user_id=target.id,
        role=WorkspaceRole.VIEWER,
        created_at=created_at,
    )
    workspace_repository = MagicMock()
    workspace_repository.get_member.side_effect = [
        owner_membership,
        target_membership,
    ]
    workspace_repository.update_member_role.return_value = updated_member
    user_repository = MagicMock()
    user_repository.get_by_id.return_value = target

    result = WorkspaceService(
        workspace_repository, user_repository
    ).update_member_role(
        user=owner,
        workspace_id=workspace_id,
        target_user_id=target.id,
        role="viewer",
    )

    assert result.user_id == target.id
    assert result.email == "member@example.com"
    assert result.role == "viewer"
    workspace_repository.update_member_role.assert_called_once_with(
        workspace_id=workspace_id,
        user_id=target.id,
        role=WorkspaceRole.VIEWER,
    )


def test_update_member_role_raises_member_not_found() -> None:
    owner = _user()
    workspace_id = uuid4()
    owner_membership = WorkspaceMember(
        workspace_id=workspace_id,
        user_id=owner.id,
        role=WorkspaceRole.OWNER,
    )
    workspace_repository = MagicMock()
    workspace_repository.get_member.side_effect = [owner_membership, None]
    user_repository = MagicMock()

    with pytest.raises(MemberNotFoundError):
        WorkspaceService(workspace_repository, user_repository).update_member_role(
            user=owner,
            workspace_id=workspace_id,
            target_user_id=uuid4(),
            role="viewer",
        )


def test_update_member_role_raises_forbidden_for_viewer() -> None:
    viewer = _user()
    workspace_id = uuid4()
    membership = WorkspaceMember(
        workspace_id=workspace_id,
        user_id=viewer.id,
        role=WorkspaceRole.VIEWER,
    )
    workspace_repository = MagicMock()
    workspace_repository.get_member.return_value = membership
    user_repository = MagicMock()

    with pytest.raises(WorkspaceForbiddenError):
        WorkspaceService(workspace_repository, user_repository).update_member_role(
            user=viewer,
            workspace_id=workspace_id,
            target_user_id=uuid4(),
            role="viewer",
        )


def test_update_member_role_admin_cannot_modify_owner() -> None:
    admin = _user()
    owner_target = User(
        id=uuid4(),
        email="owner@example.com",
        password_hash="hash",
        name="Other Owner",
    )
    workspace_id = uuid4()
    admin_membership = WorkspaceMember(
        workspace_id=workspace_id,
        user_id=admin.id,
        role=WorkspaceRole.ADMIN,
    )
    owner_membership = WorkspaceMember(
        workspace_id=workspace_id,
        user_id=owner_target.id,
        role=WorkspaceRole.OWNER,
    )
    workspace_repository = MagicMock()
    workspace_repository.get_member.side_effect = [
        admin_membership,
        owner_membership,
    ]
    user_repository = MagicMock()

    with pytest.raises(WorkspaceForbiddenError):
        WorkspaceService(workspace_repository, user_repository).update_member_role(
            user=admin,
            workspace_id=workspace_id,
            target_user_id=owner_target.id,
            role="admin",
        )


def test_update_member_role_admin_cannot_assign_owner() -> None:
    admin = _user()
    target = User(
        id=uuid4(),
        email="member@example.com",
        password_hash="hash",
        name="Member",
    )
    workspace_id = uuid4()
    admin_membership = WorkspaceMember(
        workspace_id=workspace_id,
        user_id=admin.id,
        role=WorkspaceRole.ADMIN,
    )
    target_membership = WorkspaceMember(
        workspace_id=workspace_id,
        user_id=target.id,
        role=WorkspaceRole.MEMBER,
    )
    workspace_repository = MagicMock()
    workspace_repository.get_member.side_effect = [
        admin_membership,
        target_membership,
    ]
    user_repository = MagicMock()

    with pytest.raises(WorkspaceForbiddenError):
        WorkspaceService(workspace_repository, user_repository).update_member_role(
            user=admin,
            workspace_id=workspace_id,
            target_user_id=target.id,
            role="owner",
        )


def test_update_member_role_raises_last_owner_on_self_demotion() -> None:
    owner = _user()
    workspace_id = uuid4()
    owner_membership = WorkspaceMember(
        workspace_id=workspace_id,
        user_id=owner.id,
        role=WorkspaceRole.OWNER,
    )
    workspace_repository = MagicMock()
    workspace_repository.get_member.side_effect = [
        owner_membership,
        owner_membership,
    ]
    workspace_repository.count_owners.return_value = 1
    user_repository = MagicMock()

    with pytest.raises(LastOwnerError):
        WorkspaceService(workspace_repository, user_repository).update_member_role(
            user=owner,
            workspace_id=workspace_id,
            target_user_id=owner.id,
            role="admin",
        )


def test_remove_member_success_as_owner() -> None:
    owner = _user()
    target_id = uuid4()
    workspace_id = uuid4()
    owner_membership = WorkspaceMember(
        workspace_id=workspace_id,
        user_id=owner.id,
        role=WorkspaceRole.OWNER,
    )
    target_membership = WorkspaceMember(
        workspace_id=workspace_id,
        user_id=target_id,
        role=WorkspaceRole.MEMBER,
    )
    workspace_repository = MagicMock()
    workspace_repository.get_member.side_effect = [
        owner_membership,
        target_membership,
    ]
    user_repository = MagicMock()

    WorkspaceService(workspace_repository, user_repository).remove_member(
        user=owner,
        workspace_id=workspace_id,
        target_user_id=target_id,
    )

    workspace_repository.remove_member.assert_called_once_with(
        workspace_id=workspace_id,
        user_id=target_id,
    )


def test_remove_member_raises_member_not_found() -> None:
    owner = _user()
    workspace_id = uuid4()
    owner_membership = WorkspaceMember(
        workspace_id=workspace_id,
        user_id=owner.id,
        role=WorkspaceRole.OWNER,
    )
    workspace_repository = MagicMock()
    workspace_repository.get_member.side_effect = [owner_membership, None]
    user_repository = MagicMock()

    with pytest.raises(MemberNotFoundError):
        WorkspaceService(workspace_repository, user_repository).remove_member(
            user=owner,
            workspace_id=workspace_id,
            target_user_id=uuid4(),
        )


def test_remove_member_raises_last_owner_on_self_removal() -> None:
    owner = _user()
    workspace_id = uuid4()
    owner_membership = WorkspaceMember(
        workspace_id=workspace_id,
        user_id=owner.id,
        role=WorkspaceRole.OWNER,
    )
    workspace_repository = MagicMock()
    workspace_repository.get_member.side_effect = [
        owner_membership,
        owner_membership,
    ]
    workspace_repository.count_owners.return_value = 1
    user_repository = MagicMock()

    with pytest.raises(LastOwnerError):
        WorkspaceService(workspace_repository, user_repository).remove_member(
            user=owner,
            workspace_id=workspace_id,
            target_user_id=owner.id,
        )


def test_remove_member_self_allowed_when_another_owner_exists() -> None:
    owner = _user()
    workspace_id = uuid4()
    owner_membership = WorkspaceMember(
        workspace_id=workspace_id,
        user_id=owner.id,
        role=WorkspaceRole.OWNER,
    )
    workspace_repository = MagicMock()
    workspace_repository.get_member.side_effect = [
        owner_membership,
        owner_membership,
    ]
    workspace_repository.count_owners.return_value = 2
    user_repository = MagicMock()

    WorkspaceService(workspace_repository, user_repository).remove_member(
        user=owner,
        workspace_id=workspace_id,
        target_user_id=owner.id,
    )

    workspace_repository.remove_member.assert_called_once_with(
        workspace_id=workspace_id,
        user_id=owner.id,
    )


def test_remove_member_admin_cannot_remove_owner() -> None:
    admin = _user()
    owner_target_id = uuid4()
    workspace_id = uuid4()
    admin_membership = WorkspaceMember(
        workspace_id=workspace_id,
        user_id=admin.id,
        role=WorkspaceRole.ADMIN,
    )
    owner_membership = WorkspaceMember(
        workspace_id=workspace_id,
        user_id=owner_target_id,
        role=WorkspaceRole.OWNER,
    )
    workspace_repository = MagicMock()
    workspace_repository.get_member.side_effect = [
        admin_membership,
        owner_membership,
    ]
    user_repository = MagicMock()

    with pytest.raises(WorkspaceForbiddenError):
        WorkspaceService(workspace_repository, user_repository).remove_member(
            user=admin,
            workspace_id=workspace_id,
            target_user_id=owner_target_id,
        )
