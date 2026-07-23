"""Map retrieved chunks and LLM output to API citations."""

from __future__ import annotations

from typing import Any
from uuid import UUID

import structlog

from app.modules.rag.schemas import CitationResponse, ContextChunk

logger = structlog.get_logger(__name__)


def build_citations(
    *,
    context_chunks: list[ContextChunk],
    cited_chunk_ids: list[str] | None = None,
) -> list[CitationResponse]:
    """Build citation responses from context chunks and optional LLM references."""
    chunk_by_id = {chunk.chunk_id: chunk for chunk in context_chunks}
    selected_ids: list[UUID]

    if cited_chunk_ids:
        selected_ids = []
        for raw_id in cited_chunk_ids:
            try:
                chunk_id = UUID(str(raw_id))
            except ValueError:
                logger.warning("rag_invalid_cited_chunk_id", chunk_id=raw_id)
                continue
            if chunk_id in chunk_by_id and chunk_id not in selected_ids:
                selected_ids.append(chunk_id)
            elif chunk_id not in chunk_by_id:
                logger.warning(
                    "rag_cited_chunk_not_in_context",
                    chunk_id=str(chunk_id),
                )
    else:
        selected_ids = [chunk.chunk_id for chunk in context_chunks]

    citations: list[CitationResponse] = []
    for chunk_id in selected_ids:
        chunk = chunk_by_id[chunk_id]
        metadata = _citation_metadata(chunk.chunk_metadata)
        citations.append(
            CitationResponse(
                chunk_id=chunk.chunk_id,
                document_id=chunk.document_id,
                document_title=chunk.document_title,
                chunk_preview=chunk.content_preview,
                score=chunk.score,
                metadata=metadata or None,
            )
        )
    return citations


def citations_to_metadata(citations: list[CitationResponse]) -> list[dict[str, Any]]:
    """Serialize citations for assistant message metadata storage."""
    return [citation.model_dump(mode="json") for citation in citations]


def _citation_metadata(
    chunk_metadata: dict[str, Any] | None,
) -> dict[str, Any]:
    if not chunk_metadata:
        return {}

    metadata: dict[str, Any] = {}
    for key in ("page_number", "section", "section_heading", "source_type"):
        value = chunk_metadata.get(key)
        if value is not None:
            metadata[key] = value
    return metadata
