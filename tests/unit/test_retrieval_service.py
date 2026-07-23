"""Unit tests for RetrievalService."""

from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from app.infrastructure.llm.types import EmbeddingResult
from app.modules.ingestion.models import DocumentChunk
from app.modules.ingestion.repository import SimilarChunkResult
from app.modules.retrieval.exceptions import EmptyQueryError, QueryEmbeddingError
from app.modules.retrieval.schemas import DEFAULT_TOP_K, RetrievalFilters
from app.modules.retrieval.service import RetrievalService


class MockEmbeddingProvider:
    """Embedding provider for retrieval service tests."""

    def __init__(
        self,
        *,
        vector_dim: int = 4,
        fail: bool = False,
    ) -> None:
        self.vector_dim = vector_dim
        self.fail = fail
        self.calls: list[list[str]] = []

    @property
    def provider_name(self) -> str:
        return "mock"

    def embed(self, texts: list[str]) -> EmbeddingResult:
        self.calls.append(texts)
        if self.fail:
            raise RuntimeError("embedding provider unavailable")
        return EmbeddingResult(
            vectors=[[1.0] * self.vector_dim],
            embedding_tokens=8,
            model="mock-embedding",
            latency_ms=5,
        )


class StubSettings:
    RETRIEVAL_MIN_SCORE = 0.72


def _chunk(
    *,
    workspace_id,
    document_id,
    content: str,
    chunk_index: int = 0,
) -> DocumentChunk:
    return DocumentChunk(
        id=uuid4(),
        workspace_id=workspace_id,
        document_id=document_id,
        chunk_index=chunk_index,
        content=content,
        embedding=[1.0] * 4,
        metadata_={"section": "deploy"},
        embedding_model="mock-embedding",
    )


@pytest.fixture
def workspace_id():
    return uuid4()


@pytest.fixture
def user_id():
    return uuid4()


def test_search_rejects_empty_query(workspace_id, user_id) -> None:
    service = RetrievalService(
        MagicMock(),
        embedding_provider=MockEmbeddingProvider(),
        settings=StubSettings(),
    )

    with pytest.raises(EmptyQueryError):
        service.search(
            query="   ",
            workspace_id=workspace_id,
            user_id=user_id,
        )


def test_search_raises_on_embedding_failure(workspace_id, user_id) -> None:
    service = RetrievalService(
        MagicMock(),
        embedding_provider=MockEmbeddingProvider(fail=True),
        settings=StubSettings(),
    )

    with pytest.raises(QueryEmbeddingError):
        service.search(
            query="What caused the outage?",
            workspace_id=workspace_id,
            user_id=user_id,
        )


def test_search_returns_scored_chunks_ordered_descending(
    workspace_id,
    user_id,
) -> None:
    document_id = uuid4()
    chunk_high = _chunk(
        workspace_id=workspace_id,
        document_id=document_id,
        content="Restart the API service after deploy.",
        chunk_index=0,
    )
    chunk_low = _chunk(
        workspace_id=workspace_id,
        document_id=document_id,
        content="Check Redis connectivity before scaling workers.",
        chunk_index=1,
    )

    session = MagicMock()
    service = RetrievalService(
        session,
        embedding_provider=MockEmbeddingProvider(),
        settings=StubSettings(),
    )
    service._retrieval_repository = MagicMock()
    service._retrieval_repository.search_similar_with_scores.return_value = [
        SimilarChunkResult(chunk=chunk_low, score=0.75),
        SimilarChunkResult(chunk=chunk_high, score=0.95),
    ]
    service._document_repository = MagicMock()
    service._document_repository.get_by_id.return_value = MagicMock(
        id=document_id,
        title="Runbook",
        source_type="runbook",
        file_type="md",
    )

    result = service.search(
        query="How do I restart the API?",
        workspace_id=workspace_id,
        user_id=user_id,
        top_k=8,
    )

    assert result.insufficient_context is False
    assert result.top_k == DEFAULT_TOP_K
    assert result.min_score == 0.72
    assert len(result.chunks) == 2
    assert result.chunks[0].chunk_id == chunk_high.id
    assert result.chunks[0].citation_id == chunk_high.id
    assert result.chunks[0].score == 0.95
    assert result.chunks[1].chunk_id == chunk_low.id
    assert result.chunks[1].score == 0.75
    assert result.chunks[0].document_metadata.title == "Runbook"
    assert result.chunks[0].document_metadata.chunk_metadata == {"section": "deploy"}


def test_search_flags_insufficient_context_when_all_scores_below_threshold(
    workspace_id,
    user_id,
) -> None:
    document_id = uuid4()
    chunk = _chunk(
        workspace_id=workspace_id,
        document_id=document_id,
        content="Low relevance chunk",
    )

    session = MagicMock()
    service = RetrievalService(
        session,
        embedding_provider=MockEmbeddingProvider(),
        settings=StubSettings(),
    )
    service._retrieval_repository = MagicMock()
    service._retrieval_repository.search_similar_with_scores.return_value = [
        SimilarChunkResult(chunk=chunk, score=0.5),
    ]

    result = service.search(
        query="unrelated question",
        workspace_id=workspace_id,
        user_id=user_id,
    )

    assert result.chunks == []
    assert result.insufficient_context is True


def test_search_flags_insufficient_context_when_no_chunks(
    workspace_id,
    user_id,
) -> None:
    session = MagicMock()
    service = RetrievalService(
        session,
        embedding_provider=MockEmbeddingProvider(),
        settings=StubSettings(),
    )
    service._retrieval_repository = MagicMock()
    service._retrieval_repository.search_similar_with_scores.return_value = []

    result = service.search(
        query="anything",
        workspace_id=workspace_id,
        user_id=user_id,
    )

    assert result.chunks == []
    assert result.insufficient_context is True


def test_search_truncates_content_preview(workspace_id, user_id) -> None:
    document_id = uuid4()
    long_content = "x" * 300
    chunk = _chunk(
        workspace_id=workspace_id,
        document_id=document_id,
        content=long_content,
    )

    session = MagicMock()
    service = RetrievalService(
        session,
        embedding_provider=MockEmbeddingProvider(),
        settings=StubSettings(),
    )
    service._retrieval_repository = MagicMock()
    service._retrieval_repository.search_similar_with_scores.return_value = [
        SimilarChunkResult(chunk=chunk, score=0.9),
    ]
    service._document_repository = MagicMock()
    service._document_repository.get_by_id.return_value = None

    result = service.search(
        query="preview test",
        workspace_id=workspace_id,
        user_id=user_id,
    )

    assert len(result.chunks[0].content_preview) == 200


def test_search_caches_query_embedding_within_request(
    workspace_id,
    user_id,
) -> None:
    provider = MockEmbeddingProvider()
    session = MagicMock()
    service = RetrievalService(
        session,
        embedding_provider=provider,
        settings=StubSettings(),
    )
    service._retrieval_repository = MagicMock()
    service._retrieval_repository.search_similar_with_scores.return_value = []

    service.search(
        query="same query",
        workspace_id=workspace_id,
        user_id=user_id,
    )
    service.search(
        query="same query",
        workspace_id=workspace_id,
        user_id=user_id,
    )

    assert provider.calls == [["same query"]]


def test_search_passes_metadata_filters_to_repository(
    workspace_id,
    user_id,
) -> None:
    document_id = uuid4()
    chunk = _chunk(
        workspace_id=workspace_id,
        document_id=document_id,
        content="PDF-only content",
    )

    session = MagicMock()
    service = RetrievalService(
        session,
        embedding_provider=MockEmbeddingProvider(),
        settings=StubSettings(),
    )
    service._retrieval_repository = MagicMock()
    service._retrieval_repository.search_similar_with_scores.return_value = [
        SimilarChunkResult(chunk=chunk, score=0.9),
    ]
    service._document_repository = MagicMock()
    service._document_repository.get_by_id.return_value = MagicMock(
        id=document_id,
        title="PDF Doc",
        source_type="runbook",
        file_type="pdf",
    )

    filters = RetrievalFilters(file_type="pdf", source_type="runbook", document_id=document_id)
    service.search(
        query="filtered search",
        workspace_id=workspace_id,
        user_id=user_id,
        filters=filters,
    )

    service._retrieval_repository.search_similar_with_scores.assert_called_once_with(
        workspace_id=workspace_id,
        embedding=[1.0] * 4,
        top_k=DEFAULT_TOP_K,
        file_type="pdf",
        source_type="runbook",
        document_id=document_id,
    )


def test_retrieval_filters_rejects_invalid_file_type() -> None:
    with pytest.raises(ValueError):
        RetrievalFilters(file_type="docx")
