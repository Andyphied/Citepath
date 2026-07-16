"""Unit tests for ingestion embedding batching."""

from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from app.infrastructure.db.enums import UsageEventStatus, UsageOperation
from app.infrastructure.llm.types import EmbeddingResult
from app.modules.ingestion.chunker import ContentChunk
from app.modules.ingestion.embeddings import EmbeddingError, embed_content_chunks


class MockEmbeddingProvider:
    """Configurable embedding provider for tests."""

    def __init__(
        self,
        *,
        vector_dim: int = 4,
        embedding_tokens: int = 10,
        fail_times: int = 0,
    ) -> None:
        self.vector_dim = vector_dim
        self.embedding_tokens = embedding_tokens
        self.fail_times = fail_times
        self.calls: list[list[str]] = []

    @property
    def provider_name(self) -> str:
        return "mock"

    def embed(self, texts: list[str]) -> EmbeddingResult:
        self.calls.append(texts)
        if self.fail_times > 0:
            self.fail_times -= 1
            raise RuntimeError("embedding provider unavailable")

        vectors = [[float(index)] * self.vector_dim for index in range(len(texts))]
        return EmbeddingResult(
            vectors=vectors,
            embedding_tokens=self.embedding_tokens * len(texts),
            model="mock-embedding",
            latency_ms=12,
        )


def _make_chunk(index: int) -> ContentChunk:
    return ContentChunk(
        content=f"chunk {index}",
        chunk_index=index,
        metadata={"chunk_index": index},
    )


@pytest.fixture
def workspace_id():
    return uuid4()


@pytest.fixture
def document_id():
    return uuid4()


@pytest.fixture
def job_id():
    return uuid4()


def test_embed_content_chunks_returns_embedded_chunks(
    workspace_id,
    document_id,
    job_id,
) -> None:
    chunks = [_make_chunk(0), _make_chunk(1)]
    provider = MockEmbeddingProvider()
    usage_service = MagicMock()

    result = embed_content_chunks(
        chunks=chunks,
        embedding_provider=provider,
        usage_service=usage_service,
        workspace_id=workspace_id,
        document_id=document_id,
        job_id=job_id,
        batch_size=64,
        embedding_model="text-embedding-3-small",
    )

    assert not isinstance(result, EmbeddingError)
    assert len(result) == 2
    assert all(chunk.embedding is not None for chunk in result)
    assert result[0].embedding_model == "mock-embedding"
    usage_service.log_event.assert_called_once()
    success_event = usage_service.log_event.call_args.args[0]
    assert success_event.workspace_id == workspace_id
    assert success_event.embedding_tokens == 20
    assert success_event.operation == UsageOperation.EMBEDDING_DOCUMENT
    assert success_event.metadata["document_id"] == str(document_id)
    assert success_event.metadata["job_id"] == str(job_id)


def test_embed_content_chunks_embeds_ten_chunks_in_one_batch(
    workspace_id,
    document_id,
    job_id,
) -> None:
    chunks = [_make_chunk(index) for index in range(10)]
    provider = MockEmbeddingProvider(embedding_tokens=5)
    usage_service = MagicMock()

    result = embed_content_chunks(
        chunks=chunks,
        embedding_provider=provider,
        usage_service=usage_service,
        workspace_id=workspace_id,
        document_id=document_id,
        job_id=job_id,
        batch_size=64,
        embedding_model="text-embedding-3-small",
    )

    assert not isinstance(result, EmbeddingError)
    assert len(result) == 10
    assert all(chunk.embedding is not None for chunk in result)
    assert [chunk.chunk_index for chunk in result] == list(range(10))
    assert len(provider.calls) == 1
    assert len(provider.calls[0]) == 10
    usage_service.log_event.assert_called_once()
    success_event = usage_service.log_event.call_args.args[0]
    assert success_event.embedding_tokens == 50
    assert success_event.workspace_id == workspace_id


def test_embed_content_chunks_batches_by_size(
    workspace_id,
    document_id,
    job_id,
) -> None:
    chunks = [_make_chunk(index) for index in range(5)]
    provider = MockEmbeddingProvider()
    usage_service = MagicMock()

    result = embed_content_chunks(
        chunks=chunks,
        embedding_provider=provider,
        usage_service=usage_service,
        workspace_id=workspace_id,
        document_id=document_id,
        job_id=job_id,
        batch_size=2,
        embedding_model="text-embedding-3-small",
    )

    assert not isinstance(result, EmbeddingError)
    assert len(result) == 5
    assert len(provider.calls) == 3
    assert usage_service.log_event.call_count == 3


def test_embed_content_chunks_retries_failed_batch_once(
    workspace_id,
    document_id,
    job_id,
) -> None:
    chunks = [_make_chunk(0)]
    provider = MockEmbeddingProvider(fail_times=1)
    usage_service = MagicMock()

    result = embed_content_chunks(
        chunks=chunks,
        embedding_provider=provider,
        usage_service=usage_service,
        workspace_id=workspace_id,
        document_id=document_id,
        job_id=job_id,
        batch_size=64,
        embedding_model="text-embedding-3-small",
    )

    assert not isinstance(result, EmbeddingError)
    assert len(provider.calls) == 2


def test_embed_content_chunks_fails_after_retry_exhausted(
    workspace_id,
    document_id,
    job_id,
) -> None:
    chunks = [_make_chunk(0)]
    provider = MockEmbeddingProvider(fail_times=2)
    usage_service = MagicMock()

    result = embed_content_chunks(
        chunks=chunks,
        embedding_provider=provider,
        usage_service=usage_service,
        workspace_id=workspace_id,
        document_id=document_id,
        job_id=job_id,
        batch_size=64,
        embedding_model="text-embedding-3-small",
    )

    assert isinstance(result, EmbeddingError)
    assert "after retry" in result.message
    assert len(provider.calls) == 2

    failure_event = usage_service.log_event.call_args.args[0]
    assert failure_event.status == UsageEventStatus.FAILED
    assert failure_event.operation == UsageOperation.EMBEDDING_DOCUMENT
    assert failure_event.user_id is None
    assert failure_event.metadata["document_id"] == str(document_id)
    assert failure_event.metadata["job_id"] == str(job_id)


def test_embed_content_chunks_empty_input(workspace_id, document_id, job_id) -> None:
    provider = MockEmbeddingProvider()
    usage_service = MagicMock()

    result = embed_content_chunks(
        chunks=[],
        embedding_provider=provider,
        usage_service=usage_service,
        workspace_id=workspace_id,
        document_id=document_id,
        job_id=job_id,
        batch_size=64,
        embedding_model="text-embedding-3-small",
    )

    assert result == []
    assert provider.calls == []
    usage_service.log_event.assert_not_called()
