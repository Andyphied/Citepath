"""Query embedding generation with usage logging for RET-001."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

import structlog

from app.infrastructure.db.enums import UsageEventStatus, UsageOperation
from app.infrastructure.llm.embedding import EmbeddingProvider
from app.modules.usage.service import UsageEventInput, UsageService

logger = structlog.get_logger(__name__)


@dataclass(frozen=True)
class QueryEmbeddingResult:
    """Successful query embedding for retrieval."""

    vector: list[float]
    model: str


@dataclass(frozen=True)
class QueryEmbeddingError:
    """Query embedding failure surfaced to retrieval callers."""

    message: str


def embed_query_text(
    *,
    query: str,
    embedding_provider: EmbeddingProvider,
    usage_service: UsageService,
    workspace_id: UUID,
    user_id: UUID | None,
    metadata: dict[str, Any] | None = None,
) -> QueryEmbeddingResult | QueryEmbeddingError:
    """Embed a single query string and log one usage event."""
    event_metadata: dict[str, Any] = {"query_length": len(query)}
    if metadata:
        event_metadata.update(metadata)

    provider_name = embedding_provider.provider_name
    try:
        result = embedding_provider.embed([query])
    except Exception as exc:
        logger.warning("retrieval_query_embedding_failed", error=str(exc))
        usage_service.log_event(
            UsageEventInput(
                workspace_id=workspace_id,
                user_id=user_id,
                provider=provider_name,
                model="unknown",
                operation=UsageOperation.EMBEDDING_QUERY,
                embedding_tokens=0,
                latency_ms=None,
                status=UsageEventStatus.FAILED,
                metadata=event_metadata,
            )
        )
        return QueryEmbeddingError(message=f"Query embedding failed: {exc}")

    if len(result.vectors) != 1:
        usage_service.log_event(
            UsageEventInput(
                workspace_id=workspace_id,
                user_id=user_id,
                provider=provider_name,
                model=result.model,
                operation=UsageOperation.EMBEDDING_QUERY,
                embedding_tokens=0,
                latency_ms=result.latency_ms,
                status=UsageEventStatus.FAILED,
                metadata=event_metadata,
            )
        )
        return QueryEmbeddingError(
            message=(
                "Embedding provider returned "
                f"{len(result.vectors)} vectors for one query"
            )
        )

    usage_service.log_event(
        UsageEventInput(
            workspace_id=workspace_id,
            user_id=user_id,
            provider=provider_name,
            model=result.model,
            operation=UsageOperation.EMBEDDING_QUERY,
            embedding_tokens=result.embedding_tokens,
            latency_ms=result.latency_ms,
            status=UsageEventStatus.SUCCESS,
            metadata=event_metadata,
        )
    )
    return QueryEmbeddingResult(vector=result.vectors[0], model=result.model)
