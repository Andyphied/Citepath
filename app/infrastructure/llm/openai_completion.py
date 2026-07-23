"""OpenAI chat completion provider implementation."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

from openai import OpenAI

from app.infrastructure.llm.types import CompletionResult

if TYPE_CHECKING:
    from app.infrastructure.config import Settings


class OpenAIChatCompletionProvider:
    """OpenAI chat completions API behind the ChatCompletionProvider protocol."""

    def __init__(self, *, settings: Settings) -> None:
        if not settings.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY is required for OpenAI chat completions")
        self._client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self._model = settings.CHAT_MODEL

    @property
    def provider_name(self) -> str:
        return "openai"

    def complete(
        self,
        *,
        messages: list[dict[str, str]],
        response_format: dict[str, Any] | None = None,
    ) -> CompletionResult:
        started_at = time.perf_counter()
        kwargs: dict[str, Any] = {
            "model": self._model,
            "messages": messages,
        }
        if response_format is not None:
            kwargs["response_format"] = response_format

        response = self._client.chat.completions.create(**kwargs)
        latency_ms = int((time.perf_counter() - started_at) * 1000)

        choice = response.choices[0]
        content = choice.message.content or ""
        prompt_tokens = response.usage.prompt_tokens if response.usage else 0
        completion_tokens = (
            response.usage.completion_tokens if response.usage else 0
        )

        return CompletionResult(
            content=content,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            model=response.model or self._model,
            latency_ms=latency_ms,
        )
