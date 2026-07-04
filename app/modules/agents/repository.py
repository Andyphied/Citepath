"""Agent run persistence with workspace scoping."""

from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.infrastructure.db.enums import AgentRunStatus
from app.infrastructure.db.scoped_repository import WorkspaceScopedRepository
from app.modules.agents.models import AgentRun


class AgentRepository(WorkspaceScopedRepository[AgentRun]):
    """Workspace-scoped agent run persistence."""

    _model = AgentRun

    def __init__(self, session: Session) -> None:
        super().__init__(session)

    def create_run(
        self,
        *,
        workspace_id: UUID,
        user_id: UUID,
        objective: str,
        status: AgentRunStatus,
        result: dict[str, Any] | None = None,
        step_count: int | None = None,
    ) -> AgentRun:
        """Persist an agent run in the given workspace."""
        run = AgentRun(
            workspace_id=workspace_id,
            user_id=user_id,
            objective=objective,
            status=status,
            result=result,
            step_count=step_count,
        )
        self._session.add(run)
        self._session.commit()
        self._session.refresh(run)
        return run

    def get_run_by_id(
        self,
        *,
        workspace_id: UUID,
        id: UUID,
    ) -> AgentRun | None:
        """Return an agent run by id within the given workspace, or None."""
        return self.get_by_id(workspace_id=workspace_id, id=id)
