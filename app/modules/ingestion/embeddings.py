"""Batch embedding generation for ingestion chunks."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

import structlog

from app.infrastructure.db.enums import UsageEventStatus, UsageOperation
from app.infrastructure.llm.embedding import EmbeddingProvider
from app.modules.ingestion.chunker import ContentChunk, EmbeddedChunk
from app.modules.ingestion.retry import is_retryable_exception
from app.modules.usage.service import UsageEventInput, UsageService

logger = structlog.get_logger(__name__)


@dataclass(frozen=True)
class EmbeddingError:
    """Embedding batch failure surfaced to the ingestion worker."""

    message: str
    retryable: bool = False


def _log_embedding_usage(
    *,
    usage_service: UsageService,
    workspace_id: UUID,
    document_id: UUID,
    job_id: UUID,
    provider_name: str,
    model: str,
    embedding_tokens: int,
    latency_ms: int | None,
    status: UsageEventStatus,
    batch_size: int,
) -> None:
    usage_service.log_event(
        UsageEventInput(
            workspace_id=workspace_id,
            user_id=None,
            provider=provider_name,
            model=model,
            operation=UsageOperation.EMBEDDING_DOCUMENT,
            embedding_tokens=embedding_tokens,
            latency_ms=latency_ms,
            status=status,
            metadata={
                "document_id": str(document_id),
                "job_id": str(job_id),
                "batch_size": batch_size,
            },
        )
    )


def _embed_batch_with_retry(
    *,
    embedding_provider: EmbeddingProvider,
    texts: list[str],
) -> tuple[list[list[float]], str, int, int] | EmbeddingError:
    """Call the provider once; retry the batch once on failure."""
    last_error: Exception | None = None
    for attempt in range(2):
        try:
            result = embedding_provider.embed(texts)
            if len(result.vectors) != len(texts):
                return EmbeddingError(
                    message=(
                        "Embedding provider returned "
                        f"{len(result.vectors)} vectors for {len(texts)} texts"
                    ),
                    retryable=False,
                )
            return (
                result.vectors,
                result.model,
                result.embedding_tokens,
                result.latency_ms,
            )
        except Exception as exc:
            last_error = exc
            if attempt == 0:
                logger.warning(
                    "ingestion_embedding_batch_retry",
                    batch_size=len(texts),
                    error=str(exc),
                )
                continue
            break

    message = (
        f"Embedding generation failed after retry: {last_error}"
        if last_error is not None
        else "Embedding generation failed after retry"
    )
    retryable = is_retryable_exception(last_error) if last_error is not None else False
    return EmbeddingError(message=message, retryable=retryable)


def embed_content_chunks(
    *,
    chunks: list[ContentChunk],
    embedding_provider: EmbeddingProvider,
    usage_service: UsageService,
    workspace_id: UUID,
    document_id: UUID,
    job_id: UUID,
    batch_size: int,
    embedding_model: str,
) -> list[EmbeddedChunk] | EmbeddingError:
    """Embed chunks in batches with usage logging and one retry."""
    if not chunks:
        return []

    embedded_chunks: list[EmbeddedChunk] = []
    provider_name = embedding_provider.provider_name

    for batch_start in range(0, len(chunks), batch_size):
        batch = chunks[batch_start:batch_start + batch_size]
        texts = [chunk.content for chunk in batch]

        outcome = _embed_batch_with_retry(
            embedding_provider=embedding_provider,
            texts=texts,
        )
        if isinstance(outcome, EmbeddingError):
            _log_embedding_usage(
                usage_service=usage_service,
                workspace_id=workspace_id,
                document_id=document_id,
                job_id=job_id,
                provider_name=provider_name,
                model=embedding_model,
                embedding_tokens=0,
                latency_ms=None,
                status=UsageEventStatus.FAILED,
                batch_size=len(batch),
            )
            return outcome

        vectors, model, embedding_tokens, latency_ms = outcome
        _log_embedding_usage(
            usage_service=usage_service,
            workspace_id=workspace_id,
            document_id=document_id,
            job_id=job_id,
            provider_name=provider_name,
            model=model,
            embedding_tokens=embedding_tokens,
            latency_ms=latency_ms,
            status=UsageEventStatus.SUCCESS,
            batch_size=len(batch),
        )

        for chunk, vector in zip(batch, vectors, strict=True):
            embedded_chunks.append(
                EmbeddedChunk(
                    content=chunk.content,
                    chunk_index=chunk.chunk_index,
                    metadata=chunk.metadata,
                    embedding=vector,
                    embedding_model=model,
                )
            )

    return embedded_chunks
