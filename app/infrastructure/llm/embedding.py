"""Embedding provider protocol."""

from typing import Protocol

from app.infrastructure.llm.types import EmbeddingResult


class EmbeddingProvider(Protocol):
    """Generate vector embeddings for one or more text inputs."""

    @property
    def provider_name(self) -> str:
        """Provider identifier for usage logging (e.g. openai)."""
        ...

    def embed(self, texts: list[str]) -> EmbeddingResult:
        """Embed texts in a single provider call."""
        ...
