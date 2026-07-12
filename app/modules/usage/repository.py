"""Usage event persistence."""

from decimal import Decimal
from typing import Any
from uuid import UUID

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
