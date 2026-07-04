"""Workspace domain service."""

from app.modules.users.models import User
from app.modules.workspaces.exceptions import DuplicateSlugError, InvalidSlugError
from app.modules.workspaces.repository import WorkspaceRepository
from app.modules.workspaces.schemas import WorkspaceResponse
from app.modules.workspaces.slug import (
    append_slug_suffix,
    generate_slug_from_name,
    is_valid_slug,
)


class WorkspaceService:
    """Workspace creation and membership orchestration."""

    def __init__(self, workspace_repository: WorkspaceRepository) -> None:
        self._workspace_repository = workspace_repository

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
