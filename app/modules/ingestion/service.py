"""Ingestion domain service."""

from uuid import UUID

from app.modules.ingestion.job_repository import IngestionJobRepository
from app.modules.ingestion.schemas import IngestionJobResponse


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

        # Import here to avoid circular imports between service and tasks.
        from app.modules.ingestion.tasks import process_ingestion_job

        process_ingestion_job.delay(
            str(job.id),
            str(workspace_id),
            str(document_id),
        )
        return IngestionJobResponse.model_validate(job)
