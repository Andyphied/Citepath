"""Admin aggregation routes (Owner/Admin only)."""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query

from app.api.deps import RequireViewAdminDashboardDep, UsageServiceDep
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
