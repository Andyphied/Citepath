"""Chat completion provider protocol."""

from typing import Any, Protocol

from app.infrastructure.llm.types import CompletionResult


class ChatCompletionProvider(Protocol):
    """Generate chat completions from message lists."""

    @property
    def provider_name(self) -> str:
        """Provider identifier for usage logging (e.g. openai)."""
        ...

    def complete(
        self,
        *,
        messages: list[dict[str, str]],
        response_format: dict[str, Any] | None = None,
    ) -> CompletionResult:
        """Complete a chat conversation with optional structured output."""
        ...
