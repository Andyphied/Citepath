"""Unit tests for agent HTTP exception handlers."""

import asyncio
from unittest.mock import MagicMock

from app.api.agent_errors import agent_orchestration_error_handler
from app.modules.agents.exceptions import AgentOrchestrationError


def test_agent_orchestration_error_handler_returns_503_without_details() -> None:
    request = MagicMock()
    request.state.request_id = "agent-req-123"
    request.url.path = "/workspaces/x/agent-runs"
    request.method = "POST"

    response = asyncio.run(
        agent_orchestration_error_handler(
            request,
            AgentOrchestrationError("unknown_tool: delete_everything"),
        )
    )

    assert response.status_code == 503
    body = response.body.decode()
    assert '"code":"agent_orchestration_failed"' in body.replace(" ", "")
    assert "Unable to complete the investigation at this time" in body
    assert "delete_everything" not in body
    assert "unknown_tool" not in body
