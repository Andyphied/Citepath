"""Admin dashboard API schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class DocumentStatusCounts(BaseModel):
    """Document counts keyed by lifecycle status."""

    uploaded: int = 0
    processing: int = 0
    indexed: int = 0
    failed: int = 0


class RecentDocumentUpload(BaseModel):
    """Recent document upload summary for admin overview."""

    id: UUID
    title: str | None
    status: str
    status_label: str
    uploaded_by: UUID | None
    created_at: datetime


class DocumentsOverviewResponse(BaseModel):
    """Workspace document health overview (ADMIN-001)."""

    workspace_id: UUID
    total: int
    by_status: DocumentStatusCounts
    recent_uploads: list[RecentDocumentUpload]


class AdminIngestionJobItem(BaseModel):
    """Ingestion job row with document title for admin lists."""

    id: UUID
    workspace_id: UUID
    document_id: UUID
    document_title: str | None
    status: str
    attempt_count: int
    error_message: str | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime


class AdminIngestionJobListResponse(BaseModel):
    """Paginated ingestion jobs for admin (ADMIN-002 / OBS-007)."""

    items: list[AdminIngestionJobItem]
    total: int
    page: int
    page_size: int
    pending_count: int = Field(
        description="Workspace count of ingestion jobs currently pending (OBS-007).",
    )


class RecentQuestionItem(BaseModel):
    """Recent user question preview (ADMIN-003)."""

    message_id: UUID
    conversation_id: UUID
    user_id: UUID
    user_name: str | None
    user_email: str
    question_preview: str
    created_at: datetime


class RecentQuestionsResponse(BaseModel):
    """Paginated recent questions for admin (ADMIN-003)."""

    items: list[RecentQuestionItem]
    total: int
    page: int
    page_size: int


class FailedJobsWidgetResponse(BaseModel):
    """Failed ingestion jobs widget for admin dashboard (ADMIN-005)."""

    failed_last_24h: int
    failed_last_7d: int
    items: list[AdminIngestionJobItem] = Field(
        description="Recent failed jobs (same shape as ingestion-jobs list)."
    )
    empty_message: str | None = Field(
        default=None,
        description='Present when there are no failed jobs: "No failed jobs."',
    )
