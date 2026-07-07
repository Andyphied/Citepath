"""Unit tests for DocumentService upload validation and persistence."""

from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from app.infrastructure.config import Settings
from app.infrastructure.db.enums import DocumentStatus
from app.modules.documents.exceptions import FileTooLargeError, UnsupportedFileTypeError
from app.modules.documents.service import DocumentService
from app.modules.workspaces.context import WorkspaceContext
from app.infrastructure.db.enums import WorkspaceRole


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


def test_upload_persists_document_with_uploaded_status(
    settings: Settings,
    workspace_context: WorkspaceContext,
) -> None:
    repository = MagicMock()
    storage = MagicMock()
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

    service = DocumentService(repository, storage, settings)
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
    assert result.status == "uploaded"
    assert result.file_type == "md"


def test_upload_rejects_unsupported_extension(
    settings: Settings,
    workspace_context: WorkspaceContext,
) -> None:
    service = DocumentService(MagicMock(), MagicMock(), settings)

    with pytest.raises(UnsupportedFileTypeError) as exc_info:
        service.upload(
            context=workspace_context,
            file_content=b"MZ",
            filename="malware.exe",
        )

    assert exc_info.value.extension == "exe"


def test_upload_rejects_file_over_max_size(
    settings: Settings,
    workspace_context: WorkspaceContext,
) -> None:
    service = DocumentService(MagicMock(), MagicMock(), settings)

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

    service = DocumentService(repository, storage, settings)
    result = service.upload(
        context=workspace_context,
        file_content=b"# Notes",
        filename="Notes.MD",
    )

    assert result.file_type == "md"
    assert repository.create.call_args.kwargs["file_type"] == "md"
