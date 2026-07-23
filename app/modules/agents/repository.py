"""Agent run persistence with workspace scoping."""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.infrastructure.db.enums import AgentRunStatus, AgentToolCallStatus
from app.infrastructure.db.scoped_repository import WorkspaceScopedRepository
from app.modules.agents.models import AgentRun, AgentToolCall


class AgentRepository(WorkspaceScopedRepository[AgentRun]):
    """Workspace-scoped agent run and tool call persistence."""

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

    def update_run(
        self,
        *,
        run: AgentRun,
        status: AgentRunStatus | None = None,
        result: dict[str, Any] | None = None,
        step_count: int | None = None,
        completed_at: datetime | None = None,
    ) -> AgentRun:
        """Update mutable agent run fields and commit."""
        if status is not None:
            run.status = status
        if result is not None:
            run.result = result
        if step_count is not None:
            run.step_count = step_count
        if completed_at is not None:
            run.completed_at = completed_at
        self._session.commit()
        self._session.refresh(run)
        return run

    def create_tool_call(
        self,
        *,
        workspace_id: UUID,
        agent_run_id: UUID,
        tool_name: str,
        input_: dict[str, Any] | None,
        output: dict[str, Any] | None,
        latency_ms: int | None,
        status: AgentToolCallStatus,
    ) -> AgentToolCall:
        """Persist a tool invocation for an agent run."""
        tool_call = AgentToolCall(
            workspace_id=workspace_id,
            agent_run_id=agent_run_id,
            tool_name=tool_name,
            input_=input_,
            output=output,
            latency_ms=latency_ms,
            status=status,
        )
        self._session.add(tool_call)
        self._session.commit()
        self._session.refresh(tool_call)
        return tool_call

    def count_tool_calls(
        self,
        *,
        workspace_id: UUID,
        agent_run_id: UUID,
    ) -> int:
        """Return the number of tool calls logged for an agent run."""
        stmt = select(AgentToolCall).where(
            AgentToolCall.workspace_id == workspace_id,
            AgentToolCall.agent_run_id == agent_run_id,
        )
        return len(list(self._session.scalars(stmt).all()))

    def list_tool_calls(
        self,
        *,
        workspace_id: UUID,
        agent_run_id: UUID,
    ) -> list[AgentToolCall]:
        """Return tool calls for an agent run ordered by creation time."""
        stmt = (
            select(AgentToolCall)
            .where(
                AgentToolCall.workspace_id == workspace_id,
                AgentToolCall.agent_run_id == agent_run_id,
            )
            .order_by(AgentToolCall.created_at.asc(), AgentToolCall.id.asc())
        )
        return list(self._session.scalars(stmt).all())
