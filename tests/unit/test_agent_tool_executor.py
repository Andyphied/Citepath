"""Unit tests for agent tool executor."""

from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from app.infrastructure.db.enums import AgentToolCallStatus
from app.modules.agents.exceptions import UnknownToolError
from app.modules.agents.schemas import SearchKnowledgeBaseArgs
from app.modules.agents.tool_executor import ToolExecutor
from app.modules.agents.tool_registry import RegisteredTool
from app.modules.workspaces.context import WorkspaceContext
from app.infrastructure.db.enums import WorkspaceRole


@pytest.fixture
def workspace_context():
    return WorkspaceContext(
        workspace_id=uuid4(),
        user_id=uuid4(),
        role=WorkspaceRole.MEMBER,
    )


def test_tool_executor_rejects_unknown_tool(workspace_context) -> None:
    repository = MagicMock()
    executor = ToolExecutor(registry={}, agent_repository=repository)
    agent_run_id = uuid4()

    with pytest.raises(UnknownToolError):
        executor.run(
            tool_name="delete_everything",
            arguments={"force": True},
            context=workspace_context,
            agent_run_id=agent_run_id,
        )

    repository.create_tool_call.assert_called_once()
    kwargs = repository.create_tool_call.call_args.kwargs
    assert kwargs["tool_name"] == "delete_everything"
    assert kwargs["status"] == AgentToolCallStatus.FAILED
    assert kwargs["output"] == {"error": "unknown_tool"}


def test_tool_executor_sanitizes_validation_and_execution_failures(
    workspace_context,
) -> None:
    repository = MagicMock()

    def invalid_handler(args: SearchKnowledgeBaseArgs, context: WorkspaceContext) -> dict:
        raise RuntimeError("secret db connection string postgres://user:pass@host/db")

    registry = {
        "search_knowledge_base": RegisteredTool(
            name="search_knowledge_base",
            description="search",
            args_model=SearchKnowledgeBaseArgs,
            handler=invalid_handler,
        )
    }
    executor = ToolExecutor(registry=registry, agent_repository=repository)

    validation_output = executor.run(
        tool_name="search_knowledge_base",
        arguments={},
        context=workspace_context,
        agent_run_id=uuid4(),
    )
    assert validation_output == {"error": "invalid_arguments"}
    assert "details" not in validation_output

    execution_output = executor.run(
        tool_name="search_knowledge_base",
        arguments={"query": "billing 502"},
        context=workspace_context,
        agent_run_id=uuid4(),
    )
    assert execution_output == {"error": "execution_failed"}
    assert "postgres://" not in str(execution_output)
    assert "secret" not in str(execution_output)


def test_tool_executor_logs_successful_tool_call(workspace_context) -> None:
    repository = MagicMock()

    def handler(args: SearchKnowledgeBaseArgs, context: WorkspaceContext) -> dict:
        return {"content": "result", "citations": []}

    registry = {
        "search_knowledge_base": RegisteredTool(
            name="search_knowledge_base",
            description="search",
            args_model=SearchKnowledgeBaseArgs,
            handler=handler,
        )
    }
    executor = ToolExecutor(registry=registry, agent_repository=repository)
    agent_run_id = uuid4()

    output = executor.run(
        tool_name="search_knowledge_base",
        arguments={"query": "billing 502 deployment"},
        context=workspace_context,
        agent_run_id=agent_run_id,
    )

    assert output["content"] == "result"
    repository.create_tool_call.assert_called_once()
    kwargs = repository.create_tool_call.call_args.kwargs
    assert kwargs["tool_name"] == "search_knowledge_base"
    assert kwargs["status"] == AgentToolCallStatus.SUCCESS
