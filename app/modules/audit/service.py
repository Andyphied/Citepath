"""Audit log query service."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.modules.audit.exceptions import InvalidAuditRangeError
from app.modules.audit.repository import AuditRepository
from app.modules.audit.schemas import AuditLogListResponse, AuditLogResponse


class AuditService:
    """Read-side audit log queries for admin surfaces."""

    def __init__(self, session: Session) -> None:
        self._repository = AuditRepository(session)

    def list_logs(
        self,
        *,
        workspace_id: UUID,
        page: int,
        page_size: int,
        event_type: str | None = None,
        actor_user_id: UUID | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> AuditLogListResponse:
        """List workspace audit logs newest-first with optional filters."""
        resolved_start = _as_utc(start) if start is not None else None
        resolved_end = _as_utc(end) if end is not None else None
        if (
            resolved_start is not None
            and resolved_end is not None
            and resolved_start >= resolved_end
        ):
            raise InvalidAuditRangeError()

        items, total = self._repository.list_for_workspace(
            workspace_id=workspace_id,
            page=page,
            page_size=page_size,
            event_type=event_type,
            actor_user_id=actor_user_id,
            start=resolved_start,
            end=resolved_end,
        )
        return AuditLogListResponse(
            items=[AuditLogResponse.from_audit_log(row) for row in items],
            total=total,
            page=page,
            page_size=page_size,
        )


def _as_utc(value: datetime) -> datetime:
    """Normalize naive datetimes to UTC-aware."""
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
