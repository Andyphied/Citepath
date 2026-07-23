"""Unit tests for AgentService validation and failure handling."""

from datetime import UTC, datetime
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from app.infrastructure.db.enums import AgentRunStatus, AgentToolCallStatus, WorkspaceRole
from app.modules.agents.exceptions import AgentOrchestrationError, AgentRunNotFoundError
from app.modules.agents.schemas import AgentRunRequest, InvestigationSummary
from app.modules.agents.service import (
    AGENT_RUN_COMPLETED_EVENT,
    OBJECTIVE_AUDIT_MAX_CHARS,
    AgentService,
)
from app.modules.rag.exceptions import ConversationNotFoundError
from app.modules.rag.schemas import CitationResponse
from app.modules.workspaces.context import WorkspaceContext


@pytest.fixture
def workspace_context():
    return WorkspaceContext(
        workspace_id=uuid4(),
        user_id=uuid4(),
        role=WorkspaceRole.MEMBER,
    )


def _build_service(
    *,
    agent_repository=None,
    rag_repository=None,
    audit_repository=None,
) -> AgentService:
    return AgentService(
        agent_repository=agent_repository or MagicMock(),
        rag_repository=rag_repository or MagicMock(),
        retrieval_service=MagicMock(),
        document_repository=MagicMock(),
        ingestion_repository=MagicMock(),
        completion_provider=MagicMock(),
        permission_service=MagicMock(),
        usage_service=MagicMock(),
        audit_repository=audit_repository or MagicMock(),
        settings=MagicMock(),
    )


def test_start_investigation_rejects_foreign_conversation(workspace_context) -> None:
    rag_repository = MagicMock()
    rag_repository.get_conversation_by_id.return_value = None
    service = _build_service(rag_repository=rag_repository)

    with pytest.raises(ConversationNotFoundError):
        service.start_investigation(
            context=workspace_context,
            request=AgentRunRequest(
                objective="billing 502",
                conversation_id=uuid4(),
            ),
        )


def test_start_investigation_rejects_other_users_conversation(
    workspace_context,
) -> None:
    conversation = MagicMock()
    conversation.user_id = uuid4()
    rag_repository = MagicMock()
    rag_repository.get_conversation_by_id.return_value = conversation
    service = _build_service(rag_repository=rag_repository)

    with pytest.raises(ConversationNotFoundError):
        service.start_investigation(
            context=workspace_context,
            request=AgentRunRequest(
                objective="billing 502",
                conversation_id=uuid4(),
            ),
        )


def test_start_investigation_stores_safe_orchestration_failure(
    workspace_context,
) -> None:
    agent_repository = MagicMock()
    audit_repository = MagicMock()
    run = MagicMock()
    run.id = uuid4()
    agent_repository.create_run.return_value = run
    agent_repository.count_tool_calls.return_value = 1
    service = _build_service(
        agent_repository=agent_repository,
        audit_repository=audit_repository,
    )
    service._orchestrator = MagicMock()
    service._orchestrator.run.side_effect = AgentOrchestrationError("unknown_tool")

    with pytest.raises(AgentOrchestrationError):
        service.start_investigation(
            context=workspace_context,
            request=AgentRunRequest(objective="billing 502"),
        )

    update_kwargs = agent_repository.update_run.call_args.kwargs
    assert update_kwargs["result"] == {
        "error": "agent_orchestration_failed",
        "code": "unknown_tool",
    }
    audit_repository.create.assert_called_once_with(
        workspace_id=workspace_context.workspace_id,
        actor_user_id=workspace_context.user_id,
        event_type=AGENT_RUN_COMPLETED_EVENT,
        metadata={
            "agent_run_id": str(run.id),
            "objective": "billing 502",
            "tool_call_count": 1,
            "status": AgentRunStatus.FAILED.value,
        },
        ip_address=None,
    )


def test_start_investigation_accepts_owned_conversation(workspace_context) -> None:
    conversation = MagicMock()
    conversation.user_id = workspace_context.user_id
    rag_repository = MagicMock()
    rag_repository.get_conversation_by_id.return_value = conversation

    agent_repository = MagicMock()
    audit_repository = MagicMock()
    run = MagicMock()
    run.id = uuid4()
    agent_repository.create_run.return_value = run

    service = _build_service(
        agent_repository=agent_repository,
        rag_repository=rag_repository,
        audit_repository=audit_repository,
    )
    summary = InvestigationSummary(
        problem_statement="p",
        summary="s",
    )
    citation = CitationResponse(
        chunk_id=uuid4(),
        document_id=uuid4(),
        document_title="doc",
        chunk_preview="preview",
        score=0.9,
        metadata=None,
    )
    service._orchestrator = MagicMock()
    service._orchestrator.run.return_value = (summary, [citation], 1)

    conversation_id = uuid4()
    response = service.start_investigation(
        context=workspace_context,
        request=AgentRunRequest(
            objective="billing 502",
            conversation_id=conversation_id,
        ),
    )

    assert response.status == "completed"
    update_kwargs = agent_repository.update_run.call_args.kwargs
    assert update_kwargs["result"]["conversation_id"] == str(conversation_id)
    audit_repository.create.assert_called_once_with(
        workspace_id=workspace_context.workspace_id,
        actor_user_id=workspace_context.user_id,
        event_type=AGENT_RUN_COMPLETED_EVENT,
        metadata={
            "agent_run_id": str(run.id),
            "objective": "billing 502",
            "tool_call_count": 1,
            "status": AgentRunStatus.COMPLETED.value,
        },
        ip_address=None,
    )


def test_start_investigation_truncates_objective_in_audit(workspace_context) -> None:
    agent_repository = MagicMock()
    audit_repository = MagicMock()
    run = MagicMock()
    run.id = uuid4()
    agent_repository.create_run.return_value = run
    service = _build_service(
        agent_repository=agent_repository,
        audit_repository=audit_repository,
    )
    service._orchestrator = MagicMock()
    service._orchestrator.run.return_value = (
        InvestigationSummary(problem_statement="p", summary="s"),
        [],
        0,
    )
    long_objective = "x" * (OBJECTIVE_AUDIT_MAX_CHARS + 50)

    service.start_investigation(
        context=workspace_context,
        request=AgentRunRequest(objective=long_objective),
    )

    metadata = audit_repository.create.call_args.kwargs["metadata"]
    assert len(metadata["objective"]) == OBJECTIVE_AUDIT_MAX_CHARS + 1
    assert metadata["objective"].endswith("…")


def test_list_tool_calls_returns_ordered_items(workspace_context) -> None:
    agent_repository = MagicMock()
    run = MagicMock()
    run.id = uuid4()
    run.user_id = workspace_context.user_id
    agent_repository.get_run_by_id.return_value = run

    first = MagicMock()
    first.id = uuid4()
    first.tool_name = "search_knowledge_base"
    first.input_ = {"query": "billing"}
    first.output = {"content": "restart billing-api", "truncated": False}
    first.status = AgentToolCallStatus.SUCCESS
    first.latency_ms = 12
    first.created_at = datetime(2026, 7, 23, 10, 0, 0, tzinfo=UTC)

    second = MagicMock()
    second.id = uuid4()
    second.tool_name = "summarize_document"
    second.input_ = {"document_id": str(uuid4())}
    second.output = {"content": "summary…", "truncated": True}
    second.status = AgentToolCallStatus.SUCCESS
    second.latency_ms = 40
    second.created_at = datetime(2026, 7, 23, 10, 0, 1, tzinfo=UTC)

    agent_repository.list_tool_calls.return_value = [first, second]
    service = _build_service(agent_repository=agent_repository)

    result = service.list_tool_calls(
        context=workspace_context,
        agent_run_id=run.id,
    )

    assert len(result.items) == 2
    assert result.items[0].tool_name == "search_knowledge_base"
    assert result.items[0].input == {"query": "billing"}
    assert result.items[0].latency_ms == 12
    assert result.items[1].tool_name == "summarize_document"
    assert result.items[1].output["truncated"] is True


def test_list_tool_calls_member_cannot_view_other_users_run(workspace_context) -> None:
    agent_repository = MagicMock()
    run = MagicMock()
    run.id = uuid4()
    run.user_id = uuid4()
    agent_repository.get_run_by_id.return_value = run
    service = _build_service(agent_repository=agent_repository)

    with pytest.raises(AgentRunNotFoundError):
        service.list_tool_calls(
            context=workspace_context,
            agent_run_id=run.id,
        )


def test_list_tool_calls_admin_can_view_other_users_run() -> None:
    admin_context = WorkspaceContext(
        workspace_id=uuid4(),
        user_id=uuid4(),
        role=WorkspaceRole.ADMIN,
    )
    agent_repository = MagicMock()
    run = MagicMock()
    run.id = uuid4()
    run.user_id = uuid4()
    agent_repository.get_run_by_id.return_value = run
    agent_repository.list_tool_calls.return_value = []
    service = _build_service(agent_repository=agent_repository)

    result = service.list_tool_calls(
        context=admin_context,
        agent_run_id=run.id,
    )

    assert result.items == []
    agent_repository.list_tool_calls.assert_called_once()
