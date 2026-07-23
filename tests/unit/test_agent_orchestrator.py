"""Unit tests for agent orchestrator."""

import json
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from app.infrastructure.db.enums import WorkspaceRole
from app.infrastructure.llm.types import CompletionResult
from app.modules.agents.exceptions import AgentOrchestrationError
from app.modules.agents.orchestrator import (
    INSUFFICIENT_CONTEXT_SUMMARY_TEXT,
    AgentOrchestrator,
)
from app.modules.agents.tool_executor import ToolExecutor
from app.modules.agents.tool_registry import build_tool_registry
from app.modules.retrieval.service import RetrievalService
from app.modules.workspaces.context import WorkspaceContext


def _registry(retrieval_service=None):
    return build_tool_registry(
        retrieval_service=retrieval_service or MagicMock(spec=RetrievalService),
        document_repository=MagicMock(),
        ingestion_repository=MagicMock(),
        completion_provider=MagicMock(),
        usage_service=MagicMock(),
    )


class SequenceCompletionProvider:
    provider_name = "mock"

    def __init__(self, responses: list[str]) -> None:
        self._responses = list(responses)
        self.calls = 0

    def complete(self, *, messages, response_format=None):
        content = self._responses[self.calls]
        self.calls += 1
        return CompletionResult(
            content=content,
            prompt_tokens=50,
            completion_tokens=30,
            model="mock-chat",
            latency_ms=5,
        )


class StubSettings:
    RETRIEVAL_MIN_SCORE = 0.0


@pytest.fixture
def workspace_context():
    return WorkspaceContext(
        workspace_id=uuid4(),
        user_id=uuid4(),
        role=WorkspaceRole.MEMBER,
    )


def test_orchestrator_calls_search_before_summary(workspace_context) -> None:
    retrieval_service = MagicMock(spec=RetrievalService)
    chunk_id = uuid4()
    document_id = uuid4()
    retrieval_service.search.return_value = MagicMock(
        query="billing API 502 deployment",
        insufficient_context=False,
        chunks=[
            MagicMock(
                chunk_id=chunk_id,
                content_preview="Restart billing-api after 502 deployment.",
                score=0.91,
                document_metadata=MagicMock(
                    document_id=document_id,
                    title="Billing Runbook",
                    chunk_metadata={"section": "502"},
                ),
            )
        ],
    )

    registry = _registry(retrieval_service)
    repository = MagicMock()
    repository.count_tool_calls.return_value = 1
    tool_executor = ToolExecutor(registry=registry, agent_repository=repository)

    provider = SequenceCompletionProvider(
        [
            json.dumps(
                {
                    "action": "call_tool",
                    "tool_name": "search_knowledge_base",
                    "arguments": {"query": "billing API 502 deployment"},
                    "reason": "Need runbook context",
                }
            ),
            json.dumps({"action": "finish", "reason": "Enough context gathered"}),
            json.dumps(
                {
                    "problem_statement": "Billing API returning 502 after deployment",
                    "summary": "Check billing-api restart steps",
                    "likely_causes": ["Gateway timeout regression"],
                    "likely_related_systems": ["billing-api", "api-gateway"],
                    "recommended_checks": ["Restart billing-api"],
                    "related_documents": [str(document_id)],
                    "action_items": ["Review gateway timeout config"],
                    "risks_or_unknowns": ["Need gateway logs"],
                    "next_steps": ["Validate upstream health"],
                }
            ),
        ]
    )

    orchestrator = AgentOrchestrator(
        agent_repository=repository,
        tool_executor=tool_executor,
        completion_provider=provider,
        usage_service=MagicMock(),
        registry=registry,
        settings=StubSettings(),
    )

    summary, citations, tool_calls_count = orchestrator.run(
        context=workspace_context,
        agent_run_id=uuid4(),
        objective="billing API 502 after deployment",
    )

    retrieval_service.search.assert_called_once()
    assert tool_calls_count == 1
    assert summary.problem_statement.startswith("Billing API")
    assert citations
    assert citations[0].document_id == document_id


def test_orchestrator_returns_safe_summary_without_citations(workspace_context) -> None:
    retrieval_service = MagicMock(spec=RetrievalService)
    retrieval_service.search.return_value = MagicMock(
        query="unknown incident",
        insufficient_context=True,
        chunks=[],
    )

    registry = _registry(retrieval_service)
    repository = MagicMock()
    repository.count_tool_calls.return_value = 1
    tool_executor = ToolExecutor(registry=registry, agent_repository=repository)

    provider = SequenceCompletionProvider(
        [
            json.dumps(
                {
                    "action": "call_tool",
                    "tool_name": "search_knowledge_base",
                    "arguments": {"query": "unknown incident"},
                }
            ),
            json.dumps({"action": "finish", "reason": "no evidence"}),
            json.dumps(
                {
                    "problem_statement": "should not be used",
                    "summary": "Fabricated root cause: bad deploy",
                    "likely_causes": ["invented cause"],
                    "likely_related_systems": ["invented-system"],
                    "recommended_checks": ["invented check"],
                    "related_documents": [str(uuid4())],
                    "action_items": ["invented action"],
                    "risks_or_unknowns": [],
                    "next_steps": ["invented next step"],
                }
            ),
        ]
    )

    orchestrator = AgentOrchestrator(
        agent_repository=repository,
        tool_executor=tool_executor,
        completion_provider=provider,
        usage_service=MagicMock(),
        registry=registry,
        settings=StubSettings(),
    )

    summary, citations, tool_calls_count = orchestrator.run(
        context=workspace_context,
        agent_run_id=uuid4(),
        objective="unknown incident with no docs",
    )

    assert tool_calls_count == 1
    assert citations == []
    assert summary.summary == INSUFFICIENT_CONTEXT_SUMMARY_TEXT
    assert summary.likely_causes == []
    assert summary.recommended_checks == []
    assert summary.related_documents == []
    assert summary.action_items == []
    # Summary LLM step must not run when citations are empty.
    assert provider.calls == 2


def test_orchestrator_filters_related_documents_to_citation_ids(
    workspace_context,
) -> None:
    retrieval_service = MagicMock(spec=RetrievalService)
    chunk_id = uuid4()
    document_id = uuid4()
    foreign_document_id = uuid4()
    retrieval_service.search.return_value = MagicMock(
        query="billing API 502 deployment",
        insufficient_context=False,
        chunks=[
            MagicMock(
                chunk_id=chunk_id,
                content_preview="Restart billing-api after 502 deployment.",
                score=0.91,
                document_metadata=MagicMock(
                    document_id=document_id,
                    title="Billing Runbook",
                    chunk_metadata={"section": "502"},
                ),
            )
        ],
    )

    registry = _registry(retrieval_service)
    repository = MagicMock()
    repository.count_tool_calls.return_value = 1
    tool_executor = ToolExecutor(registry=registry, agent_repository=repository)

    provider = SequenceCompletionProvider(
        [
            json.dumps(
                {
                    "action": "call_tool",
                    "tool_name": "search_knowledge_base",
                    "arguments": {"query": "billing API 502 deployment"},
                }
            ),
            json.dumps({"action": "finish", "reason": "Enough context gathered"}),
            json.dumps(
                {
                    "problem_statement": "Billing API returning 502 after deployment",
                    "summary": "Check billing-api restart steps",
                    "likely_causes": ["Gateway timeout regression"],
                    "likely_related_systems": ["billing-api"],
                    "recommended_checks": ["Restart billing-api"],
                    "related_documents": [str(document_id), str(foreign_document_id)],
                    "action_items": ["Review gateway timeout config"],
                    "risks_or_unknowns": ["Need gateway logs"],
                    "next_steps": ["Validate upstream health"],
                }
            ),
        ]
    )

    orchestrator = AgentOrchestrator(
        agent_repository=repository,
        tool_executor=tool_executor,
        completion_provider=provider,
        usage_service=MagicMock(),
        registry=registry,
        settings=StubSettings(),
    )

    summary, _citations, _tool_calls_count = orchestrator.run(
        context=workspace_context,
        agent_run_id=uuid4(),
        objective="billing API 502 after deployment",
    )

    assert summary.related_documents == [document_id]


def test_orchestrator_unknown_tool_raises_orchestration_error(
    workspace_context,
) -> None:
    registry = _registry()
    repository = MagicMock()
    tool_executor = ToolExecutor(registry=registry, agent_repository=repository)
    provider = SequenceCompletionProvider(
        [
            json.dumps(
                {
                    "action": "call_tool",
                    "tool_name": "delete_everything",
                    "arguments": {},
                }
            )
        ]
    )

    orchestrator = AgentOrchestrator(
        agent_repository=repository,
        tool_executor=tool_executor,
        completion_provider=provider,
        usage_service=MagicMock(),
        registry=registry,
        settings=StubSettings(),
    )

    with pytest.raises(AgentOrchestrationError, match="unknown_tool"):
        orchestrator.run(
            context=workspace_context,
            agent_run_id=uuid4(),
            objective="try forbidden tool",
        )
