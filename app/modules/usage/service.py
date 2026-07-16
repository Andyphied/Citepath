"""Usage tracking service."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

import structlog
from sqlalchemy.orm import Session

from app.infrastructure.db.enums import UsageEventStatus, UsageOperation
from app.modules.usage.cost_calculator import estimate_cost_usd
from app.modules.usage.repository import UsageRepository

logger = structlog.get_logger(__name__)


@dataclass(frozen=True)
class UsageEventInput:
    """Input for recording a provider usage event."""

    workspace_id: UUID
    user_id: UUID | None
    provider: str
    model: str
    operation: UsageOperation
    prompt_tokens: int = 0
    completion_tokens: int = 0
    embedding_tokens: int = 0
    latency_ms: int | None = None
    status: UsageEventStatus = UsageEventStatus.SUCCESS
    metadata: dict[str, Any] | None = None


class UsageService:
    """Record and query AI provider usage events."""

    def __init__(self, session: Session) -> None:
        self._session = session
        self._repository = UsageRepository(session)

    def log_event(self, event: UsageEventInput) -> None:
        """Persist a usage event; failures are logged and swallowed."""
        try:
            estimated_cost = estimate_cost_usd(
                provider=event.provider,
                model=event.model,
                prompt_tokens=event.prompt_tokens,
                completion_tokens=event.completion_tokens,
                embedding_tokens=event.embedding_tokens,
            )
            self._repository.create(
                workspace_id=event.workspace_id,
                user_id=event.user_id,
                provider=event.provider,
                model=event.model,
                operation=event.operation,
                prompt_tokens=event.prompt_tokens,
                completion_tokens=event.completion_tokens,
                embedding_tokens=event.embedding_tokens,
                estimated_cost_usd=estimated_cost,
                latency_ms=event.latency_ms,
                status=event.status,
                metadata=event.metadata,
            )
        except Exception:
            self._session.rollback()
            logger.exception(
                "usage_event_log_failed",
                workspace_id=str(event.workspace_id),
                operation=event.operation.value,
                provider=event.provider,
                model=event.model,
            )

    def sum_embedding_tokens_for_job(
        self,
        *,
        workspace_id: UUID,
        job_id: UUID,
    ) -> int:
        """Return aggregate embedding tokens logged for an ingestion job."""
        return self._repository.sum_embedding_tokens_for_job(
            workspace_id=workspace_id,
            job_id=job_id,
        )
