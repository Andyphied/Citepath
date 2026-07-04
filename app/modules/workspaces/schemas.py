"""Workspace request and response schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class CreateWorkspaceRequest(BaseModel):
    """Create workspace payload."""

    name: str = Field(min_length=1, max_length=255)
    slug: str | None = Field(default=None, max_length=128)

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("name must not be blank")
        return stripped

    @field_validator("slug")
    @classmethod
    def normalize_slug(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip().lower()
        if not stripped:
            return None
        return stripped


class WorkspaceResponse(BaseModel):
    """Public workspace fields returned after creation."""

    id: UUID
    name: str
    slug: str
    created_at: datetime

    model_config = {"from_attributes": True}
