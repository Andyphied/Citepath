"""Unit tests for AGENT-004..007 tools and registry registration."""

from __future__ import annotations

import json
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from app.infrastructure.db.enums import DocumentStatus, WorkspaceRole
from app.infrastructure.llm.types import CompletionResult
from app.modules.agents.document_loader import (
    ERROR_DOCUMENT_EMPTY,
    ERROR_DOCUMENT_NOT_AVAILABLE,
    ERROR_DOCUMENT_NOT_INDEXED,
)
from app.modules.agents.schemas import (
    CompareIncidentsArgs,
    ExtractActionItemsArgs,
    SuggestDebuggingStepsArgs,
    SummarizeDocumentArgs,
)
from app.modules.agents.tool_registry import build_tool_registry, tool_schemas
from app.modules.agents.tools.compare_incidents import execute_compare_incidents
from app.modules.agents.tools.extract_action_items import execute_extract_action_items
from app.modules.agents.tools.suggest_debugging_steps import (
    _normalize_steps,
    execute_suggest_debugging_steps,
)
from app.modules.agents.tools.summarize_document import execute_summarize_document
from app.modules.workspaces.context import WorkspaceContext


@pytest.fixture
def workspace_context():
    return WorkspaceContext(
        workspace_id=uuid4(),
        user_id=uuid4(),
        role=WorkspaceRole.MEMBER,
    )


class FixedCompletionProvider:
    provider_name = "mock"

    def __init__(self, content: str) -> None:
        self._content = content
        self.calls = 0
        self.messages_seen: list[list[dict[str, str]]] = []

    def complete(self, *, messages, response_format=None):
        self.calls += 1
        self.messages_seen.append(messages)
        return CompletionResult(
            content=self._content,
            prompt_tokens=20,
            completion_tokens=10,
            model="mock-chat",
            latency_ms=3,
        )


def _indexed_document(*, title: str = "Runbook"):
    document = MagicMock()
    document.status = DocumentStatus.INDEXED
    document.title = title
    return document


def _chunk(*, document_id, content: str, index: int = 0):
    chunk = MagicMock()
    chunk.id = uuid4()
    chunk.document_id = document_id
    chunk.content = content
    chunk.chunk_index = index
    chunk.metadata_ = {"section": "ops"}
    return chunk


def test_registry_includes_all_five_mvp_tools() -> None:
    registry = build_tool_registry(
        retrieval_service=MagicMock(),
        document_repository=MagicMock(),
        ingestion_repository=MagicMock(),
        completion_provider=MagicMock(),
        usage_service=MagicMock(),
    )
    assert set(registry) == {
        "search_knowledge_base",
        "summarize_document",
        "extract_action_items",
        "compare_incidents",
        "suggest_debugging_steps",
    }
    schemas = tool_schemas(registry)
    assert {item["name"] for item in schemas} == set(registry)


def test_summarize_document_returns_summary_and_citations(workspace_context) -> None:
    document_id = uuid4()
    document_repository = MagicMock()
    document_repository.get_by_id.return_value = _indexed_document(title="Billing")
    ingestion_repository = MagicMock()
    chunk = _chunk(document_id=document_id, content="Restart billing-api on 502.")
    ingestion_repository.list_chunks_for_document.return_value = [chunk]
    provider = FixedCompletionProvider(json.dumps({"summary": "Restart on 502."}))
    usage_service = MagicMock()

    output = execute_summarize_document(
        args=SummarizeDocumentArgs(document_id=document_id),
        context=workspace_context,
        agent_run_id=uuid4(),
        document_repository=document_repository,
        ingestion_repository=ingestion_repository,
        completion_provider=provider,
        usage_service=usage_service,
    )

    assert "Restart on 502." in output["content"]
    assert output["citations"][0]["document_id"] == str(document_id)
    assert output["related_documents"] == [str(document_id)]
    usage_service.log_event.assert_called()
    document_repository.get_by_id.assert_called_once_with(
        workspace_id=workspace_context.workspace_id,
        id=document_id,
    )


def test_summarize_document_foreign_id_safe_failure(workspace_context) -> None:
    document_id = uuid4()
    document_repository = MagicMock()
    document_repository.get_by_id.return_value = None
    output = execute_summarize_document(
        args=SummarizeDocumentArgs(document_id=document_id),
        context=workspace_context,
        agent_run_id=uuid4(),
        document_repository=document_repository,
        ingestion_repository=MagicMock(),
        completion_provider=MagicMock(),
        usage_service=MagicMock(),
    )
    assert output["error"] == ERROR_DOCUMENT_NOT_AVAILABLE
    assert output["citations"] == []
    assert "secret" not in output["content"].lower()


def test_summarize_document_not_indexed_graceful_failure(workspace_context) -> None:
    document_id = uuid4()
    document = _indexed_document()
    document.status = DocumentStatus.UPLOADED
    document_repository = MagicMock()
    document_repository.get_by_id.return_value = document
    output = execute_summarize_document(
        args=SummarizeDocumentArgs(document_id=document_id),
        context=workspace_context,
        agent_run_id=uuid4(),
        document_repository=document_repository,
        ingestion_repository=MagicMock(),
        completion_provider=MagicMock(),
        usage_service=MagicMock(),
    )
    assert output["error"] == ERROR_DOCUMENT_NOT_INDEXED


def test_extract_action_items_structured_output(workspace_context) -> None:
    document_id = uuid4()
    chunk = _chunk(
        document_id=document_id,
        content="TODO: rotate billing credentials after incident.",
    )
    document_repository = MagicMock()
    document_repository.get_by_id.return_value = _indexed_document(title="Postmortem")
    ingestion_repository = MagicMock()
    ingestion_repository.list_chunks_for_document.return_value = [chunk]
    provider = FixedCompletionProvider(
        json.dumps(
            {
                "summary": "One follow-up",
                "action_items": [
                    {
                        "text": "Rotate billing credentials",
                        "source_chunk_id": str(chunk.id),
                    }
                ],
            }
        )
    )

    output = execute_extract_action_items(
        args=ExtractActionItemsArgs(document_id=document_id),
        context=workspace_context,
        agent_run_id=uuid4(),
        document_repository=document_repository,
        ingestion_repository=ingestion_repository,
        completion_provider=provider,
        usage_service=MagicMock(),
    )

    assert output["action_items"][0]["text"] == "Rotate billing credentials"
    assert output["action_items"][0]["source_chunk_id"] == str(chunk.id)
    assert output["citations"]
    assert str(document_id) in output["related_documents"]


def test_extract_action_items_empty_document(workspace_context) -> None:
    document_id = uuid4()
    document_repository = MagicMock()
    document_repository.get_by_id.return_value = _indexed_document()
    ingestion_repository = MagicMock()
    ingestion_repository.list_chunks_for_document.return_value = []
    output = execute_extract_action_items(
        args=ExtractActionItemsArgs(document_id=document_id),
        context=workspace_context,
        agent_run_id=uuid4(),
        document_repository=document_repository,
        ingestion_repository=ingestion_repository,
        completion_provider=MagicMock(),
        usage_service=MagicMock(),
    )
    assert output["error"] == ERROR_DOCUMENT_EMPTY
    assert output["citations"] == []


def test_compare_incidents_highlights_common_causes(workspace_context) -> None:
    doc_a = uuid4()
    doc_b = uuid4()
    document_repository = MagicMock()
    document_repository.get_by_id.side_effect = [
        _indexed_document(title="Incident A"),
        _indexed_document(title="Incident B"),
    ]
    ingestion_repository = MagicMock()
    ingestion_repository.list_chunks_for_document.side_effect = [
        [_chunk(document_id=doc_a, content="Root cause: redis timeout")],
        [_chunk(document_id=doc_b, content="Root cause: redis saturation")],
    ]
    provider = FixedCompletionProvider(
        json.dumps(
            {
                "summary": "Both incidents involve Redis pressure.",
                "similarities": ["Redis pressure"],
                "differences": ["Timeout vs saturation"],
                "recurring_themes": ["Cache layer"],
                "common_root_causes": ["Redis capacity"],
            }
        )
    )

    output = execute_compare_incidents(
        args=CompareIncidentsArgs(document_ids=[doc_a, doc_b]),
        context=workspace_context,
        agent_run_id=uuid4(),
        document_repository=document_repository,
        ingestion_repository=ingestion_repository,
        completion_provider=provider,
        usage_service=MagicMock(),
    )

    assert "Redis capacity" in output["content"]
    assert output["common_root_causes"] == ["Redis capacity"]
    assert set(output["related_documents"]) == {str(doc_a), str(doc_b)}
    assert len(output["citations"]) == 2


def test_compare_incidents_rejects_foreign_document(workspace_context) -> None:
    doc_a = uuid4()
    foreign = uuid4()
    document_repository = MagicMock()
    document_repository.get_by_id.side_effect = [
        _indexed_document(title="Local"),
        None,
    ]
    ingestion_repository = MagicMock()
    ingestion_repository.list_chunks_for_document.return_value = [
        _chunk(document_id=doc_a, content="local content")
    ]

    output = execute_compare_incidents(
        args=CompareIncidentsArgs(document_ids=[doc_a, foreign]),
        context=workspace_context,
        agent_run_id=uuid4(),
        document_repository=document_repository,
        ingestion_repository=ingestion_repository,
        completion_provider=MagicMock(),
        usage_service=MagicMock(),
    )

    assert output["error"] == ERROR_DOCUMENT_NOT_AVAILABLE
    assert output["citations"] == []
    assert "Local" not in output["content"]


def test_compare_incidents_args_require_two_to_five_unique_ids() -> None:
    with pytest.raises(ValueError):
        CompareIncidentsArgs(document_ids=[uuid4()])
    with pytest.raises(ValueError):
        CompareIncidentsArgs(document_ids=[uuid4() for _ in range(6)])
    doc = uuid4()
    with pytest.raises(ValueError):
        CompareIncidentsArgs(document_ids=[doc, doc])


def test_suggest_debugging_steps_grounded_in_search(workspace_context) -> None:
    document_id = uuid4()
    chunk_id = uuid4()
    retrieval_service = MagicMock()
    retrieval_service.search.return_value = MagicMock(
        query="billing-api 502",
        insufficient_context=False,
        chunks=[
            MagicMock(
                chunk_id=chunk_id,
                content_preview="Check gateway timeout for billing-api 502.",
                score=0.9,
                document_metadata=MagicMock(
                    document_id=document_id,
                    title="Billing Runbook",
                    chunk_metadata={"section": "502"},
                ),
            )
        ],
    )
    provider = FixedCompletionProvider(
        json.dumps(
            {
                "summary": "Start with gateway checks.",
                "steps": [
                    {
                        "step": 1,
                        "check": "Inspect api-gateway timeout for billing-api",
                        "grounded": True,
                        "speculative": False,
                        "source_document_id": str(document_id),
                    },
                    {
                        "step": 2,
                        "check": "Ask platform team for recent deploys",
                        "grounded": False,
                        "speculative": True,
                        "source_document_id": None,
                    },
                ],
            }
        )
    )

    output = execute_suggest_debugging_steps(
        args=SuggestDebuggingStepsArgs(
            service_name="billing-api",
            symptom="502",
        ),
        context=workspace_context,
        agent_run_id=uuid4(),
        retrieval_service=retrieval_service,
        completion_provider=provider,
        usage_service=MagicMock(),
    )

    retrieval_service.search.assert_called_once()
    assert output["insufficient_context"] is False
    assert output["steps"][0]["grounded"] is True
    assert output["steps"][1]["speculative"] is True
    assert "(speculative)" in output["content"]
    assert output["citations"]


def test_normalize_steps_rejects_unsourced_grounded_claims() -> None:
    """LLM grounded=true without a citation-backed source must not stay grounded."""
    allowed_id = str(uuid4())
    foreign_id = str(uuid4())

    steps = _normalize_steps(
        [
            {
                "step": 1,
                "check": "Restart the service",
                "grounded": True,
                "speculative": False,
                "source_document_id": None,
            },
            {
                "step": 2,
                "check": "Check an unrelated foreign runbook",
                "grounded": True,
                "speculative": False,
                "source_document_id": foreign_id,
            },
            {
                "step": 3,
                "check": "Follow the cited runbook check",
                "grounded": True,
                "speculative": False,
                "source_document_id": allowed_id,
            },
        ],
        allowed_document_ids={allowed_id},
    )

    assert steps[0]["grounded"] is False
    assert steps[0]["speculative"] is True
    assert steps[0]["source_document_id"] is None
    assert steps[1]["grounded"] is False
    assert steps[1]["speculative"] is True
    assert steps[1]["source_document_id"] is None
    assert steps[2]["grounded"] is True
    assert steps[2]["speculative"] is False
    assert steps[2]["source_document_id"] == allowed_id


def test_suggest_debugging_steps_insufficient_context(workspace_context) -> None:
    retrieval_service = MagicMock()
    retrieval_service.search.return_value = MagicMock(
        query="unknown-service xyz",
        insufficient_context=True,
        chunks=[],
    )
    output = execute_suggest_debugging_steps(
        args=SuggestDebuggingStepsArgs(
            service_name="unknown-service",
            symptom="xyz",
        ),
        context=workspace_context,
        agent_run_id=uuid4(),
        retrieval_service=retrieval_service,
        completion_provider=MagicMock(),
        usage_service=MagicMock(),
    )
    assert output["error"] == "insufficient_context"
    assert output["steps"] == []
    assert output["citations"] == []
