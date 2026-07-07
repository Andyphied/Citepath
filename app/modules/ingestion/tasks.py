"""Celery tasks for the ingestion pipeline."""

from datetime import UTC, datetime
from uuid import UUID

import structlog

from app.infrastructure.celery_app import celery_app
from app.infrastructure.db.enums import DocumentStatus, IngestionJobStatus
from app.infrastructure.db.session import get_session_factory
from app.modules.documents.repository import DocumentRepository
from app.modules.ingestion.job_repository import IngestionJobRepository

logger = structlog.get_logger(__name__)


@celery_app.task(name="process_ingestion_job")
def process_ingestion_job(
    job_id: str,
    workspace_id: str,
    document_id: str,
) -> None:
    """Pick up an ingestion job and run the pipeline (stub for ING-002+)."""
    parsed_job_id = UUID(job_id)
    parsed_workspace_id = UUID(workspace_id)
    parsed_document_id = UUID(document_id)

    session = get_session_factory()()
    try:
        job_repository = IngestionJobRepository(session)
        document_repository = DocumentRepository(session)

        job = job_repository.get_by_id(
            workspace_id=parsed_workspace_id,
            id=parsed_job_id,
        )
        if job is None:
            logger.warning(
                "ingestion_job_not_found",
                job_id=job_id,
                workspace_id=workspace_id,
            )
            return

        if job.document_id != parsed_document_id:
            logger.warning(
                "ingestion_job_document_mismatch",
                job_id=job_id,
                expected_document_id=str(job.document_id),
                payload_document_id=document_id,
            )
            return

        if job.status in (
            IngestionJobStatus.COMPLETED,
            IngestionJobStatus.FAILED,
        ):
            logger.info(
                "ingestion_job_already_terminal",
                job_id=job_id,
                status=job.status.value,
            )
            return

        document = document_repository.get_by_id(
            workspace_id=parsed_workspace_id,
            id=parsed_document_id,
        )
        if document is None:
            logger.warning(
                "ingestion_document_not_found",
                job_id=job_id,
                document_id=document_id,
                workspace_id=workspace_id,
            )
            return

        started_at = datetime.now(UTC)
        job_repository.update(
            job=job,
            status=IngestionJobStatus.PROCESSING,
            attempt_count=job.attempt_count + 1,
            started_at=started_at,
        )
        document_repository.update_status(
            document=document,
            status=DocumentStatus.PROCESSING,
        )

        logger.info(
            "ingestion_job_processing",
            job_id=job_id,
            document_id=document_id,
            workspace_id=workspace_id,
        )

        # ING-002+ will extract, chunk, embed, and persist vectors here.
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
