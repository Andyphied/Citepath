"""Workspace routes."""

from uuid import UUID

from fastapi import APIRouter, status

from app.api.deps import (
    CurrentUserDep,
    RequireManageMembersDep,
    WorkspaceContextDep,
    WorkspaceServiceDep,
)
from app.modules.workspaces.schemas import (
    CreateWorkspaceRequest,
    InviteMemberRequest,
    UpdateMemberRoleRequest,
    WorkspaceDetailResponse,
    WorkspaceListResponse,
    WorkspaceMemberResponse,
    WorkspaceResponse,
)

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


@router.get(
    "",
    response_model=WorkspaceListResponse,
)
def list_workspaces(
    current_user: CurrentUserDep,
    workspace_service: WorkspaceServiceDep,
) -> WorkspaceListResponse:
    """List workspaces where the authenticated user is a member."""
    return workspace_service.list_workspaces(user=current_user)


@router.get(
    "/{workspace_id}",
    response_model=WorkspaceDetailResponse,
)
def get_workspace(
    workspace_context: WorkspaceContextDep,
    workspace_service: WorkspaceServiceDep,
) -> WorkspaceDetailResponse:
    """Return workspace details when the caller is a member."""
    return workspace_service.get_workspace(context=workspace_context)


@router.post(
    "/{workspace_id}/members",
    response_model=WorkspaceMemberResponse,
    status_code=status.HTTP_201_CREATED,
)
def invite_member(
    workspace_context: RequireManageMembersDep,
    body: InviteMemberRequest,
    workspace_service: WorkspaceServiceDep,
) -> WorkspaceMemberResponse:
    """Add an existing user to a workspace by email (Owner/Admin only)."""
    return workspace_service.invite_member(
        context=workspace_context,
        email=body.email,
        role=body.role,
    )


@router.patch(
    "/{workspace_id}/members/{user_id}",
    response_model=WorkspaceMemberResponse,
)
def update_member_role(
    workspace_context: RequireManageMembersDep,
    user_id: UUID,
    body: UpdateMemberRoleRequest,
    workspace_service: WorkspaceServiceDep,
) -> WorkspaceMemberResponse:
    """Change a workspace member's role (Owner/Admin only)."""
    return workspace_service.update_member_role(
        context=workspace_context,
        target_user_id=user_id,
        role=body.role,
    )


@router.delete(
    "/{workspace_id}/members/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def remove_member(
    workspace_context: RequireManageMembersDep,
    user_id: UUID,
    workspace_service: WorkspaceServiceDep,
) -> None:
    """Remove a member from a workspace (Owner/Admin only)."""
    workspace_service.remove_member(
        context=workspace_context,
        target_user_id=user_id,
    )


@router.post(
    "",
    response_model=WorkspaceResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_workspace(
    body: CreateWorkspaceRequest,
    current_user: CurrentUserDep,
    workspace_service: WorkspaceServiceDep,
) -> WorkspaceResponse:
    """Create a workspace; the authenticated user becomes owner."""
    return workspace_service.create_workspace(
        user=current_user,
        name=body.name,
        slug=body.slug,
    )
