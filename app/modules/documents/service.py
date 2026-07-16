"""Document domain service."""

from pathlib import Path
from uuid import UUID, uuid4

from app.infrastructure.config import Settings
from app.infrastructure.db.enums import DocumentStatus, IngestionJobStatus
from app.infrastructure.storage.interface import StorageBackend
from app.modules.audit.repository import AuditRepository
from app.modules.documents.exceptions import (
    DocumentNotFoundError,
    DocumentReindexInProgressError,
    FileTooLargeError,
    UnsupportedFileTypeError,
)
from app.modules.documents.repository import DocumentRepository
from app.modules.documents.sanitization import sanitize_ingestion_error_message
from app.modules.documents.schemas import (
    DocumentDetailResponse,
    DocumentListResponse,
    DocumentReindexResponse,
    DocumentResponse,
    DocumentUploadResponse,
)
from app.modules.ingestion.job_repository import IngestionJobRepository
from app.modules.ingestion.repository import IngestionRepository
from app.modules.ingestion.schemas import IngestionJobResponse
from app.modules.ingestion.service import IngestionService
from app.modules.workspaces.context import WorkspaceContext

ALLOWED_EXTENSIONS = frozenset({"md", "txt", "pdf", "json"})
DEFAULT_SOURCE_TYPE = "general"
DOCUMENT_DELETED_EVENT = "document.deleted"
DOCUMENT_REINDEX_REQUESTED_EVENT = "document.reindex_requested"


class DocumentService:
    """Document upload and lifecycle orchestration."""

    def __init__(
        self,
        document_repository: DocumentRepository,
        storage_backend: StorageBackend,
        settings: Settings,
        ingestion_service: IngestionService,
        ingestion_job_repository: IngestionJobRepository,
        ingestion_repository: IngestionRepository,
        audit_repository: AuditRepository,
    ) -> None:
        self._document_repository = document_repository
        self._storage_backend = storage_backend
        self._max_upload_bytes = settings.MAX_UPLOAD_BYTES
        self._ingestion_service = ingestion_service
        self._ingestion_job_repository = ingestion_job_repository
        self._ingestion_repository = ingestion_repository
        self._audit_repository = audit_repository

    def upload(
        self,
        *,
        context: WorkspaceContext,
        file_content: bytes,
        filename: str,
        title: str | None = None,
        source_type: str | None = None,
    ) -> DocumentUploadResponse:
        """Validate, store, persist a document, and enqueue ingestion."""
        file_type = self._validate_extension(filename)
        self._validate_size(len(file_content))

        document_id = uuid4()
        storage_key = self._storage_backend.save(
            workspace_id=context.workspace_id,
            document_id=document_id,
            filename=filename,
            content=file_content,
        )

        resolved_title = title or Path(filename).name or "untitled"
        document = self._document_repository.create(
            id=document_id,
            workspace_id=context.workspace_id,
            uploaded_by=context.user_id,
            title=resolved_title,
            source_type=source_type or DEFAULT_SOURCE_TYPE,
            file_type=file_type,
            storage_key=storage_key,
            status=DocumentStatus.UPLOADED,
        )
        ingestion_job = self._ingestion_service.create_job_for_document(
            workspace_id=context.workspace_id,
            document_id=document.id,
        )
        return DocumentUploadResponse(
            document=DocumentResponse.model_validate(document),
            ingestion_job=ingestion_job,
        )

    def list_documents(
        self,
        *,
        context: WorkspaceContext,
        page: int,
        page_size: int,
        status: DocumentStatus | None = None,
    ) -> DocumentListResponse:
        """Return paginated documents for the workspace."""
        documents, total = self._document_repository.list_for_workspace_paginated(
            workspace_id=context.workspace_id,
            page=page,
            page_size=page_size,
            status=status,
        )
        return DocumentListResponse(
            items=[DocumentResponse.model_validate(document) for document in documents],
            total=total,
            page=page,
            page_size=page_size,
        )

    def get_document_detail(
        self,
        *,
        context: WorkspaceContext,
        document_id: UUID,
    ) -> DocumentDetailResponse:
        """Return document metadata with latest ingestion job and chunk count."""
        document = self._document_repository.get_by_id(
            workspace_id=context.workspace_id,
            id=document_id,
        )
        if document is None:
            raise DocumentNotFoundError()

        latest_job = self._ingestion_job_repository.get_latest_for_document(
            workspace_id=context.workspace_id,
            document_id=document_id,
        )

        chunk_count = None
        if document.status == DocumentStatus.INDEXED:
            chunk_count = self._ingestion_repository.count_chunks_for_document(
                workspace_id=context.workspace_id,
                document_id=document_id,
            )

        error_message = None
        latest_job_response = None
        if latest_job is not None:
            latest_job_response = IngestionJobResponse.model_validate(latest_job)
            sanitized_error = sanitize_ingestion_error_message(
                latest_job_response.error_message
            )
            latest_job_response = latest_job_response.model_copy(
                update={"error_message": sanitized_error},
            )
            if document.status == DocumentStatus.FAILED:
                error_message = sanitized_error

        return DocumentDetailResponse(
            document=DocumentResponse.model_validate(document),
            latest_job=latest_job_response,
            chunk_count=chunk_count,
            error_message=error_message,
        )

    def delete(
        self,
        *,
        context: WorkspaceContext,
        document_id: UUID,
        ip_address: str | None = None,
    ) -> None:
        """Delete a document, its chunks, ingestion jobs, storage file, and audit."""
        document = self._document_repository.get_by_id(
            workspace_id=context.workspace_id,
            id=document_id,
        )
        if document is None:
            raise DocumentNotFoundError()

        storage_key = document.storage_key

        self._ingestion_repository.delete_chunks_for_document(
            workspace_id=context.workspace_id,
            document_id=document_id,
        )
        self._ingestion_job_repository.delete_for_document(
            workspace_id=context.workspace_id,
            document_id=document_id,
        )
        self._audit_repository.create(
            workspace_id=context.workspace_id,
            actor_user_id=context.user_id,
            event_type=DOCUMENT_DELETED_EVENT,
            metadata={
                "document_id": str(document_id),
                "title": document.title,
            },
            ip_address=ip_address,
        )
        self._document_repository.delete(document=document)

        if storage_key:
            self._storage_backend.delete(storage_key)

    def reindex(
        self,
        *,
        context: WorkspaceContext,
        document_id: UUID,
        ip_address: str | None = None,
    ) -> DocumentReindexResponse:
        """Delete existing chunks, reset status, enqueue ingestion, and audit."""
        document = self._document_repository.get_by_id(
            workspace_id=context.workspace_id,
            id=document_id,
        )
        if document is None:
            raise DocumentNotFoundError()

        latest_job = self._ingestion_job_repository.get_latest_for_document(
            workspace_id=context.workspace_id,
            document_id=document_id,
        )
        if latest_job is not None and latest_job.status in (
            IngestionJobStatus.PENDING,
            IngestionJobStatus.PROCESSING,
        ):
            raise DocumentReindexInProgressError()

        self._ingestion_repository.delete_chunks_for_document(
            workspace_id=context.workspace_id,
            document_id=document_id,
        )
        updated_document = self._document_repository.update_status(
            document=document,
            status=DocumentStatus.PROCESSING,
        )
        self._audit_repository.create(
            workspace_id=context.workspace_id,
            actor_user_id=context.user_id,
            event_type=DOCUMENT_REINDEX_REQUESTED_EVENT,
            metadata={
                "document_id": str(document_id),
                "title": document.title,
            },
            ip_address=ip_address,
        )
        ingestion_job = self._ingestion_service.create_job_for_document(
            workspace_id=context.workspace_id,
            document_id=document_id,
        )
        return DocumentReindexResponse(
            document=DocumentResponse.model_validate(updated_document),
            ingestion_job=ingestion_job,
        )

    def _validate_extension(self, filename: str) -> str:
        suffix = Path(filename).suffix.lower().lstrip(".")
        if suffix not in ALLOWED_EXTENSIONS:
            raise UnsupportedFileTypeError(extension=suffix or None)
        return suffix

    def _validate_size(self, size: int) -> None:
        if size > self._max_upload_bytes:
            raise FileTooLargeError(
                max_bytes=self._max_upload_bytes,
                actual_bytes=size,
            )
