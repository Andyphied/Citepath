"""Ingestion API schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class IngestionJobResponse(BaseModel):
    """Ingestion job metadata returned to clients."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    workspace_id: UUID
    document_id: UUID
    status: str
    attempt_count: int
    error_message: str | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
