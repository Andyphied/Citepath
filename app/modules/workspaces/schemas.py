"""Workspace request and response schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator


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


class WorkspaceListItemResponse(BaseModel):
    """Workspace summary for the authenticated user's membership list."""

    id: UUID
    name: str
    role: str
    created_at: datetime


class WorkspaceListResponse(BaseModel):
    """Paginated-style list wrapper for user workspaces."""

    items: list[WorkspaceListItemResponse]


class WorkspaceDetailResponse(BaseModel):
    """Workspace detail for members."""

    id: UUID
    name: str
    member_count: int
    created_at: datetime


class InviteMemberRequest(BaseModel):
    """Invite an existing user to a workspace by email."""

    email: EmailStr
    role: str = Field(
        description="Workspace role: owner, admin, member, or viewer"
    )

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().lower()

    @field_validator("role")
    @classmethod
    def normalize_role(cls, value: str) -> str:
        normalized = value.strip().lower()
        allowed = {"owner", "admin", "member", "viewer"}
        if normalized not in allowed:
            raise ValueError(
                "role must be one of: owner, admin, member, viewer"
            )
        return normalized


class WorkspaceMemberResponse(BaseModel):
    """Workspace member returned after invite."""

    user_id: UUID
    email: str
    role: str
    created_at: datetime
