"""Validate and execute whitelisted agent tools."""

from __future__ import annotations

import time
from typing import Any
from uuid import UUID

import structlog
from pydantic import ValidationError

from app.infrastructure.db.enums import AgentToolCallStatus
from app.modules.agents.exceptions import UnknownToolError
from app.modules.agents.repository import AgentRepository
from app.modules.agents.tool_registry import RegisteredTool
from app.modules.workspaces.context import WorkspaceContext

logger = structlog.get_logger(__name__)

TOOL_OUTPUT_MAX_CHARS = 8000


class ToolExecutor:
    """Execute registry tools with workspace context injection."""

    def __init__(
        self,
        *,
        registry: dict[str, RegisteredTool],
        agent_repository: AgentRepository,
    ) -> None:
        self._registry = registry
        self._agent_repository = agent_repository

    def run(
        self,
        *,
        tool_name: str,
        arguments: dict[str, Any] | None,
        context: WorkspaceContext,
        agent_run_id: UUID,
    ) -> dict[str, Any]:
        """Validate tool name, execute handler, and persist agent_tool_calls row."""
        registered = self._registry.get(tool_name)
        raw_args = arguments or {}
        if registered is None:
            self._agent_repository.create_tool_call(
                workspace_id=context.workspace_id,
                agent_run_id=agent_run_id,
                tool_name=tool_name,
                input_=raw_args,
                output={"error": "unknown_tool"},
                latency_ms=0,
                status=AgentToolCallStatus.FAILED,
            )
            raise UnknownToolError(tool_name)

        started_at = time.perf_counter()
        try:
            validated_args = registered.args_model.model_validate(raw_args)
            output = registered.handler(validated_args, context)
            status = AgentToolCallStatus.SUCCESS
        except ValidationError:
            logger.warning(
                "agent_tool_invalid_arguments",
                tool_name=tool_name,
            )
            output = {"error": "invalid_arguments"}
            status = AgentToolCallStatus.FAILED
        except Exception as exc:
            logger.warning(
                "agent_tool_execution_failed",
                tool_name=tool_name,
                error_type=type(exc).__name__,
            )
            output = {"error": "execution_failed"}
            status = AgentToolCallStatus.FAILED

        latency_ms = int((time.perf_counter() - started_at) * 1000)
        truncated_output = _truncate_output(output)

        self._agent_repository.create_tool_call(
            workspace_id=context.workspace_id,
            agent_run_id=agent_run_id,
            tool_name=tool_name,
            input_=raw_args,
            output=truncated_output,
            latency_ms=latency_ms,
            status=status,
        )

        return truncated_output


def _truncate_output(output: dict[str, Any]) -> dict[str, Any]:
    """Truncate large tool output strings to control token usage."""
    content = output.get("content")
    if isinstance(content, str) and len(content) > TOOL_OUTPUT_MAX_CHARS:
        return {
            **output,
            "content": content[:TOOL_OUTPUT_MAX_CHARS] + "…",
            "truncated": True,
        }
    return output
