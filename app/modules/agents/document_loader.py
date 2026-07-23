"""Workspace-scoped document chunk loading for agent tools."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from app.infrastructure.db.enums import DocumentStatus
from app.modules.agents.token_budget import MAX_TOOL_INPUT_TOKENS, count_tokens
from app.modules.documents.repository import DocumentRepository
from app.modules.ingestion.models import DocumentChunk
from app.modules.ingestion.repository import IngestionRepository

# Stable codes — never leak foreign workspace titles or content.
ERROR_DOCUMENT_NOT_AVAILABLE = "document_not_available"
ERROR_DOCUMENT_NOT_INDEXED = "document_not_indexed"
ERROR_DOCUMENT_EMPTY = "document_empty"


@dataclass(frozen=True)
class LoadedChunk:
    """Chunk text with citation identifiers for tool outputs."""

    chunk_id: UUID
    document_id: UUID
    document_title: str | None
    content: str
    chunk_index: int
    metadata: dict[str, Any] | None


@dataclass(frozen=True)
class DocumentLoadResult:
    """Result of loading a workspace-scoped document for an agent tool."""

    document_id: UUID
    title: str | None
    chunks: list[LoadedChunk]
    truncated: bool
    error: str | None


def load_document_for_tool(
    *,
    document_id: UUID,
    workspace_id: UUID,
    document_repository: DocumentRepository,
    ingestion_repository: IngestionRepository,
    max_input_tokens: int = MAX_TOOL_INPUT_TOKENS,
) -> DocumentLoadResult:
    """Load indexed document chunks for a tool, scoped to workspace_id.

    Foreign / missing documents return ``document_not_available`` without
    leaking titles or content from other workspaces.
    """
    document = document_repository.get_by_id(
        workspace_id=workspace_id,
        id=document_id,
    )
    if document is None:
        return DocumentLoadResult(
            document_id=document_id,
            title=None,
            chunks=[],
            truncated=False,
            error=ERROR_DOCUMENT_NOT_AVAILABLE,
        )

    if document.status != DocumentStatus.INDEXED:
        return DocumentLoadResult(
            document_id=document_id,
            title=document.title,
            chunks=[],
            truncated=False,
            error=ERROR_DOCUMENT_NOT_INDEXED,
        )

    raw_chunks = ingestion_repository.list_chunks_for_document(
        workspace_id=workspace_id,
        document_id=document_id,
    )
    if not raw_chunks:
        return DocumentLoadResult(
            document_id=document_id,
            title=document.title,
            chunks=[],
            truncated=False,
            error=ERROR_DOCUMENT_EMPTY,
        )

    selected, truncated = _select_chunks_within_budget(
        raw_chunks,
        document_title=document.title,
        max_input_tokens=max_input_tokens,
    )
    return DocumentLoadResult(
        document_id=document_id,
        title=document.title,
        chunks=selected,
        truncated=truncated,
        error=None,
    )


def chunks_to_citations(chunks: list[LoadedChunk]) -> list[dict]:
    """Build citation payloads from loaded chunks."""
    citations: list[dict] = []
    for chunk in chunks:
        preview = chunk.content[:400]
        if len(chunk.content) > 400:
            preview = preview + "…"
        citations.append(
            {
                "chunk_id": str(chunk.chunk_id),
                "document_id": str(chunk.document_id),
                "document_title": chunk.document_title,
                "chunk_preview": preview,
                "score": 1.0,
                "metadata": chunk.metadata,
            }
        )
    return citations


def format_chunks_for_prompt(chunks: list[LoadedChunk]) -> str:
    """Format chunk text for LLM prompts with stable delimiters."""
    parts: list[str] = []
    for chunk in chunks:
        title = chunk.document_title or "untitled"
        parts.append(
            f"<<<DOCUMENT_DATA chunk_id={chunk.chunk_id} "
            f"document_id={chunk.document_id} title={title}>>>\n"
            f"{chunk.content}\n"
            f"<<<END_DOCUMENT_DATA>>>"
        )
    return "\n\n".join(parts)


def batch_chunks_by_token_budget(
    chunks: list[LoadedChunk],
    *,
    max_input_tokens: int = MAX_TOOL_INPUT_TOKENS,
) -> list[list[LoadedChunk]]:
    """Split chunks into sequential batches that fit the token budget."""
    if not chunks:
        return []

    batches: list[list[LoadedChunk]] = []
    current: list[LoadedChunk] = []
    current_tokens = 0

    for chunk in chunks:
        chunk_tokens = count_tokens(chunk.content)
        if current and current_tokens + chunk_tokens > max_input_tokens:
            batches.append(current)
            current = []
            current_tokens = 0
        current.append(chunk)
        current_tokens += chunk_tokens

    if current:
        batches.append(current)
    return batches


def _select_chunks_within_budget(
    raw_chunks: list[DocumentChunk],
    *,
    document_title: str | None,
    max_input_tokens: int,
) -> tuple[list[LoadedChunk], bool]:
    """Take chunks in order until the token budget is exhausted."""
    selected: list[LoadedChunk] = []
    used_tokens = 0
    for raw in raw_chunks:
        chunk_tokens = count_tokens(raw.content)
        if selected and used_tokens + chunk_tokens > max_input_tokens:
            return selected, True
        selected.append(
            LoadedChunk(
                chunk_id=raw.id,
                document_id=raw.document_id,
                document_title=document_title,
                content=raw.content,
                chunk_index=raw.chunk_index,
                metadata=raw.metadata_,
            )
        )
        used_tokens += chunk_tokens
        if used_tokens >= max_input_tokens:
            truncated = len(selected) < len(raw_chunks)
            return selected, truncated
    return selected, False


def unavailable_document_output(document_id: UUID, *, error: str) -> dict:
    """Safe tool failure payload that does not leak cross-workspace data."""
    messages = {
        ERROR_DOCUMENT_NOT_AVAILABLE: (
            "Document is not available in this workspace."
        ),
        ERROR_DOCUMENT_NOT_INDEXED: (
            "Document is not indexed yet and cannot be used by this tool."
        ),
        ERROR_DOCUMENT_EMPTY: (
            "Document has no indexed chunks available for this tool."
        ),
    }
    return {
        "content": messages.get(error, "Document cannot be processed."),
        "citations": [],
        "related_documents": [],
        "error": error,
        "document_id": str(document_id),
    }
