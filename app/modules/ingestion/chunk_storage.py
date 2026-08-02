"""Persist embedded ingestion chunks to pgvector."""

from dataclasses import dataclass
from uuid import UUID

import structlog

from app.modules.ingestion.chunker import EmbeddedChunk
from app.modules.ingestion.repository import IngestionRepository
from app.modules.ingestion.retry import is_retryable_exception

logger = structlog.get_logger(__name__)


@dataclass(frozen=True)
class ChunkStorageError:
    """Chunk persistence failed."""

    message: str
    retryable: bool = False


def persist_embedded_chunks(
    *,
    ingestion_repository: IngestionRepository,
    embedded_chunks: list[EmbeddedChunk],
    workspace_id: UUID,
    document_id: UUID,
) -> int | ChunkStorageError:
    """Replace document chunks with embedded vectors; returns chunk count or error."""
    try:
        ingestion_repository.replace_chunks_for_document(
            workspace_id=workspace_id,
            document_id=document_id,
            embedded_chunks=embedded_chunks,
        )
        return len(embedded_chunks)
    except Exception as exc:
        logger.exception(
            "ingestion_chunk_storage_failed",
            workspace_id=str(workspace_id),
            document_id=str(document_id),
            chunk_count=len(embedded_chunks),
        )
        return ChunkStorageError(
            message=str(exc),
            retryable=is_retryable_exception(exc),
        )
