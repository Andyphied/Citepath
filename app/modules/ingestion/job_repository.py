"""Ingestion job persistence with workspace scoping."""

from datetime import datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.infrastructure.db.enums import IngestionJobStatus
from app.infrastructure.db.scoped_repository import WorkspaceScopedRepository
from app.modules.ingestion.models import IngestionJob


class IngestionJobRepository(WorkspaceScopedRepository[IngestionJob]):
    """Workspace-scoped ingestion job CRUD."""

    _model = IngestionJob

    def __init__(self, session: Session) -> None:
        super().__init__(session)

    def create(
        self,
        *,
        workspace_id: UUID,
        document_id: UUID,
        status: IngestionJobStatus = IngestionJobStatus.PENDING,
    ) -> IngestionJob:
        """Persist a pending ingestion job in the given workspace."""
        job = IngestionJob(
            workspace_id=workspace_id,
            document_id=document_id,
            status=status,
        )
        self._session.add(job)
        self._session.commit()
        self._session.refresh(job)
        return job

    def get_by_id(
        self,
        *,
        workspace_id: UUID,
        id: UUID,
    ) -> IngestionJob | None:
        """Return a job by id within the given workspace, or None."""
        return super().get_by_id(workspace_id=workspace_id, id=id)

    def update(
        self,
        *,
        job: IngestionJob,
        status: IngestionJobStatus | None = None,
        attempt_count: int | None = None,
        error_message: str | None = None,
        started_at: datetime | None = None,
        completed_at: datetime | None = None,
    ) -> IngestionJob:
        """Update mutable fields on an ingestion job and commit."""
        if status is not None:
            job.status = status
        if attempt_count is not None:
            job.attempt_count = attempt_count
        if error_message is not None:
            job.error_message = error_message
        if started_at is not None:
            job.started_at = started_at
        if completed_at is not None:
            job.completed_at = completed_at
        self._session.commit()
        self._session.refresh(job)
        return job
