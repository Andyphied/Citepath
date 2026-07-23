"""Unit tests for AgentService validation and failure handling."""

from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from app.infrastructure.db.enums import WorkspaceRole
from app.modules.agents.exceptions import AgentOrchestrationError
from app.modules.agents.schemas import AgentRunRequest, InvestigationSummary
from app.modules.agents.service import AgentService
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


def _build_service(*, agent_repository=None, rag_repository=None) -> AgentService:
    service = AgentService(
        agent_repository=agent_repository or MagicMock(),
        rag_repository=rag_repository or MagicMock(),
        retrieval_service=MagicMock(),
        document_repository=MagicMock(),
        ingestion_repository=MagicMock(),
        completion_provider=MagicMock(),
        permission_service=MagicMock(),
        usage_service=MagicMock(),
        settings=MagicMock(),
    )
    return service


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
    run = MagicMock()
    run.id = uuid4()
    agent_repository.create_run.return_value = run
    service = _build_service(agent_repository=agent_repository)
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


def test_start_investigation_accepts_owned_conversation(workspace_context) -> None:
    conversation = MagicMock()
    conversation.user_id = workspace_context.user_id
    rag_repository = MagicMock()
    rag_repository.get_conversation_by_id.return_value = conversation

    agent_repository = MagicMock()
    run = MagicMock()
    run.id = uuid4()
    agent_repository.create_run.return_value = run

    service = _build_service(
        agent_repository=agent_repository,
        rag_repository=rag_repository,
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
