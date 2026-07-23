"""Shared types for LLM provider integrations."""

from dataclasses import dataclass


@dataclass(frozen=True)
class EmbeddingResult:
    """Normalized embedding provider response."""

    vectors: list[list[float]]
    embedding_tokens: int
    model: str
    latency_ms: int


@dataclass(frozen=True)
class CompletionResult:
    """Normalized chat completion provider response."""

    content: str
    prompt_tokens: int
    completion_tokens: int
    model: str
    latency_ms: int
