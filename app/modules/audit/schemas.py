"""Audit log API schemas."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel

from app.modules.audit.models import AuditLog


class AuditLogResponse(BaseModel):
    """Single audit log entry."""

    id: UUID
    workspace_id: UUID
    actor_user_id: UUID | None
    event_type: str
    metadata: dict[str, Any] | None
    ip_address: str | None
    created_at: datetime

    @classmethod
    def from_audit_log(cls, audit_log: AuditLog) -> "AuditLogResponse":
        """Map ORM row to API response (metadata_ → metadata)."""
        return cls(
            id=audit_log.id,
            workspace_id=audit_log.workspace_id,
            actor_user_id=audit_log.actor_user_id,
            event_type=audit_log.event_type,
            metadata=audit_log.metadata_,
            ip_address=audit_log.ip_address,
            created_at=audit_log.created_at,
        )


class AuditLogListResponse(BaseModel):
    """Paginated audit log list."""

    items: list[AuditLogResponse]
    total: int
    page: int
    page_size: int
