"""Usage tracking service."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

import structlog
from sqlalchemy.orm import Session

from app.infrastructure.db.enums import UsageEventStatus, UsageOperation
from app.modules.observability.metrics import observe_llm_call
from app.modules.usage.cost_calculator import estimate_cost_usd
from app.modules.usage.exceptions import InvalidUsageRangeError
from app.modules.usage.repository import UsageRepository
from app.modules.usage.schemas import (
    UsageByDayResponse,
    UsageByOperationResponse,
    UsageTotalsResponse,
    WorkspaceUsageSummaryResponse,
)

logger = structlog.get_logger(__name__)

DEFAULT_USAGE_SUMMARY_DAYS = 7


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
        """Persist a usage event; failures are logged and swallowed.

        Uses a savepoint so a failed usage write does not roll back the
        caller's in-flight transaction (agent runs, RAG persistence, etc.).
        """
        observe_llm_call(
            operation=event.operation.value,
            status=event.status.value,
        )
        try:
            estimated_cost = estimate_cost_usd(
                provider=event.provider,
                model=event.model,
                prompt_tokens=event.prompt_tokens,
                completion_tokens=event.completion_tokens,
                embedding_tokens=event.embedding_tokens,
            )
            with self._session.begin_nested():
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

    def get_workspace_summary(
        self,
        *,
        workspace_id: UUID,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> WorkspaceUsageSummaryResponse:
        """Aggregate usage for a workspace; default window is the last 7 days."""
        resolved_end = _as_utc(end) if end is not None else datetime.now(UTC)
        resolved_start = (
            _as_utc(start)
            if start is not None
            else resolved_end - timedelta(days=DEFAULT_USAGE_SUMMARY_DAYS)
        )
        if resolved_start >= resolved_end:
            raise InvalidUsageRangeError()

        totals, by_day, by_operation = self._repository.aggregate_workspace_usage(
            workspace_id=workspace_id,
            start=resolved_start,
            end=resolved_end,
        )

        return WorkspaceUsageSummaryResponse(
            workspace_id=workspace_id,
            from_=resolved_start,
            to=resolved_end,
            totals=UsageTotalsResponse(
                prompt_tokens=totals.prompt_tokens,
                completion_tokens=totals.completion_tokens,
                embedding_tokens=totals.embedding_tokens,
                estimated_cost_usd=totals.estimated_cost_usd,
                call_count=totals.call_count,
            ),
            by_day=[
                UsageByDayResponse(
                    date=row.day,
                    prompt_tokens=row.prompt_tokens,
                    completion_tokens=row.completion_tokens,
                    embedding_tokens=row.embedding_tokens,
                    estimated_cost_usd=row.estimated_cost_usd,
                    call_count=row.call_count,
                )
                for row in by_day
            ],
            by_operation=[
                UsageByOperationResponse(
                    operation=row.operation,
                    prompt_tokens=row.prompt_tokens,
                    completion_tokens=row.completion_tokens,
                    embedding_tokens=row.embedding_tokens,
                    estimated_cost_usd=row.estimated_cost_usd,
                    call_count=row.call_count,
                )
                for row in by_operation
            ],
        )


def _as_utc(value: datetime) -> datetime:
    """Normalize naive datetimes to UTC-aware."""
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
