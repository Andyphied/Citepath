"""Admin aggregation routes (Owner/Admin only)."""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query

from app.api.deps import (
    AuditServiceDep,
    RequireViewAdminDashboardDep,
    UsageServiceDep,
)
from app.modules.audit.schemas import AuditLogListResponse
from app.modules.usage.schemas import WorkspaceUsageSummaryResponse

router = APIRouter(prefix="/workspaces", tags=["admin"])


@router.get(
    "/{workspace_id}/admin/usage",
    response_model=WorkspaceUsageSummaryResponse,
    response_model_by_alias=True,
)
def get_workspace_usage_summary(
    workspace_id: UUID,
    workspace_context: RequireViewAdminDashboardDep,
    usage_service: UsageServiceDep,
    from_: Annotated[
        datetime | None,
        Query(
            alias="from",
            description="Inclusive range start (ISO-8601). Default: 7 days before 'to'.",
        ),
    ] = None,
    to: Annotated[
        datetime | None,
        Query(
            description="Exclusive range end (ISO-8601). Default: now (UTC).",
        ),
    ] = None,
) -> WorkspaceUsageSummaryResponse:
    """Return token/cost aggregates for the workspace (Owner/Admin only)."""
    _ = workspace_id
    return usage_service.get_workspace_summary(
        workspace_id=workspace_context.workspace_id,
        start=from_,
        end=to,
    )


@router.get(
    "/{workspace_id}/admin/audit-logs",
    response_model=AuditLogListResponse,
)
def list_workspace_audit_logs(
    workspace_id: UUID,
    workspace_context: RequireViewAdminDashboardDep,
    audit_service: AuditServiceDep,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    event_type: Annotated[
        str | None,
        Query(description="Filter by exact event_type (e.g. document.uploaded)."),
    ] = None,
    actor_user_id: Annotated[
        UUID | None,
        Query(description="Filter by actor user id."),
    ] = None,
    from_: Annotated[
        datetime | None,
        Query(
            alias="from",
            description="Inclusive created_at lower bound (ISO-8601).",
        ),
    ] = None,
    to: Annotated[
        datetime | None,
        Query(
            description="Exclusive created_at upper bound (ISO-8601).",
        ),
    ] = None,
) -> AuditLogListResponse:
    """Return paginated audit logs for the workspace (Owner/Admin only)."""
    _ = workspace_id
    return audit_service.list_logs(
        workspace_id=workspace_context.workspace_id,
        page=page,
        page_size=page_size,
        event_type=event_type,
        actor_user_id=actor_user_id,
        start=from_,
        end=to,
    )
