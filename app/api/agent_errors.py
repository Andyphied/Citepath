"""Agent-related HTTP exception handlers."""

from fastapi import Request, status

from app.modules.agents.exceptions import (
    AgentCompletionError,
    AgentOrchestrationError,
    AgentRunNotFoundError,
    EmptyObjectiveError,
)
from app.modules.observability.errors import error_response


async def empty_objective_handler(
    request: Request,
    _exc: EmptyObjectiveError,
):
    """Return 422 when the investigation objective is empty."""
    return error_response(
        request=request,
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        code="empty_objective",
        message="Objective must not be empty",
    )


async def agent_run_not_found_handler(
    request: Request,
    _exc: AgentRunNotFoundError,
):
    """Return 404 when an agent run is missing or not accessible."""
    return error_response(
        request=request,
        status_code=status.HTTP_404_NOT_FOUND,
        code="not_found",
        message="Agent run not found",
    )


async def agent_orchestration_error_handler(
    request: Request,
    _exc: AgentOrchestrationError,
):
    """Return 503 without exposing orchestration internals."""
    return error_response(
        request=request,
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        code="agent_orchestration_failed",
        message="Unable to complete the investigation at this time",
    )


async def agent_completion_error_handler(
    request: Request,
    _exc: AgentCompletionError,
):
    """Return 503 without exposing provider error details."""
    return error_response(
        request=request,
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        code="agent_completion_failed",
        message="Unable to complete the investigation at this time",
    )
