"""Usage event persistence."""

from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.infrastructure.db.enums import UsageEventStatus, UsageOperation
from app.modules.usage.models import UsageEvent


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
