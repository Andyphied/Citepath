"""Audit log persistence."""

from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.modules.audit.models import AuditLog


class AuditRepository:
    """Append-only audit event persistence."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create(
        self,
        *,
        workspace_id: UUID,
        actor_user_id: UUID | None,
        event_type: str,
        metadata: dict[str, Any] | None = None,
        ip_address: str | None = None,
    ) -> AuditLog:
        """Persist a new audit log entry."""
        audit_log = AuditLog(
            workspace_id=workspace_id,
            actor_user_id=actor_user_id,
            event_type=event_type,
            metadata_=metadata,
            ip_address=ip_address,
        )
        self._session.add(audit_log)
        self._session.flush()
        return audit_log
