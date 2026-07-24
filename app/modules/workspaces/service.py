"""Workspace domain service."""

from uuid import UUID

from app.infrastructure.db.enums import WorkspaceRole
from app.modules.audit.repository import AuditRepository
from app.modules.users.models import User
from app.modules.users.repository import UserRepository
from app.modules.workspaces.context import WorkspaceContext
from app.modules.workspaces.exceptions import (
    AlreadyMemberError,
    DuplicateSlugError,
    InvalidSlugError,
    LastOwnerError,
    MemberNotFoundError,
    UserNotFoundError,
    WorkspaceForbiddenError,
)
from app.modules.workspaces.permissions import PermissionAction, PermissionService
from app.modules.workspaces.repository import WorkspaceRepository
from app.modules.workspaces.schemas import (
    WorkspaceDetailResponse,
    WorkspaceListItemResponse,
    WorkspaceListResponse,
    WorkspaceMemberResponse,
    WorkspaceResponse,
)
from app.modules.workspaces.slug import (
    append_slug_suffix,
    generate_slug_from_name,
    is_valid_slug,
)

MEMBER_ROLE_CHANGED_EVENT = "member.role_changed"


class WorkspaceService:
    """Workspace creation and membership orchestration."""

    def __init__(
        self,
        workspace_repository: WorkspaceRepository,
        user_repository: UserRepository,
        permission_service: PermissionService | None = None,
        audit_repository: AuditRepository | None = None,
    ) -> None:
        self._workspace_repository = workspace_repository
        self._user_repository = user_repository
        self._permission_service = permission_service or PermissionService()
        self._audit_repository = audit_repository

    def create_workspace(
        self,
        *,
        user: User,
        name: str,
        slug: str | None,
    ) -> WorkspaceResponse:
        """Create a workspace and assign the caller as owner."""
        resolved_slug = self._resolve_slug(name=name, slug=slug)
        workspace = self._workspace_repository.create_workspace_with_owner(
            name=name,
            slug=resolved_slug,
            created_by=user.id,
        )
        return WorkspaceResponse.model_validate(workspace)

    def list_workspaces(self, *, user: User) -> WorkspaceListResponse:
        """Return workspaces where the user is a member, including role."""
        rows = self._workspace_repository.list_for_user(user.id)
        items = [
            WorkspaceListItemResponse(
                id=workspace.id,
                name=workspace.name,
                role=role.value,
                created_at=workspace.created_at,
            )
            for workspace, role in rows
        ]
        return WorkspaceListResponse(items=items)

    def get_workspace(self, *, context: WorkspaceContext) -> WorkspaceDetailResponse:
        """Return workspace details for an authenticated member."""
        workspace = self._workspace_repository.get_by_id(context.workspace_id)
        if workspace is None:
            raise WorkspaceForbiddenError()

        return WorkspaceDetailResponse(
            id=workspace.id,
            name=workspace.name,
            member_count=self._workspace_repository.count_members(context.workspace_id),
            created_at=workspace.created_at,
        )

    def invite_member(
        self,
        *,
        context: WorkspaceContext,
        email: str,
        role: str,
    ) -> WorkspaceMemberResponse:
        """Add an existing user to a workspace by email (Owner/Admin only)."""
        target_role = WorkspaceRole(role)

        if (
            context.role == WorkspaceRole.ADMIN
            and target_role == WorkspaceRole.OWNER
        ):
            self._raise_admin_owner_forbidden(context=context)

        invitee = self._user_repository.get_by_email(email)
        if invitee is None:
            raise UserNotFoundError()

        existing = self._workspace_repository.get_member(
            context.workspace_id,
            invitee.id,
        )
        if existing is not None:
            raise AlreadyMemberError()

        member = self._workspace_repository.add_member(
            workspace_id=context.workspace_id,
            user_id=invitee.id,
            role=target_role,
        )
        return WorkspaceMemberResponse(
            user_id=invitee.id,
            email=invitee.email,
            role=member.role.value,
            created_at=member.created_at,
        )

    def update_member_role(
        self,
        *,
        context: WorkspaceContext,
        target_user_id: UUID,
        role: str,
        ip_address: str | None = None,
    ) -> WorkspaceMemberResponse:
        """Change a member's role (Owner/Admin only)."""
        target_membership = self._workspace_repository.get_member(
            context.workspace_id,
            target_user_id,
        )
        if target_membership is None:
            raise MemberNotFoundError()

        old_role = target_membership.role
        new_role = WorkspaceRole(role)

        if context.role == WorkspaceRole.ADMIN:
            if old_role == WorkspaceRole.OWNER:
                self._raise_admin_owner_forbidden(context=context)
            if new_role == WorkspaceRole.OWNER:
                self._raise_admin_owner_forbidden(context=context)

        if (
            old_role == WorkspaceRole.OWNER
            and new_role != WorkspaceRole.OWNER
            and self._workspace_repository.count_owners(context.workspace_id) == 1
        ):
            raise LastOwnerError()

        updated = self._workspace_repository.update_member_role(
            workspace_id=context.workspace_id,
            user_id=target_user_id,
            role=new_role,
        )
        target_user = self._user_repository.get_by_id(target_user_id)
        if target_user is None:
            raise MemberNotFoundError()

        if self._audit_repository is not None and old_role != new_role:
            self._audit_repository.create(
                workspace_id=context.workspace_id,
                actor_user_id=context.user_id,
                event_type=MEMBER_ROLE_CHANGED_EVENT,
                metadata={
                    "target_user_id": str(target_user_id),
                    "old_role": old_role.value,
                    "new_role": new_role.value,
                },
                ip_address=ip_address,
            )

        return WorkspaceMemberResponse(
            user_id=target_user.id,
            email=target_user.email,
            role=updated.role.value,
            created_at=updated.created_at,
        )

    def remove_member(
        self,
        *,
        context: WorkspaceContext,
        target_user_id: UUID,
    ) -> None:
        """Remove a member from a workspace (Owner/Admin only)."""
        target_membership = self._workspace_repository.get_member(
            context.workspace_id,
            target_user_id,
        )
        if target_membership is None:
            raise MemberNotFoundError()

        if (
            context.role == WorkspaceRole.ADMIN
            and target_membership.role == WorkspaceRole.OWNER
        ):
            self._raise_admin_owner_forbidden(context=context)

        if (
            target_membership.role == WorkspaceRole.OWNER
            and self._workspace_repository.count_owners(context.workspace_id) == 1
        ):
            raise LastOwnerError()

        self._workspace_repository.remove_member(
            workspace_id=context.workspace_id,
            user_id=target_user_id,
        )

    def _raise_admin_owner_forbidden(
        self,
        *,
        context: WorkspaceContext,
    ) -> None:
        """Record audit and raise when Admin attempts Owner escalation."""
        self._permission_service.record_authorization_failure(
            workspace_id=context.workspace_id,
            user_id=context.user_id,
            action=PermissionAction.MANAGE_MEMBERS,
            role=context.role,
            reason="admin_owner_escalation_blocked",
        )
        raise WorkspaceForbiddenError()

    def _resolve_slug(self, *, name: str, slug: str | None) -> str:
        if slug is not None:
            if not is_valid_slug(slug):
                raise InvalidSlugError()
            if self._workspace_repository.slug_exists(slug):
                raise DuplicateSlugError()
            return slug

        base_slug = generate_slug_from_name(name)
        resolved = base_slug
        counter = 2
        while self._workspace_repository.slug_exists(resolved):
            resolved = append_slug_suffix(base_slug, counter)
            counter += 1
        return resolved
