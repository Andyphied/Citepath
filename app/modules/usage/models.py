"""Usage tracking domain models."""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, Integer, Numeric, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.db.base import Base
from app.infrastructure.db.enums import (
    UsageEventStatus,
    UsageOperation,
    usage_event_status_enum,
    usage_operation_enum,
)


class UsageEvent(Base):
    __tablename__ = "usage_events"

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
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
    )
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    model: Mapped[str] = mapped_column(String(128), nullable=False)
    operation: Mapped[UsageOperation] = mapped_column(usage_operation_enum, nullable=False)
    prompt_tokens: Mapped[int] = mapped_column(Integer, server_default="0", nullable=False)
    completion_tokens: Mapped[int] = mapped_column(Integer, server_default="0", nullable=False)
    embedding_tokens: Mapped[int] = mapped_column(Integer, server_default="0", nullable=False)
    estimated_cost_usd: Mapped[Decimal | None] = mapped_column(Numeric(10, 6), nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[UsageEventStatus] = mapped_column(usage_event_status_enum, nullable=False)
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

    __table_args__ = (
        Index("ix_usage_events_workspace_id_created_at", "workspace_id", created_at.desc()),
        Index(
            "ix_usage_events_workspace_id_operation_created_at",
            "workspace_id",
            "operation",
            created_at.desc(),
        ),
    )
