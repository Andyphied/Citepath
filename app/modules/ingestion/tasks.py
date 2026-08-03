"""Celery tasks for the ingestion pipeline."""

from datetime import UTC, datetime
from uuid import UUID

import structlog
from celery.exceptions import MaxRetriesExceededError
from sqlalchemy.orm import Session

from app.infrastructure.celery_app import celery_app
from app.infrastructure.config import get_settings
from app.infrastructure.db.enums import DocumentStatus, IngestionJobStatus
from app.infrastructure.db.session import get_session_factory
from app.infrastructure.llm.factory import create_embedding_provider
from app.infrastructure.storage import create_storage_backend
from app.infrastructure.storage.validation import reject_unsafe_storage_key
from app.modules.documents.repository import DocumentRepository
from app.modules.documents.sanitization import sanitize_ingestion_error_message
from app.modules.ingestion.chunk_storage import ChunkStorageError, persist_embedded_chunks
from app.modules.ingestion.chunker import chunk_extraction_result
from app.modules.ingestion.embeddings import EmbeddingError, embed_content_chunks
from app.modules.ingestion.extractors import (
    ExtractionError,
    extract_document_text,
)
from app.modules.ingestion.job_repository import IngestionJobRepository
from app.modules.ingestion.pipeline import truncate_error_message
from app.modules.ingestion.repository import IngestionRepository
from app.modules.ingestion.retry import (
    INGESTION_MAX_RETRIES,
    RetryableIngestionError,
    is_retryable_exception,
    retry_countdown_seconds,
)
from app.modules.observability.metrics import (
    observe_ingestion_duration,
    observe_ingestion_failure,
    observe_ingestion_job,
)
from app.modules.observability.worker_heartbeat import register_celery_heartbeat
from app.modules.usage.service import UsageService

logger = structlog.get_logger(__name__)

# OBS-007: structured worker heartbeat on Celery worker_ready.
register_celery_heartbeat(celery_app)


def _duration_seconds_since(started_at: datetime | None) -> float | None:
    if not isinstance(started_at, datetime):
        return None
    start = started_at if started_at.tzinfo is not None else started_at.replace(tzinfo=UTC)
    try:
        return max((datetime.now(UTC) - start).total_seconds(), 0.0)
    except TypeError:
        return None


def _client_safe_error_message(error_message: str) -> str:
    """Persist a truncated, client-safe error without storage paths."""
    truncated = truncate_error_message(error_message)
    return sanitize_ingestion_error_message(truncated) or truncated


def _fail_ingestion(
    *,
    session: Session,
    job,
    document,
    error_message: str,
    job_id: str,
    document_id: str,
    workspace_id: str,
    error_type: str,
    exc: BaseException | None = None,
) -> None:
    """Mark job and document failed in one commit; log + metrics (OBS-005)."""
    safe_message = _client_safe_error_message(error_message)
    completed_at = datetime.now(UTC)
    duration_seconds = _duration_seconds_since(getattr(job, "started_at", None))

    job.status = IngestionJobStatus.FAILED
    job.error_message = safe_message
    job.completed_at = completed_at
    document.status = DocumentStatus.FAILED
    session.commit()

    observe_ingestion_job(status=IngestionJobStatus.FAILED.value)
    observe_ingestion_failure(error_type=error_type)
    if duration_seconds is not None:
        observe_ingestion_duration(
            status=IngestionJobStatus.FAILED.value,
            seconds=duration_seconds,
        )

    log_kwargs = {
        "job_id": job_id,
        "document_id": document_id,
        "workspace_id": workspace_id,
        "error_message": truncate_error_message(error_message),
        "error_type": error_type,
        "duration_seconds": duration_seconds,
    }
    if exc is not None:
        logger.error("ingestion_job_failed", **log_kwargs, exc_info=exc)
    else:
        logger.error("ingestion_job_failed", **log_kwargs, stack_info=True)


def _fail_ingestion_by_ids(
    *,
    job_id: str,
    workspace_id: str,
    document_id: str,
    error_message: str,
    error_type: str = "retries_exhausted",
    exc: BaseException | None = None,
) -> None:
    """Mark job/document failed using a fresh session (post-retry exhaustion)."""
    session = get_session_factory()()
    try:
        parsed_job_id = UUID(job_id)
        parsed_workspace_id = UUID(workspace_id)
        parsed_document_id = UUID(document_id)
        job_repository = IngestionJobRepository(session)
        document_repository = DocumentRepository(session)
        job = job_repository.get_by_id(
            workspace_id=parsed_workspace_id,
            id=parsed_job_id,
        )
        document = document_repository.get_by_id(
            workspace_id=parsed_workspace_id,
            id=parsed_document_id,
        )
        if job is None or document is None:
            logger.warning(
                "ingestion_fail_after_retries_missing_rows",
                job_id=job_id,
                document_id=document_id,
                workspace_id=workspace_id,
            )
            return
        if job.status == IngestionJobStatus.COMPLETED:
            return
        _fail_ingestion(
            session=session,
            job=job,
            document=document,
            error_message=error_message,
            job_id=job_id,
            document_id=document_id,
            workspace_id=workspace_id,
            error_type=error_type,
            exc=exc,
        )
    finally:
        session.close()


def _request_retry_or_fail(
    task,
    *,
    job_id: str,
    workspace_id: str,
    document_id: str,
    error_message: str,
) -> None:
    """Ask Celery to retry a transient failure, or fail permanently when exhausted."""
    countdown = retry_countdown_seconds(task.request.retries)
    logger.warning(
        "ingestion_job_retry_scheduled",
        job_id=job_id,
        document_id=document_id,
        workspace_id=workspace_id,
        error_message=truncate_error_message(error_message),
        retries_so_far=task.request.retries,
        countdown_seconds=countdown,
        max_retries=INGESTION_MAX_RETRIES,
    )
    try:
        raise task.retry(
            exc=RetryableIngestionError(error_message),
            countdown=countdown,
            max_retries=INGESTION_MAX_RETRIES,
        )
    except MaxRetriesExceededError as exc:
        logger.error(
            "ingestion_job_retries_exhausted",
            job_id=job_id,
            document_id=document_id,
            workspace_id=workspace_id,
            error_message=truncate_error_message(error_message),
            max_retries=INGESTION_MAX_RETRIES,
            exc_info=exc,
        )
        _fail_ingestion_by_ids(
            job_id=job_id,
            workspace_id=workspace_id,
            document_id=document_id,
            error_message=error_message,
            error_type="retries_exhausted",
            exc=exc,
        )


def _complete_ingestion(
    *,
    job_repository: IngestionJobRepository,
    document_repository: DocumentRepository,
    job,
    document,
    job_id: str,
    document_id: str,
    workspace_id: str,
    chunk_count: int,
) -> None:
    completed_at = datetime.now(UTC)
    duration_seconds = _duration_seconds_since(getattr(job, "started_at", None))
    job_repository.update(
        job=job,
        status=IngestionJobStatus.COMPLETED,
        completed_at=completed_at,
    )
    observe_ingestion_job(status=IngestionJobStatus.COMPLETED.value)
    if duration_seconds is not None:
        observe_ingestion_duration(
            status=IngestionJobStatus.COMPLETED.value,
            seconds=duration_seconds,
        )
    document_repository.update_status(
        document=document,
        status=DocumentStatus.INDEXED,
    )
    logger.info(
        "ingestion_storage_completed",
        job_id=job_id,
        document_id=document_id,
        workspace_id=workspace_id,
        chunk_count=chunk_count,
        duration_seconds=duration_seconds,
    )


@celery_app.task(
    bind=True,
    name="process_ingestion_job",
    max_retries=INGESTION_MAX_RETRIES,
)
def process_ingestion_job(
    self,
    job_id: str,
    workspace_id: str,
    document_id: str,
) -> None:
    """Pick up an ingestion job, extract text, and prepare for chunking."""
    parsed_job_id = UUID(job_id)
    parsed_workspace_id = UUID(workspace_id)
    parsed_document_id = UUID(document_id)
    retry_message: str | None = None

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
        observe_ingestion_job(status=IngestionJobStatus.PROCESSING.value)
        document_repository.update_status(
            document=document,
            status=DocumentStatus.PROCESSING,
        )

        logger.info(
            "ingestion_job_processing",
            job_id=job_id,
            document_id=document_id,
            workspace_id=workspace_id,
            attempt_count=job.attempt_count,
            celery_retries=self.request.retries,
        )

        if not document.storage_key:
            _fail_ingestion(
                session=session,
                job=job,
                document=document,
                error_message="Document has no storage key",
                job_id=job_id,
                document_id=document_id,
                workspace_id=workspace_id,
                error_type="validation",
            )
            return

        if not document.file_type:
            _fail_ingestion(
                session=session,
                job=job,
                document=document,
                error_message="Document has no file type",
                job_id=job_id,
                document_id=document_id,
                workspace_id=workspace_id,
                error_type="validation",
            )
            return

        expected_storage_prefix = f"{workspace_id}/{document_id}/"
        if not document.storage_key.startswith(expected_storage_prefix):
            _fail_ingestion(
                session=session,
                job=job,
                document=document,
                error_message="Storage key does not match document workspace",
                job_id=job_id,
                document_id=document_id,
                workspace_id=workspace_id,
                error_type="validation",
            )
            return

        try:
            reject_unsafe_storage_key(document.storage_key)
        except ValueError as exc:
            _fail_ingestion(
                session=session,
                job=job,
                document=document,
                error_message=str(exc),
                job_id=job_id,
                document_id=document_id,
                workspace_id=workspace_id,
                error_type="validation",
                exc=exc,
            )
            return

        settings = get_settings()
        storage_backend = create_storage_backend(settings)

        try:
            file_content = storage_backend.get(document.storage_key)
        except (FileNotFoundError, ValueError) as exc:
            _fail_ingestion(
                session=session,
                job=job,
                document=document,
                error_message=str(exc),
                job_id=job_id,
                document_id=document_id,
                workspace_id=workspace_id,
                error_type="storage_read",
                exc=exc,
            )
            return
        except Exception as exc:
            # Classify transient local/S3 I/O (timeouts, connection resets, etc.).
            if is_retryable_exception(exc):
                retry_message = str(exc)
            else:
                _fail_ingestion(
                    session=session,
                    job=job,
                    document=document,
                    error_message=str(exc),
                    job_id=job_id,
                    document_id=document_id,
                    workspace_id=workspace_id,
                    error_type="storage_read",
                    exc=exc,
                )
                return

        if retry_message is None:
            try:
                extraction_result = extract_document_text(
                    file_type=document.file_type,
                    content=file_content,
                )
            except ExtractionError as exc:
                # Permanent: empty/unsupported/corrupt content — no Celery autoretry.
                _fail_ingestion(
                    session=session,
                    job=job,
                    document=document,
                    error_message=exc.message,
                    job_id=job_id,
                    document_id=document_id,
                    workspace_id=workspace_id,
                    error_type="extraction",
                    exc=exc,
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
                if embedded_chunks.retryable:
                    retry_message = embedded_chunks.message
                else:
                    _fail_ingestion(
                        session=session,
                        job=job,
                        document=document,
                        error_message=embedded_chunks.message,
                        job_id=job_id,
                        document_id=document_id,
                        workspace_id=workspace_id,
                        error_type="embedding",
                    )
            else:
                logger.info(
                    "ingestion_embedding_completed",
                    job_id=job_id,
                    document_id=document_id,
                    workspace_id=workspace_id,
                    chunk_count=len(embedded_chunks),
                )

                session.commit()

                ingestion_repository = IngestionRepository(session)
                storage_result = persist_embedded_chunks(
                    ingestion_repository=ingestion_repository,
                    embedded_chunks=embedded_chunks,
                    workspace_id=parsed_workspace_id,
                    document_id=parsed_document_id,
                )
                if isinstance(storage_result, ChunkStorageError):
                    if storage_result.retryable:
                        retry_message = storage_result.message
                    else:
                        _fail_ingestion(
                            session=session,
                            job=job,
                            document=document,
                            error_message=storage_result.message,
                            job_id=job_id,
                            document_id=document_id,
                            workspace_id=workspace_id,
                            error_type="chunk_storage",
                        )
                else:
                    _complete_ingestion(
                        job_repository=job_repository,
                        document_repository=document_repository,
                        job=job,
                        document=document,
                        job_id=job_id,
                        document_id=document_id,
                        workspace_id=workspace_id,
                        chunk_count=storage_result,
                    )
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

    if retry_message is not None:
        _request_retry_or_fail(
            self,
            job_id=job_id,
            workspace_id=workspace_id,
            document_id=document_id,
            error_message=retry_message,
        )
