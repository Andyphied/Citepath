"""Agent run routes."""

from uuid import UUID

from fastapi import APIRouter, Request

from app.api.deps import AgentServiceDep, RequireRunAgentDep
from app.modules.agents.schemas import (
    AgentRunDetailResponse,
    AgentRunRequest,
    AgentRunResponse,
    AgentToolCallListResponse,
)


router = APIRouter(prefix="/workspaces", tags=["agent-runs"])


@router.post(
    "/{workspace_id}/agent-runs",
    response_model=AgentRunResponse,
)
async def start_agent_run(
    workspace_id: UUID,
    body: AgentRunRequest,
    workspace_context: RequireRunAgentDep,
    agent_service: AgentServiceDep,
    request: Request,
) -> AgentRunResponse:
    """Start a synchronous incident investigation agent run."""
    _ = workspace_id
    client_ip = request.client.host if request.client else None
    return agent_service.start_investigation(
        context=workspace_context,
        request=body,
        ip_address=client_ip,
    )


@router.get(
    "/{workspace_id}/agent-runs/{agent_run_id}",
    response_model=AgentRunDetailResponse,
)
async def get_agent_run(
    workspace_id: UUID,
    agent_run_id: UUID,
    workspace_context: RequireRunAgentDep,
    agent_service: AgentServiceDep,
    request: Request,
) -> AgentRunDetailResponse:
    """Return an agent run accessible to the caller."""
    _ = workspace_id
    client_ip = request.client.host if request.client else None
    return agent_service.get_run(
        context=workspace_context,
        agent_run_id=agent_run_id,
        ip_address=client_ip,
    )


@router.get(
    "/{workspace_id}/agent-runs/{agent_run_id}/tool-calls",
    response_model=AgentToolCallListResponse,
)
async def list_agent_tool_calls(
    workspace_id: UUID,
    agent_run_id: UUID,
    workspace_context: RequireRunAgentDep,
    agent_service: AgentServiceDep,
    request: Request,
) -> AgentToolCallListResponse:
    """List ordered tool calls for an agent run (audit/debug)."""
    _ = workspace_id
    client_ip = request.client.host if request.client else None
    return agent_service.list_tool_calls(
        context=workspace_context,
        agent_run_id=agent_run_id,
        ip_address=client_ip,
    )
