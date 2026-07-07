"""Document API schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


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
