"""Usage event persistence."""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.infrastructure.db.enums import UsageEventStatus, UsageOperation
from app.modules.usage.models import UsageEvent


@dataclass(frozen=True)
class UsageTotalsRow:
    """Aggregated usage totals for a filter window."""

    prompt_tokens: int
    completion_tokens: int
    embedding_tokens: int
    estimated_cost_usd: Decimal
    call_count: int


@dataclass(frozen=True)
class UsageByDayRow:
    """Daily usage aggregate (UTC date)."""

    day: date
    prompt_tokens: int
    completion_tokens: int
    embedding_tokens: int
    estimated_cost_usd: Decimal
    call_count: int


@dataclass(frozen=True)
class UsageByOperationRow:
    """Per-operation usage aggregate."""

    operation: str
    prompt_tokens: int
    completion_tokens: int
    embedding_tokens: int
    estimated_cost_usd: Decimal
    call_count: int


class UsageRepository:
    """Append-only usage event persistence."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create(
        self,
        *,
        workspace_id: UUID,
        user_id: UUID | None,
        provider: str,
        model: str,
        operation: UsageOperation,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        embedding_tokens: int = 0,
        estimated_cost_usd: Decimal | None = None,
        latency_ms: int | None = None,
        status: UsageEventStatus,
        metadata: dict[str, Any] | None = None,
    ) -> UsageEvent:
        """Persist a usage event."""
        usage_event = UsageEvent(
            workspace_id=workspace_id,
            user_id=user_id,
            provider=provider,
            model=model,
            operation=operation,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            embedding_tokens=embedding_tokens,
            estimated_cost_usd=estimated_cost_usd,
            latency_ms=latency_ms,
            status=status,
            metadata_=metadata,
        )
        self._session.add(usage_event)
        self._session.flush()
        return usage_event

    def sum_embedding_tokens_for_job(
        self,
        *,
        workspace_id: UUID,
        job_id: UUID,
    ) -> int:
        """Sum embedding tokens for document-ingestion batches linked to a job."""
        total = self._session.scalar(
            select(func.coalesce(func.sum(UsageEvent.embedding_tokens), 0)).where(
                UsageEvent.workspace_id == workspace_id,
                UsageEvent.operation.in_(
                    [
                        UsageOperation.EMBEDDING_DOCUMENT,
                        UsageOperation.EMBEDDING,
                    ]
                ),
                UsageEvent.metadata_["job_id"].astext == str(job_id),
            )
        )
        return int(total or 0)

    def aggregate_workspace_usage(
        self,
        *,
        workspace_id: UUID,
        start: datetime,
        end: datetime,
    ) -> tuple[UsageTotalsRow, list[UsageByDayRow], list[UsageByOperationRow]]:
        """Aggregate usage_events for a workspace in ``[start, end)`` (UTC)."""
        window = (
            UsageEvent.workspace_id == workspace_id,
            UsageEvent.created_at >= start,
            UsageEvent.created_at < end,
        )

        totals_row = self._session.execute(
            select(
                func.coalesce(func.sum(UsageEvent.prompt_tokens), 0),
                func.coalesce(func.sum(UsageEvent.completion_tokens), 0),
                func.coalesce(func.sum(UsageEvent.embedding_tokens), 0),
                func.coalesce(func.sum(UsageEvent.estimated_cost_usd), 0),
                func.count(UsageEvent.id),
            ).where(*window)
        ).one()

        totals = UsageTotalsRow(
            prompt_tokens=int(totals_row[0] or 0),
            completion_tokens=int(totals_row[1] or 0),
            embedding_tokens=int(totals_row[2] or 0),
            estimated_cost_usd=Decimal(str(totals_row[3] or 0)),
            call_count=int(totals_row[4] or 0),
        )

        day_expr = func.date_trunc("day", UsageEvent.created_at)
        day_rows = self._session.execute(
            select(
                day_expr,
                func.coalesce(func.sum(UsageEvent.prompt_tokens), 0),
                func.coalesce(func.sum(UsageEvent.completion_tokens), 0),
                func.coalesce(func.sum(UsageEvent.embedding_tokens), 0),
                func.coalesce(func.sum(UsageEvent.estimated_cost_usd), 0),
                func.count(UsageEvent.id),
            )
            .where(*window)
            .group_by(day_expr)
            .order_by(day_expr.asc())
        ).all()

        by_day = [
            UsageByDayRow(
                day=_as_utc_date(row[0]),
                prompt_tokens=int(row[1] or 0),
                completion_tokens=int(row[2] or 0),
                embedding_tokens=int(row[3] or 0),
                estimated_cost_usd=Decimal(str(row[4] or 0)),
                call_count=int(row[5] or 0),
            )
            for row in day_rows
        ]

        op_rows = self._session.execute(
            select(
                UsageEvent.operation,
                func.coalesce(func.sum(UsageEvent.prompt_tokens), 0),
                func.coalesce(func.sum(UsageEvent.completion_tokens), 0),
                func.coalesce(func.sum(UsageEvent.embedding_tokens), 0),
                func.coalesce(func.sum(UsageEvent.estimated_cost_usd), 0),
                func.count(UsageEvent.id),
            )
            .where(*window)
            .group_by(UsageEvent.operation)
            .order_by(UsageEvent.operation.asc())
        ).all()

        by_operation = [
            UsageByOperationRow(
                operation=(
                    row[0].value if isinstance(row[0], UsageOperation) else str(row[0])
                ),
                prompt_tokens=int(row[1] or 0),
                completion_tokens=int(row[2] or 0),
                embedding_tokens=int(row[3] or 0),
                estimated_cost_usd=Decimal(str(row[4] or 0)),
                call_count=int(row[5] or 0),
            )
            for row in op_rows
        ]

        return totals, by_day, by_operation


def _as_utc_date(value: datetime | date) -> date:
    """Normalize date_trunc results to a calendar date."""
    if isinstance(value, datetime):
        return value.date()
    return value
