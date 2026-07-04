"""Workspace routes."""

from uuid import UUID

from fastapi import APIRouter, status

from app.api.deps import CurrentUserDep, WorkspaceServiceDep
from app.modules.workspaces.schemas import (
    CreateWorkspaceRequest,
    InviteMemberRequest,
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
    workspace_id: UUID,
    current_user: CurrentUserDep,
    workspace_service: WorkspaceServiceDep,
) -> WorkspaceDetailResponse:
    """Return workspace details when the caller is a member."""
    return workspace_service.get_workspace(
        user=current_user,
        workspace_id=workspace_id,
    )


@router.post(
    "/{workspace_id}/members",
    response_model=WorkspaceMemberResponse,
    status_code=status.HTTP_201_CREATED,
)
def invite_member(
    workspace_id: UUID,
    body: InviteMemberRequest,
    current_user: CurrentUserDep,
    workspace_service: WorkspaceServiceDep,
) -> WorkspaceMemberResponse:
    """Add an existing user to a workspace by email (Owner/Admin only)."""
    return workspace_service.invite_member(
        user=current_user,
        workspace_id=workspace_id,
        email=body.email,
        role=body.role,
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
