"""Document API schemas."""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.infrastructure.db.enums import DocumentStatus
from app.modules.ingestion.schemas import IngestionJobResponse

if TYPE_CHECKING:
    from app.modules.documents.models import Document


class DocumentResponse(BaseModel):
    """Uploaded document metadata returned to clients."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    workspace_id: UUID
    title: str
    source_type: str | None
    file_type: str
    status: str
    status_label: str
    uploaded_by: UUID
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_document(cls, document: "Document") -> "DocumentResponse":
        """Build a response with machine status and human-readable label."""
        status = (
            document.status
            if isinstance(document.status, DocumentStatus)
            else DocumentStatus(document.status)
        )
        return cls(
            id=document.id,
            workspace_id=document.workspace_id,
            title=document.title,
            source_type=document.source_type,
            file_type=document.file_type,
            status=status.value,
            status_label=status.label,
            uploaded_by=document.uploaded_by,
            created_at=document.created_at,
            updated_at=document.updated_at,
        )


class DocumentUploadResponse(BaseModel):
    """Upload response including document metadata and ingestion job."""

    document: DocumentResponse
    ingestion_job: IngestionJobResponse


class DocumentReindexResponse(BaseModel):
    """Re-index response including updated document metadata and new ingestion job."""

    document: DocumentResponse
    ingestion_job: IngestionJobResponse


class DocumentListResponse(BaseModel):
    """Paginated workspace document list."""

    items: list[DocumentResponse]
    total: int
    page: int
    page_size: int


class DocumentDetailResponse(BaseModel):
    """Document metadata with ingestion context."""

    document: DocumentResponse
    latest_job: IngestionJobResponse | None = None
    chunk_count: int | None = None
    error_message: str | None = None
