"""OpenAI embedding provider implementation."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from openai import OpenAI

from app.infrastructure.llm.types import EmbeddingResult

if TYPE_CHECKING:
    from app.infrastructure.config import Settings


class OpenAIEmbeddingProvider:
    """OpenAI embeddings API behind the EmbeddingProvider protocol."""

    def __init__(self, *, settings: Settings) -> None:
        if not settings.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY is required for OpenAI embeddings")
        self._client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self._model = settings.EMBEDDING_MODEL

    @property
    def provider_name(self) -> str:
        return "openai"

    def embed(self, texts: list[str]) -> EmbeddingResult:
        if not texts:
            return EmbeddingResult(
                vectors=[],
                embedding_tokens=0,
                model=self._model,
                latency_ms=0,
            )

        started_at = time.perf_counter()
        response = self._client.embeddings.create(
            input=texts,
            model=self._model,
        )
        latency_ms = int((time.perf_counter() - started_at) * 1000)

        ordered = sorted(response.data, key=lambda item: item.index)
        vectors = [item.embedding for item in ordered]
        embedding_tokens = response.usage.total_tokens if response.usage else 0

        return EmbeddingResult(
            vectors=vectors,
            embedding_tokens=embedding_tokens,
            model=response.model or self._model,
            latency_ms=latency_ms,
        )
