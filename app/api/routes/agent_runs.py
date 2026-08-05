"""Agent run routes."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Body, Request

from app.api.deps import AgentServiceDep, RequireRunAgentDep
from app.modules.agents.schemas import (
    AgentRunDetailResponse,
    AgentRunRequest,
    AgentRunResponse,
    AgentToolCallListResponse,
)


router = APIRouter(prefix="/workspaces", tags=["agent-runs"])

_AGENT_RUN_EXAMPLES = {
    "demo_billing_investigation": {
        "summary": "Northstar billing 502 investigation",
        "description": (
            "Synchronous agent run using allowed read-only tools "
            "(search, summarize, compare, extract, suggest debugging steps)."
        ),
        "value": {
            "objective": (
                "Investigate billing API 502 errors after the latest "
                "deployment and recommend checks from workspace runbooks "
                "and incidents."
            ),
        },
    },
    "with_conversation": {
        "summary": "Link run to an existing conversation",
        "value": {
            "objective": (
                "Compare the last two billing incidents and list action items."
            ),
            "conversation_id": "11111111-1111-1111-1111-111111111111",
        },
    },
}


@router.post(
    "/{workspace_id}/agent-runs",
    response_model=AgentRunResponse,
    summary="Start an incident investigation agent run",
    response_description="Structured investigation summary with citations",
)
async def start_agent_run(
    workspace_id: UUID,
    body: Annotated[
        AgentRunRequest,
        Body(openapi_examples=_AGENT_RUN_EXAMPLES),
    ],
    workspace_context: RequireRunAgentDep,
    agent_service: AgentServiceDep,
    request: Request,
) -> AgentRunResponse:
    """Start a synchronous incident investigation agent run.

    The agent may only call the allow-listed tools. It cannot execute shell
    commands, mutate documents, or call external remediation APIs.
    """
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
    summary="Get an agent run",
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
    summary="List tool calls for an agent run",
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
