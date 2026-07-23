"""Chat completion calls with usage logging for RAG answers."""

from __future__ import annotations

from typing import Any
from uuid import UUID

import structlog

from app.infrastructure.db.enums import UsageEventStatus, UsageOperation
from app.infrastructure.llm.completion import ChatCompletionProvider
from app.modules.rag.exceptions import ChatCompletionError
from app.modules.usage.service import UsageEventInput, UsageService

logger = structlog.get_logger(__name__)


def complete_rag_answer(
    *,
    messages: list[dict[str, str]],
    completion_provider: ChatCompletionProvider,
    usage_service: UsageService,
    workspace_id: UUID,
    user_id: UUID,
    prompt_version: str,
    response_format: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
) -> str:
    """Call the chat provider and log a chat_completion usage event."""
    event_metadata: dict[str, Any] = {
        "purpose": "rag_answer",
        "prompt_version": prompt_version,
    }
    if metadata:
        event_metadata.update(metadata)

    provider_name = completion_provider.provider_name
    try:
        result = completion_provider.complete(
            messages=messages,
            response_format=response_format,
        )
    except Exception as exc:
        logger.warning("rag_chat_completion_failed", error=str(exc))
        usage_service.log_event(
            UsageEventInput(
                workspace_id=workspace_id,
                user_id=user_id,
                provider=provider_name,
                model="unknown",
                operation=UsageOperation.CHAT_COMPLETION,
                latency_ms=None,
                status=UsageEventStatus.FAILED,
                metadata=event_metadata,
            )
        )
        raise ChatCompletionError("Chat completion failed") from exc

    usage_service.log_event(
        UsageEventInput(
            workspace_id=workspace_id,
            user_id=user_id,
            provider=provider_name,
            model=result.model,
            operation=UsageOperation.CHAT_COMPLETION,
            prompt_tokens=result.prompt_tokens,
            completion_tokens=result.completion_tokens,
            latency_ms=result.latency_ms,
            status=UsageEventStatus.SUCCESS,
            metadata=event_metadata,
        )
    )
    return result.content
