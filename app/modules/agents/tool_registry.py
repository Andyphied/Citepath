"""Static tool registry for MVP agent tools."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from pydantic import BaseModel

from app.infrastructure.llm.completion import ChatCompletionProvider
from app.modules.agents.schemas import (
    CompareIncidentsArgs,
    ExtractActionItemsArgs,
    SearchKnowledgeBaseArgs,
    SuggestDebuggingStepsArgs,
    SummarizeDocumentArgs,
)
from app.modules.agents.tools.compare_incidents import execute_compare_incidents
from app.modules.agents.tools.extract_action_items import execute_extract_action_items
from app.modules.agents.tools.search_knowledge_base import execute_search_knowledge_base
from app.modules.agents.tools.suggest_debugging_steps import (
    execute_suggest_debugging_steps,
)
from app.modules.agents.tools.summarize_document import execute_summarize_document
from app.modules.documents.repository import DocumentRepository
from app.modules.ingestion.repository import IngestionRepository
from app.modules.retrieval.service import RetrievalService
from app.modules.usage.service import UsageService
from app.modules.workspaces.context import WorkspaceContext

ToolHandler = Callable[..., dict[str, Any]]


@dataclass(frozen=True)
class RegisteredTool:
    """Metadata and handler for a whitelisted agent tool."""

    name: str
    description: str
    args_model: type[BaseModel]
    handler: ToolHandler


def build_tool_registry(
    *,
    retrieval_service: RetrievalService,
    document_repository: DocumentRepository,
    ingestion_repository: IngestionRepository,
    completion_provider: ChatCompletionProvider,
    usage_service: UsageService,
) -> dict[str, RegisteredTool]:
    """Build the static MVP tool registry (five whitelisted tools)."""

    def _search_handler(
        args: SearchKnowledgeBaseArgs,
        context: WorkspaceContext,
        *,
        agent_run_id: UUID,
    ) -> dict:
        del agent_run_id
        return execute_search_knowledge_base(
            args=args,
            context=context,
            retrieval_service=retrieval_service,
        )

    def _summarize_handler(
        args: SummarizeDocumentArgs,
        context: WorkspaceContext,
        *,
        agent_run_id: UUID,
    ) -> dict:
        return execute_summarize_document(
            args=args,
            context=context,
            agent_run_id=agent_run_id,
            document_repository=document_repository,
            ingestion_repository=ingestion_repository,
            completion_provider=completion_provider,
            usage_service=usage_service,
        )

    def _extract_handler(
        args: ExtractActionItemsArgs,
        context: WorkspaceContext,
        *,
        agent_run_id: UUID,
    ) -> dict:
        return execute_extract_action_items(
            args=args,
            context=context,
            agent_run_id=agent_run_id,
            document_repository=document_repository,
            ingestion_repository=ingestion_repository,
            completion_provider=completion_provider,
            usage_service=usage_service,
        )

    def _compare_handler(
        args: CompareIncidentsArgs,
        context: WorkspaceContext,
        *,
        agent_run_id: UUID,
    ) -> dict:
        return execute_compare_incidents(
            args=args,
            context=context,
            agent_run_id=agent_run_id,
            document_repository=document_repository,
            ingestion_repository=ingestion_repository,
            completion_provider=completion_provider,
            usage_service=usage_service,
        )

    def _debug_handler(
        args: SuggestDebuggingStepsArgs,
        context: WorkspaceContext,
        *,
        agent_run_id: UUID,
    ) -> dict:
        return execute_suggest_debugging_steps(
            args=args,
            context=context,
            agent_run_id=agent_run_id,
            retrieval_service=retrieval_service,
            completion_provider=completion_provider,
            usage_service=usage_service,
        )

    return {
        "search_knowledge_base": RegisteredTool(
            name="search_knowledge_base",
            description=(
                "Search indexed workspace documentation for runbooks, incidents, "
                "and architecture notes. Returns chunk previews with citations."
            ),
            args_model=SearchKnowledgeBaseArgs,
            handler=_search_handler,
        ),
        "summarize_document": RegisteredTool(
            name="summarize_document",
            description=(
                "Summarize a specific indexed document by document_id. "
                "Use when a search result identifies a relevant runbook or incident."
            ),
            args_model=SummarizeDocumentArgs,
            handler=_summarize_handler,
        ),
        "extract_action_items": RegisteredTool(
            name="extract_action_items",
            description=(
                "Extract concrete action items from an indexed document by "
                "document_id, with source citations."
            ),
            args_model=ExtractActionItemsArgs,
            handler=_extract_handler,
        ),
        "compare_incidents": RegisteredTool(
            name="compare_incidents",
            description=(
                "Compare 2–5 incident documents in the same workspace to find "
                "similarities, differences, and recurring root causes."
            ),
            args_model=CompareIncidentsArgs,
            handler=_compare_handler,
        ),
        "suggest_debugging_steps": RegisteredTool(
            name="suggest_debugging_steps",
            description=(
                "Suggest a numbered debugging checklist for a service and symptom, "
                "grounded in retrieved workspace runbooks. Speculative steps are labeled."
            ),
            args_model=SuggestDebuggingStepsArgs,
            handler=_debug_handler,
        ),
    }


def tool_schemas(registry: dict[str, RegisteredTool]) -> list[dict[str, Any]]:
    """Return JSON schema descriptions for LLM planning prompts."""
    schemas: list[dict[str, Any]] = []
    for tool in registry.values():
        schemas.append(
            {
                "name": tool.name,
                "description": tool.description,
                "arguments_schema": tool.args_model.model_json_schema(),
            }
        )
    return schemas
