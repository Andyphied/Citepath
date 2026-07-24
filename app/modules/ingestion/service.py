"""Ingestion domain service."""

from uuid import UUID

from app.modules.documents.sanitization import sanitize_ingestion_error_message
from app.modules.ingestion.exceptions import IngestionJobNotFoundError
from app.modules.ingestion.job_repository import IngestionJobRepository
from app.modules.ingestion.schemas import IngestionJobResponse
from app.modules.observability.metrics import observe_ingestion_job


class IngestionService:
    """Ingestion job lifecycle orchestration."""

    def __init__(self, job_repository: IngestionJobRepository) -> None:
        self._job_repository = job_repository

    def create_job_for_document(
        self,
        *,
        workspace_id: UUID,
        document_id: UUID,
    ) -> IngestionJobResponse:
        """Create a pending ingestion job and enqueue background processing."""
        job = self._job_repository.create(
            workspace_id=workspace_id,
            document_id=document_id,
        )
        observe_ingestion_job(status=job.status.value)

        # Import here to avoid circular imports between service and tasks.
        from app.modules.ingestion.tasks import process_ingestion_job

        process_ingestion_job.delay(
            str(job.id),
            str(workspace_id),
            str(document_id),
        )
        return IngestionJobResponse.model_validate(job)

    def get_job(
        self,
        *,
        workspace_id: UUID,
        job_id: UUID,
    ) -> IngestionJobResponse:
        """Return ingestion job metadata with sanitized error messages."""
        job = self._job_repository.get_by_id(
            workspace_id=workspace_id,
            id=job_id,
        )
        if job is None:
            raise IngestionJobNotFoundError()

        response = IngestionJobResponse.model_validate(job)
        sanitized_error = sanitize_ingestion_error_message(
            response.error_message,
        )
        return response.model_copy(update={"error_message": sanitized_error})
