"""Ingestion job persistence with workspace scoping."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.infrastructure.db.enums import IngestionJobStatus
from app.infrastructure.db.scoped_repository import WorkspaceScopedRepository
from app.modules.documents.models import Document
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

    def delete_for_document(
        self,
        *,
        workspace_id: UUID,
        document_id: UUID,
    ) -> None:
        """Delete all ingestion jobs for a document in the workspace."""
        delete_stmt = delete(IngestionJob).where(
            IngestionJob.workspace_id == workspace_id,
            IngestionJob.document_id == document_id,
        )
        self._session.execute(delete_stmt)
        self._session.commit()

    def get_latest_for_document(
        self,
        *,
        workspace_id: UUID,
        document_id: UUID,
    ) -> IngestionJob | None:
        """Return the most recent ingestion job for a document in the workspace."""
        stmt = (
            select(IngestionJob)
            .where(IngestionJob.document_id == document_id)
            .order_by(IngestionJob.created_at.desc())
            .limit(1)
        )
        stmt = self._scoped_filter(stmt, workspace_id)
        return self._session.scalar(stmt)

    def list_for_workspace_paginated(
        self,
        *,
        workspace_id: UUID,
        page: int,
        page_size: int,
        status: IngestionJobStatus | None = None,
    ) -> tuple[list[tuple[IngestionJob, str | None]], int]:
        """Return paginated jobs with document titles for a workspace."""
        conditions = [IngestionJob.workspace_id == workspace_id]
        if status is not None:
            conditions.append(IngestionJob.status == status)

        total = self._session.scalar(
            select(func.count()).select_from(IngestionJob).where(*conditions)
        )
        total = int(total or 0)

        offset = (page - 1) * page_size
        stmt = (
            select(IngestionJob, Document.title)
            .outerjoin(Document, Document.id == IngestionJob.document_id)
            .where(*conditions)
            .order_by(IngestionJob.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        rows = list(self._session.execute(stmt).all())
        return [(job, title) for job, title in rows], total

    def count_failed_since(
        self,
        *,
        workspace_id: UUID,
        since: datetime,
    ) -> int:
        """Count failed ingestion jobs created at or after ``since``."""
        total = self._session.scalar(
            select(func.count())
            .select_from(IngestionJob)
            .where(
                IngestionJob.workspace_id == workspace_id,
                IngestionJob.status == IngestionJobStatus.FAILED,
                IngestionJob.created_at >= since,
            )
        )
        return int(total or 0)

    def count_by_status(
        self,
        *,
        workspace_id: UUID,
        status: IngestionJobStatus,
    ) -> int:
        """Count ingestion jobs in a workspace with the given status."""
        total = self._session.scalar(
            select(func.count())
            .select_from(IngestionJob)
            .where(
                IngestionJob.workspace_id == workspace_id,
                IngestionJob.status == status,
            )
        )
        return int(total or 0)

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
