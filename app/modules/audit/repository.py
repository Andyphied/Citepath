"""Audit log persistence."""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
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
        """Persist a new audit log entry and commit."""
        audit_log = AuditLog(
            workspace_id=workspace_id,
            actor_user_id=actor_user_id,
            event_type=event_type,
            metadata_=metadata,
            ip_address=ip_address,
        )
        self._session.add(audit_log)
        self._session.commit()
        self._session.refresh(audit_log)
        return audit_log

    def list_for_workspace(
        self,
        *,
        workspace_id: UUID,
        page: int,
        page_size: int,
        event_type: str | None = None,
        actor_user_id: UUID | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> tuple[list[AuditLog], int]:
        """Return paginated audit logs for a workspace (newest first)."""
        conditions = [AuditLog.workspace_id == workspace_id]
        if event_type is not None:
            conditions.append(AuditLog.event_type == event_type)
        if actor_user_id is not None:
            conditions.append(AuditLog.actor_user_id == actor_user_id)
        if start is not None:
            conditions.append(AuditLog.created_at >= start)
        if end is not None:
            conditions.append(AuditLog.created_at < end)

        total = self._session.scalar(
            select(func.count()).select_from(AuditLog).where(*conditions)
        )
        total = int(total or 0)

        offset = (page - 1) * page_size
        stmt = (
            select(AuditLog)
            .where(*conditions)
            .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
            .offset(offset)
            .limit(page_size)
        )
        items = list(self._session.scalars(stmt).all())
        return items, total
