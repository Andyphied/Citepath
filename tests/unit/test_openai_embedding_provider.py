"""Unit tests for OpenAI embedding provider."""

from unittest.mock import MagicMock, patch

import pytest

from app.infrastructure.config import Settings
from app.infrastructure.llm.openai_embedding import OpenAIEmbeddingProvider


def _settings() -> Settings:
    return Settings(
        DATABASE_URL="postgresql://user:pass@localhost:5432/citepath",
        REDIS_URL="redis://localhost:6379/0",
        JWT_SECRET_KEY="test-secret",
        STORAGE_BACKEND="local",
        LLM_PROVIDER="openai",
        OPENAI_API_KEY="sk-test",
        EMBEDDING_MODEL="text-embedding-3-small",
    )


def test_openai_embedding_provider_returns_ordered_vectors() -> None:
    settings = _settings()
    provider = OpenAIEmbeddingProvider(settings=settings)

    embedding_one = MagicMock(index=1, embedding=[0.1, 0.2])
    embedding_zero = MagicMock(index=0, embedding=[0.3, 0.4])
    usage = MagicMock(total_tokens=42)
    response = MagicMock(
        data=[embedding_one, embedding_zero],
        usage=usage,
        model="text-embedding-3-small",
    )

    with patch.object(provider._client.embeddings, "create", return_value=response):
        result = provider.embed(["first", "second"])

    assert result.vectors == [[0.3, 0.4], [0.1, 0.2]]
    assert result.embedding_tokens == 42
    assert result.model == "text-embedding-3-small"
    assert provider.provider_name == "openai"


def test_openai_embedding_provider_requires_api_key() -> None:
    settings = MagicMock()
    settings.OPENAI_API_KEY = None
    settings.EMBEDDING_MODEL = "text-embedding-3-small"

    with pytest.raises(ValueError, match="OPENAI_API_KEY"):
        OpenAIEmbeddingProvider(settings=settings)
