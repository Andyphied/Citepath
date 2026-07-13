"""Ingestion-related HTTP exception handlers."""

from fastapi import Request, status

from app.modules.ingestion.exceptions import IngestionJobNotFoundError
from app.modules.observability.errors import error_response


async def ingestion_job_not_found_handler(
    request: Request,
    _exc: IngestionJobNotFoundError,
):
    """Return 404 when an ingestion job is missing or not in the workspace."""
    return error_response(
        request=request,
        status_code=status.HTTP_404_NOT_FOUND,
        code="not_found",
        message="Ingestion job not found",
    )
