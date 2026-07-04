"""Workspace persistence."""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.infrastructure.db.enums import WorkspaceRole
from app.modules.workspaces.exceptions import DuplicateSlugError
from app.modules.workspaces.models import Workspace, WorkspaceMember


class WorkspaceRepository:
    """Workspace and membership persistence."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def slug_exists(self, slug: str) -> bool:
        """Return True when a workspace with the slug already exists."""
        workspace_id = self._session.scalar(
            select(Workspace.id).where(Workspace.slug == slug)
        )
        return workspace_id is not None

    def list_for_user(self, user_id: UUID) -> list[tuple[Workspace, WorkspaceRole]]:
        """Return workspaces the user belongs to with their role."""
        rows = self._session.execute(
            select(Workspace, WorkspaceMember.role)
            .join(WorkspaceMember, WorkspaceMember.workspace_id == Workspace.id)
            .where(WorkspaceMember.user_id == user_id)
            .order_by(Workspace.created_at.desc())
        ).all()
        return [(workspace, role) for workspace, role in rows]

    def get_by_id(self, workspace_id: UUID) -> Workspace | None:
        """Return a workspace by id, or None when it does not exist."""
        return self._session.scalar(
            select(Workspace).where(Workspace.id == workspace_id)
        )

    def count_members(self, workspace_id: UUID) -> int:
        """Return the number of members in a workspace."""
        count = self._session.scalar(
            select(func.count())
            .select_from(WorkspaceMember)
            .where(WorkspaceMember.workspace_id == workspace_id)
        )
        return int(count or 0)

    def get_member(self, workspace_id: UUID, user_id: UUID) -> WorkspaceMember | None:
        """Return membership for a user in a workspace, or None."""
        return self._session.scalar(
            select(WorkspaceMember).where(
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.user_id == user_id,
            )
        )

    def create_workspace_with_owner(
        self,
        *,
        name: str,
        slug: str,
        created_by: UUID,
    ) -> Workspace:
        """Persist a workspace and assign the creator as owner."""
        workspace = Workspace(name=name, slug=slug, created_by=created_by)
        self._session.add(workspace)
        self._session.flush()
        member = WorkspaceMember(
            workspace_id=workspace.id,
            user_id=created_by,
            role=WorkspaceRole.OWNER,
        )
        self._session.add(member)
        try:
            self._session.commit()
        except IntegrityError:
            self._session.rollback()
            raise DuplicateSlugError from None
        self._session.refresh(workspace)
        return workspace
