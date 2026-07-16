"""Unit tests for DocumentService upload validation and persistence."""

from datetime import datetime
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from app.infrastructure.config import Settings
from app.infrastructure.db.enums import DocumentStatus, IngestionJobStatus, WorkspaceRole
from app.modules.documents.exceptions import (
    DocumentNotFoundError,
    DocumentReindexInProgressError,
    EmptyFileError,
    FileTooLargeError,
    InvalidFileContentError,
    UnsupportedFileTypeError,
)
from app.modules.documents.schemas import DocumentDetailResponse, DocumentListResponse
from app.modules.documents.service import DocumentService
from app.modules.ingestion.schemas import IngestionJobResponse
from app.modules.workspaces.context import WorkspaceContext


@pytest.fixture
def settings() -> Settings:
    return Settings(
        DATABASE_URL="postgresql://user:pass@localhost:5432/atlasops",
        REDIS_URL="redis://localhost:6379/0",
        JWT_SECRET_KEY="test-secret-key",
        STORAGE_BACKEND="local",
        LLM_PROVIDER="openai",
        OPENAI_API_KEY="sk-test",
        MAX_UPLOAD_BYTES=1024,
        STORAGE_PATH="/tmp/uploads",
    )


@pytest.fixture
def workspace_context() -> WorkspaceContext:
    return WorkspaceContext(
        workspace_id=uuid4(),
        user_id=uuid4(),
        role=WorkspaceRole.MEMBER,
    )


def _ingestion_job_response(
    *,
    workspace_id,
    document_id,
) -> IngestionJobResponse:
    return IngestionJobResponse(
        id=uuid4(),
        workspace_id=workspace_id,
        document_id=document_id,
        status="pending",
        attempt_count=0,
        error_message=None,
        started_at=None,
        completed_at=None,
        created_at=datetime.fromisoformat("2026-07-07T00:00:00+00:00"),
    )


def _build_service(
    repository: MagicMock,
    settings: Settings,
    *,
    storage: MagicMock | None = None,
    ingestion_service: MagicMock | None = None,
    job_repository: MagicMock | None = None,
    ingestion_repository: MagicMock | None = None,
    audit_repository: MagicMock | None = None,
) -> DocumentService:
    return DocumentService(
        repository,
        storage or MagicMock(),
        settings,
        ingestion_service or MagicMock(),
        job_repository or MagicMock(),
        ingestion_repository or MagicMock(),
        audit_repository or MagicMock(),
    )


def test_upload_persists_document_and_creates_ingestion_job(
    settings: Settings,
    workspace_context: WorkspaceContext,
) -> None:
    repository = MagicMock()
    storage = MagicMock()
    ingestion_service = MagicMock()
    storage.save.return_value = f"{workspace_context.workspace_id}/doc-key/runbook.md"

    created = MagicMock()
    created.id = uuid4()
    created.workspace_id = workspace_context.workspace_id
    created.uploaded_by = workspace_context.user_id
    created.title = "billing-api-runbook.md"
    created.source_type = "general"
    created.file_type = "md"
    created.status = DocumentStatus.UPLOADED
    created.created_at = "2026-07-06T00:00:00Z"
    created.updated_at = "2026-07-06T00:00:00Z"
    repository.create.return_value = created

    job_response = _ingestion_job_response(
        workspace_id=workspace_context.workspace_id,
        document_id=created.id,
    )
    ingestion_service.create_job_for_document.return_value = job_response

    service = _build_service(
        repository,
        settings,
        storage=storage,
        ingestion_service=ingestion_service,
    )
    result = service.upload(
        context=workspace_context,
        file_content=b"# Runbook",
        filename="billing-api-runbook.md",
    )

    storage.save.assert_called_once()
    repository.create.assert_called_once()
    create_kwargs = repository.create.call_args.kwargs
    assert create_kwargs["workspace_id"] == workspace_context.workspace_id
    assert create_kwargs["uploaded_by"] == workspace_context.user_id
    assert create_kwargs["title"] == "billing-api-runbook.md"
    assert create_kwargs["file_type"] == "md"
    assert create_kwargs["status"] == DocumentStatus.UPLOADED
    ingestion_service.create_job_for_document.assert_called_once_with(
        workspace_id=workspace_context.workspace_id,
        document_id=created.id,
    )
    assert result.document.status == "uploaded"
    assert result.document.file_type == "md"
    assert result.ingestion_job.status == "pending"
    assert result.ingestion_job.document_id == created.id


def test_upload_rejects_unsupported_extension(
    settings: Settings,
    workspace_context: WorkspaceContext,
) -> None:
    service = _build_service(MagicMock(), settings)

    with pytest.raises(UnsupportedFileTypeError) as exc_info:
        service.upload(
            context=workspace_context,
            file_content=b"MZ",
            filename="malware.exe",
        )

    assert exc_info.value.extension == "exe"


def test_upload_rejects_empty_file(
    settings: Settings,
    workspace_context: WorkspaceContext,
) -> None:
    service = _build_service(MagicMock(), settings)

    with pytest.raises(EmptyFileError):
        service.upload(
            context=workspace_context,
            file_content=b"",
            filename="empty.md",
        )


def test_upload_rejects_docx_extension(
    settings: Settings,
    workspace_context: WorkspaceContext,
) -> None:
    service = _build_service(MagicMock(), settings)

    with pytest.raises(UnsupportedFileTypeError) as exc_info:
        service.upload(
            context=workspace_context,
            file_content=b"PK\x03\x04",
            filename="report.docx",
        )

    assert exc_info.value.extension == "docx"


def test_upload_rejects_fake_pdf_without_magic_bytes(
    settings: Settings,
    workspace_context: WorkspaceContext,
) -> None:
    service = _build_service(MagicMock(), settings)

    with pytest.raises(InvalidFileContentError) as exc_info:
        service.upload(
            context=workspace_context,
            file_content=b"not a pdf",
            filename="fake.pdf",
        )

    assert exc_info.value.file_type == "pdf"
    assert exc_info.value.reason == "invalid_pdf_signature"


def test_upload_accepts_valid_pdf_magic_bytes(
    settings: Settings,
    workspace_context: WorkspaceContext,
) -> None:
    repository = MagicMock()
    storage = MagicMock()
    ingestion_service = MagicMock()
    storage.save.return_value = "key"

    created = MagicMock()
    created.id = uuid4()
    created.workspace_id = workspace_context.workspace_id
    created.uploaded_by = workspace_context.user_id
    created.title = "report.pdf"
    created.source_type = "general"
    created.file_type = "pdf"
    created.status = DocumentStatus.UPLOADED
    created.created_at = "2026-07-06T00:00:00Z"
    created.updated_at = "2026-07-06T00:00:00Z"
    repository.create.return_value = created
    ingestion_service.create_job_for_document.return_value = _ingestion_job_response(
        workspace_id=workspace_context.workspace_id,
        document_id=created.id,
    )

    service = _build_service(
        repository,
        settings,
        storage=storage,
        ingestion_service=ingestion_service,
    )
    result = service.upload(
        context=workspace_context,
        file_content=b"%PDF-1.4 minimal",
        filename="report.pdf",
    )

    storage.save.assert_called_once()
    assert result.document.file_type == "pdf"


def test_upload_rejects_invalid_utf8_text_file(
    settings: Settings,
    workspace_context: WorkspaceContext,
) -> None:
    service = _build_service(MagicMock(), settings)

    with pytest.raises(InvalidFileContentError) as exc_info:
        service.upload(
            context=workspace_context,
            file_content=b"\xff\xfe",
            filename="notes.txt",
        )

    assert exc_info.value.file_type == "txt"
    assert exc_info.value.reason == "invalid_text_encoding"


def test_upload_rejects_file_over_max_size(
    settings: Settings,
    workspace_context: WorkspaceContext,
) -> None:
    service = _build_service(MagicMock(), settings)

    with pytest.raises(FileTooLargeError) as exc_info:
        service.upload(
            context=workspace_context,
            file_content=b"x" * (settings.MAX_UPLOAD_BYTES + 1),
            filename="large.md",
        )

    assert exc_info.value.max_bytes == settings.MAX_UPLOAD_BYTES


def test_upload_accepts_case_insensitive_extension(
    settings: Settings,
    workspace_context: WorkspaceContext,
) -> None:
    repository = MagicMock()
    storage = MagicMock()
    ingestion_service = MagicMock()
    storage.save.return_value = "key"

    created = MagicMock()
    created.id = uuid4()
    created.workspace_id = workspace_context.workspace_id
    created.uploaded_by = workspace_context.user_id
    created.title = "Notes.MD"
    created.source_type = "general"
    created.file_type = "md"
    created.status = DocumentStatus.UPLOADED
    created.created_at = "2026-07-06T00:00:00Z"
    created.updated_at = "2026-07-06T00:00:00Z"
    repository.create.return_value = created
    ingestion_service.create_job_for_document.return_value = _ingestion_job_response(
        workspace_id=workspace_context.workspace_id,
        document_id=created.id,
    )

    service = _build_service(
        repository,
        settings,
        storage=storage,
        ingestion_service=ingestion_service,
    )
    result = service.upload(
        context=workspace_context,
        file_content=b"# Notes",
        filename="Notes.MD",
    )

    assert result.document.file_type == "md"
    assert repository.create.call_args.kwargs["file_type"] == "md"


def test_list_documents_returns_paginated_response(
    settings: Settings,
    workspace_context: WorkspaceContext,
) -> None:
    repository = MagicMock()
    documents = []
    for index in range(2):
        document = MagicMock()
        document.id = uuid4()
        document.workspace_id = workspace_context.workspace_id
        document.uploaded_by = workspace_context.user_id
        document.title = f"doc-{index}"
        document.source_type = "general"
        document.file_type = "md"
        document.status = DocumentStatus.INDEXED
        document.created_at = datetime.fromisoformat("2026-07-07T00:00:00+00:00")
        document.updated_at = datetime.fromisoformat("2026-07-07T00:00:00+00:00")
        documents.append(document)

    repository.list_for_workspace_paginated.return_value = (documents, 5)
    service = _build_service(repository, settings)

    result = service.list_documents(
        context=workspace_context,
        page=2,
        page_size=2,
        status=DocumentStatus.INDEXED,
    )

    repository.list_for_workspace_paginated.assert_called_once_with(
        workspace_id=workspace_context.workspace_id,
        page=2,
        page_size=2,
        status=DocumentStatus.INDEXED,
    )
    assert isinstance(result, DocumentListResponse)
    assert result.total == 5
    assert result.page == 2
    assert result.page_size == 2
    assert len(result.items) == 2
    assert result.items[0].title == "doc-0"
    assert result.items[0].status == "indexed"


def test_get_document_detail_returns_chunk_count_for_indexed_document(
    settings: Settings,
    workspace_context: WorkspaceContext,
) -> None:
    document_id = uuid4()
    document = MagicMock()
    document.id = document_id
    document.workspace_id = workspace_context.workspace_id
    document.uploaded_by = workspace_context.user_id
    document.title = "indexed-doc.md"
    document.source_type = "general"
    document.file_type = "md"
    document.status = DocumentStatus.INDEXED
    document.created_at = datetime.fromisoformat("2026-07-07T00:00:00+00:00")
    document.updated_at = datetime.fromisoformat("2026-07-07T00:00:00+00:00")

    repository = MagicMock()
    repository.get_by_id.return_value = document

    latest_job = MagicMock()
    latest_job.id = uuid4()
    latest_job.workspace_id = workspace_context.workspace_id
    latest_job.document_id = document_id
    latest_job.status = "completed"
    latest_job.attempt_count = 1
    latest_job.error_message = None
    latest_job.started_at = datetime.fromisoformat("2026-07-07T00:00:01+00:00")
    latest_job.completed_at = datetime.fromisoformat("2026-07-07T00:00:02+00:00")
    latest_job.created_at = datetime.fromisoformat("2026-07-07T00:00:00+00:00")

    job_repository = MagicMock()
    job_repository.get_latest_for_document.return_value = latest_job
    ingestion_repository = MagicMock()
    ingestion_repository.count_chunks_for_document.return_value = 4

    service = _build_service(
        repository,
        settings,
        job_repository=job_repository,
        ingestion_repository=ingestion_repository,
    )
    result = service.get_document_detail(
        context=workspace_context,
        document_id=document_id,
    )

    assert isinstance(result, DocumentDetailResponse)
    assert result.document.status == "indexed"
    assert result.chunk_count == 4
    assert result.error_message is None
    assert result.latest_job is not None
    assert result.latest_job.status == "completed"


def test_get_document_detail_returns_error_message_for_failed_document(
    settings: Settings,
    workspace_context: WorkspaceContext,
) -> None:
    document_id = uuid4()
    document = MagicMock()
    document.id = document_id
    document.workspace_id = workspace_context.workspace_id
    document.uploaded_by = workspace_context.user_id
    document.title = "failed-doc.pdf"
    document.source_type = "general"
    document.file_type = "pdf"
    document.status = DocumentStatus.FAILED
    document.created_at = datetime.fromisoformat("2026-07-07T00:00:00+00:00")
    document.updated_at = datetime.fromisoformat("2026-07-07T00:00:00+00:00")

    repository = MagicMock()
    repository.get_by_id.return_value = document

    latest_job = MagicMock()
    latest_job.id = uuid4()
    latest_job.workspace_id = workspace_context.workspace_id
    latest_job.document_id = document_id
    latest_job.status = "failed"
    latest_job.attempt_count = 1
    latest_job.error_message = "PDF contains no pages"
    latest_job.started_at = datetime.fromisoformat("2026-07-07T00:00:01+00:00")
    latest_job.completed_at = datetime.fromisoformat("2026-07-07T00:00:02+00:00")
    latest_job.created_at = datetime.fromisoformat("2026-07-07T00:00:00+00:00")

    job_repository = MagicMock()
    job_repository.get_latest_for_document.return_value = latest_job

    service = _build_service(
        repository,
        settings,
        job_repository=job_repository,
    )
    result = service.get_document_detail(
        context=workspace_context,
        document_id=document_id,
    )

    assert result.document.status == "failed"
    assert result.error_message == "PDF contains no pages"
    assert result.chunk_count is None
    assert result.latest_job is not None
    assert result.latest_job.error_message == "PDF contains no pages"


def test_get_document_detail_sanitizes_path_bearing_error_message(
    settings: Settings,
    workspace_context: WorkspaceContext,
) -> None:
    document_id = uuid4()
    document = MagicMock()
    document.id = document_id
    document.workspace_id = workspace_context.workspace_id
    document.uploaded_by = workspace_context.user_id
    document.title = "failed-doc.pdf"
    document.source_type = "general"
    document.file_type = "pdf"
    document.status = DocumentStatus.FAILED
    document.created_at = datetime.fromisoformat("2026-07-07T00:00:00+00:00")
    document.updated_at = datetime.fromisoformat("2026-07-07T00:00:00+00:00")

    repository = MagicMock()
    repository.get_by_id.return_value = document

    storage_path = (
        f"{workspace_context.workspace_id}/{document_id}/failed-doc.pdf"
    )
    latest_job = MagicMock()
    latest_job.id = uuid4()
    latest_job.workspace_id = workspace_context.workspace_id
    latest_job.document_id = document_id
    latest_job.status = "failed"
    latest_job.attempt_count = 1
    latest_job.error_message = f"Storage object not found: {storage_path}"
    latest_job.started_at = datetime.fromisoformat("2026-07-07T00:00:01+00:00")
    latest_job.completed_at = datetime.fromisoformat("2026-07-07T00:00:02+00:00")
    latest_job.created_at = datetime.fromisoformat("2026-07-07T00:00:00+00:00")

    job_repository = MagicMock()
    job_repository.get_latest_for_document.return_value = latest_job

    service = _build_service(
        repository,
        settings,
        job_repository=job_repository,
    )
    result = service.get_document_detail(
        context=workspace_context,
        document_id=document_id,
    )

    assert result.error_message == "Stored file could not be read"
    assert result.latest_job is not None
    assert result.latest_job.error_message == "Stored file could not be read"
    assert storage_path not in (result.error_message or "")


def test_get_document_detail_raises_when_document_missing(
    settings: Settings,
    workspace_context: WorkspaceContext,
) -> None:
    repository = MagicMock()
    repository.get_by_id.return_value = None
    service = _build_service(repository, settings)

    with pytest.raises(DocumentNotFoundError):
        service.get_document_detail(
            context=workspace_context,
            document_id=uuid4(),
        )


def test_delete_removes_chunks_jobs_document_storage_and_audits(
    settings: Settings,
    workspace_context: WorkspaceContext,
) -> None:
    document_id = uuid4()
    document = MagicMock()
    document.id = document_id
    document.title = "runbook.md"
    document.storage_key = f"{workspace_context.workspace_id}/{document_id}/runbook.md"

    repository = MagicMock()
    repository.get_by_id.return_value = document
    storage = MagicMock()
    ingestion_repository = MagicMock()
    job_repository = MagicMock()
    audit_repository = MagicMock()

    service = _build_service(
        repository,
        settings,
        storage=storage,
        ingestion_repository=ingestion_repository,
        job_repository=job_repository,
        audit_repository=audit_repository,
    )
    service.delete(
        context=workspace_context,
        document_id=document_id,
        ip_address="127.0.0.1",
    )

    repository.get_by_id.assert_called_once_with(
        workspace_id=workspace_context.workspace_id,
        id=document_id,
    )
    ingestion_repository.delete_chunks_for_document.assert_called_once_with(
        workspace_id=workspace_context.workspace_id,
        document_id=document_id,
    )
    job_repository.delete_for_document.assert_called_once_with(
        workspace_id=workspace_context.workspace_id,
        document_id=document_id,
    )
    audit_repository.create.assert_called_once_with(
        workspace_id=workspace_context.workspace_id,
        actor_user_id=workspace_context.user_id,
        event_type="document.deleted",
        metadata={
            "document_id": str(document_id),
            "title": "runbook.md",
        },
        ip_address="127.0.0.1",
    )
    repository.delete.assert_called_once_with(document=document)
    storage.delete.assert_called_once_with(document.storage_key)


def test_delete_raises_when_document_missing(
    settings: Settings,
    workspace_context: WorkspaceContext,
) -> None:
    repository = MagicMock()
    repository.get_by_id.return_value = None
    service = _build_service(repository, settings)

    with pytest.raises(DocumentNotFoundError):
        service.delete(
            context=workspace_context,
            document_id=uuid4(),
        )

    repository.delete.assert_not_called()


def test_reindex_deletes_chunks_resets_status_enqueues_job_and_audits(
    settings: Settings,
    workspace_context: WorkspaceContext,
) -> None:
    document_id = uuid4()
    document = MagicMock()
    document.id = document_id
    document.title = "indexed-runbook.md"
    document.workspace_id = workspace_context.workspace_id
    document.uploaded_by = workspace_context.user_id
    document.source_type = "general"
    document.file_type = "md"
    document.status = DocumentStatus.INDEXED
    document.created_at = datetime.fromisoformat("2026-07-07T00:00:00+00:00")
    document.updated_at = datetime.fromisoformat("2026-07-07T00:00:00+00:00")

    completed_job = MagicMock()
    completed_job.status = IngestionJobStatus.COMPLETED

    updated_document = MagicMock()
    updated_document.id = document_id
    updated_document.workspace_id = workspace_context.workspace_id
    updated_document.uploaded_by = workspace_context.user_id
    updated_document.title = "indexed-runbook.md"
    updated_document.source_type = "general"
    updated_document.file_type = "md"
    updated_document.status = DocumentStatus.PROCESSING
    updated_document.created_at = document.created_at
    updated_document.updated_at = document.updated_at

    repository = MagicMock()
    repository.get_by_id.return_value = document
    repository.update_status.return_value = updated_document

    job_repository = MagicMock()
    job_repository.get_latest_for_document.return_value = completed_job

    ingestion_repository = MagicMock()
    ingestion_service = MagicMock()
    audit_repository = MagicMock()
    job_response = _ingestion_job_response(
        workspace_id=workspace_context.workspace_id,
        document_id=document_id,
    )
    ingestion_service.create_job_for_document.return_value = job_response

    service = _build_service(
        repository,
        settings,
        ingestion_service=ingestion_service,
        job_repository=job_repository,
        ingestion_repository=ingestion_repository,
        audit_repository=audit_repository,
    )
    result = service.reindex(
        context=workspace_context,
        document_id=document_id,
        ip_address="127.0.0.1",
    )

    ingestion_repository.delete_chunks_for_document.assert_called_once_with(
        workspace_id=workspace_context.workspace_id,
        document_id=document_id,
    )
    repository.update_status.assert_called_once_with(
        document=document,
        status=DocumentStatus.PROCESSING,
    )
    audit_repository.create.assert_called_once_with(
        workspace_id=workspace_context.workspace_id,
        actor_user_id=workspace_context.user_id,
        event_type="document.reindex_requested",
        metadata={
            "document_id": str(document_id),
            "title": "indexed-runbook.md",
        },
        ip_address="127.0.0.1",
    )
    ingestion_service.create_job_for_document.assert_called_once_with(
        workspace_id=workspace_context.workspace_id,
        document_id=document_id,
    )
    assert result.document.status == "processing"
    assert result.ingestion_job.status == "pending"


@pytest.mark.parametrize(
    "job_status",
    [IngestionJobStatus.PENDING, IngestionJobStatus.PROCESSING],
)
def test_reindex_raises_when_job_already_in_progress(
    settings: Settings,
    workspace_context: WorkspaceContext,
    job_status: IngestionJobStatus,
) -> None:
    document_id = uuid4()
    document = MagicMock()
    document.id = document_id

    latest_job = MagicMock()
    latest_job.status = job_status

    repository = MagicMock()
    repository.get_by_id.return_value = document
    job_repository = MagicMock()
    job_repository.get_latest_for_document.return_value = latest_job
    ingestion_repository = MagicMock()

    service = _build_service(
        repository,
        settings,
        job_repository=job_repository,
        ingestion_repository=ingestion_repository,
    )

    with pytest.raises(DocumentReindexInProgressError):
        service.reindex(
            context=workspace_context,
            document_id=document_id,
        )

    ingestion_repository.delete_chunks_for_document.assert_not_called()


def test_reindex_raises_when_document_missing(
    settings: Settings,
    workspace_context: WorkspaceContext,
) -> None:
    repository = MagicMock()
    repository.get_by_id.return_value = None
    service = _build_service(repository, settings)

    with pytest.raises(DocumentNotFoundError):
        service.reindex(
            context=workspace_context,
            document_id=uuid4(),
        )
