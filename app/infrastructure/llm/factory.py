"""Factory helpers for LLM and embedding providers."""

from app.infrastructure.config import Settings
from app.infrastructure.llm.embedding import EmbeddingProvider
from app.infrastructure.llm.openai_embedding import OpenAIEmbeddingProvider


def create_embedding_provider(settings: Settings) -> EmbeddingProvider:
    """Build the configured embedding provider from application settings."""
    return OpenAIEmbeddingProvider(settings=settings)
