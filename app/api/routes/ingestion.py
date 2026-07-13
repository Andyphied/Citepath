"""Ingestion job routes."""

from uuid import UUID

from fastapi import APIRouter

from app.api.deps import IngestionServiceDep, RequireViewDocumentsDep
from app.modules.ingestion.schemas import IngestionJobResponse

router = APIRouter(prefix="/workspaces", tags=["ingestion"])


@router.get(
    "/{workspace_id}/ingestion-jobs/{job_id}",
    response_model=IngestionJobResponse,
)
async def get_ingestion_job(
    job_id: UUID,
    workspace_context: RequireViewDocumentsDep,
    ingestion_service: IngestionServiceDep,
) -> IngestionJobResponse:
    """Return ingestion job status and metadata for a workspace document."""
    return ingestion_service.get_job(
        workspace_id=workspace_context.workspace_id,
        job_id=job_id,
    )
