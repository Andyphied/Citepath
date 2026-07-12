"""LLM and embedding provider abstractions."""

from app.infrastructure.llm.factory import create_embedding_provider
from app.infrastructure.llm.types import EmbeddingResult

__all__ = ["EmbeddingResult", "create_embedding_provider"]
