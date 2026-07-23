"""Agent LLM completion helpers with usage logging."""

from __future__ import annotations

import json
from typing import Any
from uuid import UUID

import structlog

from app.infrastructure.db.enums import UsageEventStatus, UsageOperation
from app.infrastructure.llm.completion import ChatCompletionProvider
from app.modules.agents.exceptions import AgentCompletionError
from app.modules.usage.service import UsageEventInput, UsageService

logger = structlog.get_logger(__name__)


def complete_agent_step(
    *,
    messages: list[dict[str, str]],
    completion_provider: ChatCompletionProvider,
    usage_service: UsageService,
    workspace_id: UUID,
    user_id: UUID,
    agent_run_id: UUID,
    purpose: str,
    response_format: dict[str, Any] | None = None,
) -> str:
    """Call chat completion for an agent planning or summary step."""
    metadata = {
        "purpose": purpose,
        "agent_run_id": str(agent_run_id),
    }
    provider_name = completion_provider.provider_name
    try:
        result = completion_provider.complete(
            messages=messages,
            response_format=response_format,
        )
    except Exception as exc:
        logger.warning("agent_completion_failed", purpose=purpose, error=str(exc))
        usage_service.log_event(
            UsageEventInput(
                workspace_id=workspace_id,
                user_id=user_id,
                provider=provider_name,
                model="unknown",
                operation=UsageOperation.AGENT_STEP,
                latency_ms=None,
                status=UsageEventStatus.FAILED,
                metadata=metadata,
            )
        )
        raise AgentCompletionError("Agent completion failed") from exc

    usage_service.log_event(
        UsageEventInput(
            workspace_id=workspace_id,
            user_id=user_id,
            provider=provider_name,
            model=result.model,
            operation=UsageOperation.AGENT_STEP,
            prompt_tokens=result.prompt_tokens,
            completion_tokens=result.completion_tokens,
            latency_ms=result.latency_ms,
            status=UsageEventStatus.SUCCESS,
            metadata=metadata,
        )
    )
    return result.content


def parse_json_content(raw_content: str) -> dict[str, Any]:
    """Parse JSON object content from LLM responses."""
    try:
        payload = json.loads(raw_content)
    except json.JSONDecodeError as exc:
        raise AgentCompletionError("Agent returned malformed JSON") from exc
    if not isinstance(payload, dict):
        raise AgentCompletionError("Agent JSON payload must be an object")
    return payload
