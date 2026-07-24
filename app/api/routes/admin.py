"""Admin aggregation routes (Owner/Admin only)."""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query

from app.api.deps import (
    AdminServiceDep,
    AuditServiceDep,
    RequireViewAdminDashboardDep,
    UsageServiceDep,
)
from app.infrastructure.db.enums import IngestionJobStatus
from app.modules.admin.schemas import (
    AdminIngestionJobListResponse,
    DocumentsOverviewResponse,
    FailedJobsWidgetResponse,
    RecentQuestionsResponse,
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
    "/{workspace_id}/admin/documents-overview",
    response_model=DocumentsOverviewResponse,
)
def get_documents_overview(
    workspace_id: UUID,
    workspace_context: RequireViewAdminDashboardDep,
    admin_service: AdminServiceDep,
) -> DocumentsOverviewResponse:
    """Return document totals, counts by status, and recent uploads."""
    _ = workspace_id
    return admin_service.get_documents_overview(
        workspace_id=workspace_context.workspace_id,
    )


@router.get(
    "/{workspace_id}/admin/ingestion-jobs",
    response_model=AdminIngestionJobListResponse,
)
def list_ingestion_jobs(
    workspace_id: UUID,
    workspace_context: RequireViewAdminDashboardDep,
    admin_service: AdminServiceDep,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    status: Annotated[
        IngestionJobStatus | None,
        Query(description="Filter by job status (pending/processing/completed/failed)."),
    ] = None,
) -> AdminIngestionJobListResponse:
    """List ingestion jobs with document titles (Owner/Admin only)."""
    _ = workspace_id
    return admin_service.list_ingestion_jobs(
        workspace_id=workspace_context.workspace_id,
        page=page,
        page_size=page_size,
        status=status,
    )


@router.get(
    "/{workspace_id}/admin/recent-questions",
    response_model=RecentQuestionsResponse,
)
def list_recent_questions(
    workspace_id: UUID,
    workspace_context: RequireViewAdminDashboardDep,
    admin_service: AdminServiceDep,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 50,
) -> RecentQuestionsResponse:
    """List recent user questions with previews (Owner/Admin only)."""
    _ = workspace_id
    return admin_service.list_recent_questions(
        workspace_id=workspace_context.workspace_id,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/{workspace_id}/admin/failed-jobs",
    response_model=FailedJobsWidgetResponse,
)
def get_failed_jobs_widget(
    workspace_id: UUID,
    workspace_context: RequireViewAdminDashboardDep,
    admin_service: AdminServiceDep,
) -> FailedJobsWidgetResponse:
    """Return failed-job counts (24h/7d) and recent failures for the dashboard."""
    _ = workspace_id
    return admin_service.get_failed_jobs_widget(
        workspace_id=workspace_context.workspace_id,
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
