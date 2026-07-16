"""Unit tests for query embedding usage logging."""

from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from app.infrastructure.db.enums import UsageEventStatus, UsageOperation
from app.infrastructure.llm.types import EmbeddingResult
from app.modules.retrieval.embeddings import (
    QueryEmbeddingError,
    QueryEmbeddingResult,
    embed_query_text,
)


class MockEmbeddingProvider:
    """Configurable embedding provider for retrieval tests."""

    def __init__(
        self,
        *,
        vector_dim: int = 4,
        embedding_tokens: int = 8,
        fail: bool = False,
        wrong_vector_count: bool = False,
    ) -> None:
        self.vector_dim = vector_dim
        self.embedding_tokens = embedding_tokens
        self.fail = fail
        self.wrong_vector_count = wrong_vector_count
        self.calls: list[list[str]] = []

    @property
    def provider_name(self) -> str:
        return "mock"

    def embed(self, texts: list[str]) -> EmbeddingResult:
        self.calls.append(texts)
        if self.fail:
            raise RuntimeError("embedding provider unavailable")
        if self.wrong_vector_count:
            return EmbeddingResult(
                vectors=[],
                embedding_tokens=0,
                model="mock-embedding",
                latency_ms=5,
            )

        return EmbeddingResult(
            vectors=[[1.0] * self.vector_dim],
            embedding_tokens=self.embedding_tokens,
            model="mock-embedding",
            latency_ms=5,
        )


@pytest.fixture
def workspace_id():
    return uuid4()


@pytest.fixture
def user_id():
    return uuid4()


def test_embed_query_text_returns_vector_and_logs_usage(
    workspace_id,
    user_id,
) -> None:
    provider = MockEmbeddingProvider(embedding_tokens=12)
    usage_service = MagicMock()
    conversation_id = uuid4()

    result = embed_query_text(
        query="What caused the outage?",
        embedding_provider=provider,
        usage_service=usage_service,
        workspace_id=workspace_id,
        user_id=user_id,
        metadata={"conversation_id": str(conversation_id)},
    )

    assert isinstance(result, QueryEmbeddingResult)
    assert result.model == "mock-embedding"
    assert len(result.vector) == 4
    assert provider.calls == [["What caused the outage?"]]

    usage_service.log_event.assert_called_once()
    event = usage_service.log_event.call_args.args[0]
    assert event.workspace_id == workspace_id
    assert event.user_id == user_id
    assert event.operation == UsageOperation.EMBEDDING_QUERY
    assert event.embedding_tokens == 12
    assert event.status == UsageEventStatus.SUCCESS
    assert event.metadata["conversation_id"] == str(conversation_id)
    assert event.metadata["query_length"] == len("What caused the outage?")


def test_embed_query_text_logs_failed_usage_on_provider_error(
    workspace_id,
    user_id,
) -> None:
    provider = MockEmbeddingProvider(fail=True)
    usage_service = MagicMock()

    result = embed_query_text(
        query="status?",
        embedding_provider=provider,
        usage_service=usage_service,
        workspace_id=workspace_id,
        user_id=user_id,
    )

    assert isinstance(result, QueryEmbeddingError)
    failure_event = usage_service.log_event.call_args.args[0]
    assert failure_event.operation == UsageOperation.EMBEDDING_QUERY
    assert failure_event.status == UsageEventStatus.FAILED
    assert failure_event.embedding_tokens == 0


def test_embed_query_text_logs_failed_usage_on_vector_count_mismatch(
    workspace_id,
    user_id,
) -> None:
    provider = MockEmbeddingProvider(wrong_vector_count=True)
    usage_service = MagicMock()

    result = embed_query_text(
        query="status?",
        embedding_provider=provider,
        usage_service=usage_service,
        workspace_id=workspace_id,
        user_id=user_id,
    )

    assert isinstance(result, QueryEmbeddingError)
    failure_event = usage_service.log_event.call_args.args[0]
    assert failure_event.operation == UsageOperation.EMBEDDING_QUERY
    assert failure_event.status == UsageEventStatus.FAILED
