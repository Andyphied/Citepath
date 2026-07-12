"""Document domain service."""

from pathlib import Path
from uuid import uuid4

from app.infrastructure.config import Settings
from app.infrastructure.db.enums import DocumentStatus
from app.infrastructure.storage.interface import StorageBackend
from app.modules.documents.exceptions import (
    FileTooLargeError,
    UnsupportedFileTypeError,
)
from app.modules.documents.repository import DocumentRepository
from app.modules.documents.schemas import (
    DocumentListResponse,
    DocumentResponse,
    DocumentUploadResponse,
)
from app.modules.ingestion.service import IngestionService
from app.modules.workspaces.context import WorkspaceContext

ALLOWED_EXTENSIONS = frozenset({"md", "txt", "pdf", "json"})
DEFAULT_SOURCE_TYPE = "general"


class DocumentService:
    """Document upload and lifecycle orchestration."""

    def __init__(
        self,
        document_repository: DocumentRepository,
        storage_backend: StorageBackend,
        settings: Settings,
        ingestion_service: IngestionService,
    ) -> None:
        self._document_repository = document_repository
        self._storage_backend = storage_backend
        self._max_upload_bytes = settings.MAX_UPLOAD_BYTES
        self._ingestion_service = ingestion_service

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
