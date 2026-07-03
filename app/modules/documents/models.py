"""Document domain models."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.db.base import Base
from app.infrastructure.db.enums import DocumentStatus, document_status_enum


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id"),
        nullable=False,
    )
    uploaded_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
    )
    title: Mapped[str | None] = mapped_column(String(512), nullable=True)
    source_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    file_type: Mapped[str | None] = mapped_column(String(16), nullable=True)
    storage_key: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    status: Mapped[DocumentStatus] = mapped_column(document_status_enum, nullable=False)
    metadata_: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata",
        JSONB,
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    __table_args__ = (
        Index("ix_documents_workspace_id_created_at", "workspace_id", created_at.desc()),
        Index("ix_documents_workspace_id_status", "workspace_id", "status"),
    )
