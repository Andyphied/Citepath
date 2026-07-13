"""Document API schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.modules.ingestion.schemas import IngestionJobResponse


class DocumentResponse(BaseModel):
    """Uploaded document metadata returned to clients."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    workspace_id: UUID
    title: str
    source_type: str | None
    file_type: str
    status: str
    uploaded_by: UUID
    created_at: datetime
    updated_at: datetime


class DocumentUploadResponse(BaseModel):
    """Upload response including document metadata and ingestion job."""

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
