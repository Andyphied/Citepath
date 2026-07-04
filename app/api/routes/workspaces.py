"""Workspace routes."""

from fastapi import APIRouter, status

from app.api.deps import CurrentUserDep, WorkspaceServiceDep
from app.modules.workspaces.schemas import (
    CreateWorkspaceRequest,
    WorkspaceResponse,
)

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


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
