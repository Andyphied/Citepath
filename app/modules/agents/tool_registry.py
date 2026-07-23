"""Static tool registry for MVP agent tools."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel

from app.modules.agents.schemas import SearchKnowledgeBaseArgs
from app.modules.agents.tools.search_knowledge_base import execute_search_knowledge_base
from app.modules.retrieval.service import RetrievalService
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
) -> dict[str, RegisteredTool]:
    """Build the static MVP tool registry."""

    def _search_handler(args: SearchKnowledgeBaseArgs, context: WorkspaceContext) -> dict:
        return execute_search_knowledge_base(
            args=args,
            context=context,
            retrieval_service=retrieval_service,
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
