"""Celery tasks for the ingestion pipeline."""

from datetime import UTC, datetime
from uuid import UUID

import structlog

from app.infrastructure.celery_app import celery_app
from app.infrastructure.config import get_settings
from app.infrastructure.db.enums import DocumentStatus, IngestionJobStatus
from app.infrastructure.db.session import get_session_factory
from app.infrastructure.storage import create_storage_backend
from app.infrastructure.storage.validation import reject_unsafe_storage_key
from app.modules.documents.repository import DocumentRepository
from app.infrastructure.llm.factory import create_embedding_provider
from app.modules.ingestion.chunker import chunk_extraction_result
from app.modules.ingestion.embeddings import EmbeddingError, embed_content_chunks
from app.modules.usage.service import UsageService
from app.modules.ingestion.extractors import (
    ExtractionError,
    extract_document_text,
)
from app.modules.ingestion.job_repository import IngestionJobRepository
from app.modules.ingestion.pipeline import truncate_error_message

logger = structlog.get_logger(__name__)


def _fail_ingestion(
    *,
    job_repository: IngestionJobRepository,
    document_repository: DocumentRepository,
    job,
    document,
    error_message: str,
    job_id: str,
    document_id: str,
    workspace_id: str,
) -> None:
    truncated_message = truncate_error_message(error_message)
    completed_at = datetime.now(UTC)
    job_repository.update(
        job=job,
        status=IngestionJobStatus.FAILED,
        error_message=truncated_message,
        completed_at=completed_at,
    )
    document_repository.update_status(
        document=document,
        status=DocumentStatus.FAILED,
    )
    logger.error(
        "ingestion_job_failed",
        job_id=job_id,
        document_id=document_id,
        workspace_id=workspace_id,
        error_message=truncated_message,
    )


@celery_app.task(name="process_ingestion_job")
def process_ingestion_job(
    job_id: str,
    workspace_id: str,
    document_id: str,
) -> None:
    """Pick up an ingestion job, extract text, and prepare for chunking."""
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

        if not document.storage_key:
            _fail_ingestion(
                job_repository=job_repository,
                document_repository=document_repository,
                job=job,
                document=document,
                error_message="Document has no storage key",
                job_id=job_id,
                document_id=document_id,
                workspace_id=workspace_id,
            )
            return

        if not document.file_type:
            _fail_ingestion(
                job_repository=job_repository,
                document_repository=document_repository,
                job=job,
                document=document,
                error_message="Document has no file type",
                job_id=job_id,
                document_id=document_id,
                workspace_id=workspace_id,
            )
            return

        expected_storage_prefix = f"{workspace_id}/{document_id}/"
        if not document.storage_key.startswith(expected_storage_prefix):
            _fail_ingestion(
                job_repository=job_repository,
                document_repository=document_repository,
                job=job,
                document=document,
                error_message="Storage key does not match document workspace",
                job_id=job_id,
                document_id=document_id,
                workspace_id=workspace_id,
            )
            return

        try:
            reject_unsafe_storage_key(document.storage_key)
        except ValueError as exc:
            _fail_ingestion(
                job_repository=job_repository,
                document_repository=document_repository,
                job=job,
                document=document,
                error_message=str(exc),
                job_id=job_id,
                document_id=document_id,
                workspace_id=workspace_id,
            )
            return

        settings = get_settings()
        storage_backend = create_storage_backend(settings)

        try:
            file_content = storage_backend.get(document.storage_key)
        except (FileNotFoundError, ValueError) as exc:
            _fail_ingestion(
                job_repository=job_repository,
                document_repository=document_repository,
                job=job,
                document=document,
                error_message=str(exc),
                job_id=job_id,
                document_id=document_id,
                workspace_id=workspace_id,
            )
            return

        try:
            extraction_result = extract_document_text(
                file_type=document.file_type,
                content=file_content,
            )
        except ExtractionError as exc:
            _fail_ingestion(
                job_repository=job_repository,
                document_repository=document_repository,
                job=job,
                document=document,
                error_message=exc.message,
                job_id=job_id,
                document_id=document_id,
                workspace_id=workspace_id,
            )
            return

        logger.info(
            "ingestion_extraction_completed",
            job_id=job_id,
            document_id=document_id,
            workspace_id=workspace_id,
            segment_count=len(extraction_result.segments),
        )

        chunks = chunk_extraction_result(
            extraction_result=extraction_result,
            workspace_id=parsed_workspace_id,
            document_id=parsed_document_id,
            document_title=document.title or "untitled",
            source_type=document.source_type or "general",
            chunk_size_tokens=settings.CHUNK_SIZE_TOKENS,
            chunk_overlap_tokens=settings.CHUNK_OVERLAP_TOKENS,
        )

        logger.info(
            "ingestion_chunking_completed",
            job_id=job_id,
            document_id=document_id,
            workspace_id=workspace_id,
            chunk_count=len(chunks),
        )

        embedding_provider = create_embedding_provider(settings)
        usage_service = UsageService(session)
        embedded_chunks = embed_content_chunks(
            chunks=chunks,
            embedding_provider=embedding_provider,
            usage_service=usage_service,
            workspace_id=parsed_workspace_id,
            document_id=parsed_document_id,
            job_id=parsed_job_id,
            batch_size=settings.EMBEDDING_BATCH_SIZE,
            embedding_model=settings.EMBEDDING_MODEL,
        )
        if isinstance(embedded_chunks, EmbeddingError):
            _fail_ingestion(
                job_repository=job_repository,
                document_repository=document_repository,
                job=job,
                document=document,
                error_message=embedded_chunks.message,
                job_id=job_id,
                document_id=document_id,
                workspace_id=workspace_id,
            )
            return

        logger.info(
            "ingestion_embedding_completed",
            job_id=job_id,
            document_id=document_id,
            workspace_id=workspace_id,
            chunk_count=len(embedded_chunks),
        )

        session.commit()

        # ING-005 will persist embedded chunks to pgvector here.
        _ = embedded_chunks
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
