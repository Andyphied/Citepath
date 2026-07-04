"""Workspace-scoped repository base for tenant-owned entities."""

from typing import Generic, TypeVar
from uuid import UUID

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.infrastructure.db.base import Base

ModelT = TypeVar("ModelT", bound=Base)


class WorkspaceScopedRepository(Generic[ModelT]):
    """Base repository that requires workspace_id on tenant-owned queries."""

    _model: type[ModelT]

    def __init__(self, session: Session) -> None:
        self._session = session

    def _scoped_filter(
        self,
        stmt: Select[tuple[ModelT]],
        workspace_id: UUID,
    ) -> Select[tuple[ModelT]]:
        """Apply workspace_id predicate to a select statement."""
        return stmt.where(self._model.workspace_id == workspace_id)

    def get_by_id(self, *, workspace_id: UUID, id: UUID) -> ModelT | None:
        """Return a row by id within the given workspace, or None."""
        stmt = select(self._model).where(self._model.id == id)
        stmt = self._scoped_filter(stmt, workspace_id)
        return self._session.scalar(stmt)
