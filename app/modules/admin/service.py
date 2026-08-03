"""Admin dashboard aggregation service (read-only)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy.orm import Session

from app.infrastructure.db.enums import DocumentStatus, IngestionJobStatus
from app.modules.admin.schemas import (
    AdminIngestionJobItem,
    AdminIngestionJobListResponse,
    DocumentsOverviewResponse,
    DocumentStatusCounts,
    FailedJobsWidgetResponse,
    RecentDocumentUpload,
    RecentQuestionItem,
    RecentQuestionsResponse,
)
from app.modules.documents.repository import DocumentRepository
from app.modules.documents.sanitization import sanitize_ingestion_error_message
from app.modules.ingestion.job_repository import IngestionJobRepository
from app.modules.ingestion.models import IngestionJob
from app.modules.rag.repository import RAGRepository

_QUESTION_PREVIEW_MAX_LEN = 200
_DEFAULT_RECENT_UPLOADS = 10
_DEFAULT_FAILED_WIDGET_ITEMS = 10
_EMPTY_FAILED_MESSAGE = "No failed jobs."


class AdminService:
    """Compose workspace-scoped admin aggregates from domain repositories."""

    def __init__(self, session: Session) -> None:
        self._documents = DocumentRepository(session)
        self._ingestion_jobs = IngestionJobRepository(session)
        self._rag = RAGRepository(session)

    def get_documents_overview(
        self,
        *,
        workspace_id: UUID,
        recent_limit: int = _DEFAULT_RECENT_UPLOADS,
    ) -> DocumentsOverviewResponse:
        """Return document totals, counts by status, and recent uploads."""
        counts = self._documents.count_by_status_for_workspace(
            workspace_id=workspace_id
        )
        total = sum(counts.values())
        recent, _ = self._documents.list_for_workspace_paginated(
            workspace_id=workspace_id,
            page=1,
            page_size=recent_limit,
        )
        return DocumentsOverviewResponse(
            workspace_id=workspace_id,
            total=total,
            by_status=DocumentStatusCounts(
                uploaded=counts[DocumentStatus.UPLOADED],
                processing=counts[DocumentStatus.PROCESSING],
                indexed=counts[DocumentStatus.INDEXED],
                failed=counts[DocumentStatus.FAILED],
            ),
            recent_uploads=[
                RecentDocumentUpload(
                    id=doc.id,
                    title=doc.title,
                    status=(
                        doc.status.value
                        if isinstance(doc.status, DocumentStatus)
                        else str(doc.status)
                    ),
                    status_label=(
                        doc.status.label
                        if isinstance(doc.status, DocumentStatus)
                        else DocumentStatus(doc.status).label
                    ),
                    uploaded_by=doc.uploaded_by,
                    created_at=doc.created_at,
                )
                for doc in recent
            ],
        )

    def list_ingestion_jobs(
        self,
        *,
        workspace_id: UUID,
        page: int,
        page_size: int,
        status: IngestionJobStatus | None = None,
    ) -> AdminIngestionJobListResponse:
        """List ingestion jobs with document titles, newest first."""
        rows, total = self._ingestion_jobs.list_for_workspace_paginated(
            workspace_id=workspace_id,
            page=page,
            page_size=page_size,
            status=status,
        )
        pending_count = self._ingestion_jobs.count_by_status(
            workspace_id=workspace_id,
            status=IngestionJobStatus.PENDING,
        )
        return AdminIngestionJobListResponse(
            items=[
                _job_item(job=job, document_title=title) for job, title in rows
            ],
            total=total,
            page=page,
            page_size=page_size,
            pending_count=pending_count,
        )

    def list_recent_questions(
        self,
        *,
        workspace_id: UUID,
        page: int,
        page_size: int,
    ) -> RecentQuestionsResponse:
        """List recent user questions with identity and truncated preview."""
        rows, total = self._rag.list_recent_user_questions_paginated(
            workspace_id=workspace_id,
            page=page,
            page_size=page_size,
        )
        items = [
            RecentQuestionItem(
                message_id=message.id,
                conversation_id=conversation.id,
                user_id=conversation.user_id,
                user_name=user_name,
                user_email=user_email,
                question_preview=_preview(message.content),
                created_at=message.created_at,
            )
            for message, conversation, user_name, user_email in rows
        ]
        return RecentQuestionsResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
        )

    def get_failed_jobs_widget(
        self,
        *,
        workspace_id: UUID,
        item_limit: int = _DEFAULT_FAILED_WIDGET_ITEMS,
    ) -> FailedJobsWidgetResponse:
        """Return failed-job counts (24h/7d) and a short recent failed list."""
        now = datetime.now(UTC)
        failed_last_24h = self._ingestion_jobs.count_failed_since(
            workspace_id=workspace_id,
            since=now - timedelta(hours=24),
        )
        failed_last_7d = self._ingestion_jobs.count_failed_since(
            workspace_id=workspace_id,
            since=now - timedelta(days=7),
        )
        rows, _ = self._ingestion_jobs.list_for_workspace_paginated(
            workspace_id=workspace_id,
            page=1,
            page_size=item_limit,
            status=IngestionJobStatus.FAILED,
        )
        items = [_job_item(job=job, document_title=title) for job, title in rows]
        empty_message = _EMPTY_FAILED_MESSAGE if failed_last_7d == 0 else None
        return FailedJobsWidgetResponse(
            failed_last_24h=failed_last_24h,
            failed_last_7d=failed_last_7d,
            items=items,
            empty_message=empty_message,
        )


def _job_item(*, job: IngestionJob, document_title: str | None) -> AdminIngestionJobItem:
    status = (
        job.status.value
        if isinstance(job.status, IngestionJobStatus)
        else str(job.status)
    )
    return AdminIngestionJobItem(
        id=job.id,
        workspace_id=job.workspace_id,
        document_id=job.document_id,
        document_title=document_title,
        status=status,
        attempt_count=job.attempt_count,
        error_message=sanitize_ingestion_error_message(job.error_message),
        started_at=job.started_at,
        completed_at=job.completed_at,
        created_at=job.created_at,
    )


def _preview(content: str) -> str:
    text = content.strip()
    if len(text) <= _QUESTION_PREVIEW_MAX_LEN:
        return text
    return text[:_QUESTION_PREVIEW_MAX_LEN].rstrip() + "…"
