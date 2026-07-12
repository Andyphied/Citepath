"""Unit tests for embedded chunk persistence."""

from unittest.mock import MagicMock
from uuid import uuid4

from app.modules.ingestion.chunk_storage import ChunkStorageError, persist_embedded_chunks
from app.modules.ingestion.chunker import EmbeddedChunk


def _embedded_chunk(*, chunk_index: int = 0) -> EmbeddedChunk:
    vector = [0.0] * 1536
    vector[0] = 0.5
    return EmbeddedChunk(
        content=f"chunk {chunk_index}",
        chunk_index=chunk_index,
        metadata={"index": chunk_index},
        embedding=vector,
        embedding_model="text-embedding-3-small",
    )


def test_persist_embedded_chunks_returns_chunk_count() -> None:
    repository = MagicMock()
    workspace_id = uuid4()
    document_id = uuid4()
    embedded_chunks = [_embedded_chunk(chunk_index=0), _embedded_chunk(chunk_index=1)]

    result = persist_embedded_chunks(
        ingestion_repository=repository,
        embedded_chunks=embedded_chunks,
        workspace_id=workspace_id,
        document_id=document_id,
    )

    assert result == 2
    repository.replace_chunks_for_document.assert_called_once_with(
        workspace_id=workspace_id,
        document_id=document_id,
        embedded_chunks=embedded_chunks,
    )


def test_persist_embedded_chunks_returns_error_on_repository_failure() -> None:
    repository = MagicMock()
    repository.replace_chunks_for_document.side_effect = RuntimeError("db write failed")

    result = persist_embedded_chunks(
        ingestion_repository=repository,
        embedded_chunks=[_embedded_chunk()],
        workspace_id=uuid4(),
        document_id=uuid4(),
    )

    assert isinstance(result, ChunkStorageError)
    assert "db write failed" in result.message
