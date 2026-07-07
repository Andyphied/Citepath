"""Unit tests for process_ingestion_job Celery task."""

from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from app.infrastructure.db.enums import DocumentStatus, IngestionJobStatus
from app.modules.ingestion.tasks import process_ingestion_job

FIXTURES_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "documents"


@pytest.fixture
def workspace_id():
    return uuid4()


@pytest.fixture
def document_id():
    return uuid4()


@pytest.fixture
def job_id():
    return uuid4()


def _build_job(
    *,
    job_id,
    workspace_id,
    document_id,
    status=IngestionJobStatus.PENDING,
    attempt_count=0,
):
    job = MagicMock()
    job.id = job_id
    job.workspace_id = workspace_id
    job.document_id = document_id
    job.status = status
    job.attempt_count = attempt_count
    return job


def _build_document(
    *,
    document_id,
    workspace_id,
    file_type="txt",
    storage_key=None,
):
    document = MagicMock()
    document.id = document_id
    document.workspace_id = workspace_id
    document.status = DocumentStatus.UPLOADED
    document.file_type = file_type
    if storage_key is None:
        document.storage_key = f"{workspace_id}/{document_id}/sample.txt"
    else:
        document.storage_key = storage_key
    return document


@patch("app.modules.ingestion.tasks.create_storage_backend")
@patch("app.modules.ingestion.tasks.get_settings")
@patch("app.modules.ingestion.tasks.get_session_factory")
def test_process_ingestion_job_sets_processing_status(
    mock_session_factory,
    mock_get_settings,
    mock_create_storage_backend,
    job_id,
    workspace_id,
    document_id,
) -> None:
    session = MagicMock()
    mock_session_factory.return_value = MagicMock(return_value=session)
    mock_get_settings.return_value = MagicMock(
        CHUNK_SIZE_TOKENS=1000,
        CHUNK_OVERLAP_TOKENS=150,
    )
    storage_backend = MagicMock()
    storage_backend.get.return_value = (FIXTURES_DIR / "sample.txt").read_bytes()
    mock_create_storage_backend.return_value = storage_backend

    job = _build_job(job_id=job_id, workspace_id=workspace_id, document_id=document_id)
    document = _build_document(document_id=document_id, workspace_id=workspace_id)

    job_repository = MagicMock()
    job_repository.get_by_id.return_value = job
    document_repository = MagicMock()
    document_repository.get_by_id.return_value = document

    with patch(
        "app.modules.ingestion.tasks.IngestionJobRepository",
        return_value=job_repository,
    ), patch(
        "app.modules.ingestion.tasks.DocumentRepository",
        return_value=document_repository,
    ):
        process_ingestion_job(
            str(job_id),
            str(workspace_id),
            str(document_id),
        )

    job_repository.update.assert_called_once()
    update_kwargs = job_repository.update.call_args.kwargs
    assert update_kwargs["status"] == IngestionJobStatus.PROCESSING
    assert update_kwargs["attempt_count"] == 1
    assert isinstance(update_kwargs["started_at"], datetime)

    document_repository.update_status.assert_called_once_with(
        document=document,
        status=DocumentStatus.PROCESSING,
    )
    storage_backend.get.assert_called_once_with(document.storage_key)
    session.close.assert_called_once()


@patch("app.modules.ingestion.tasks.create_storage_backend")
@patch("app.modules.ingestion.tasks.get_settings")
@patch("app.modules.ingestion.tasks.get_session_factory")
def test_process_ingestion_job_completes_chunking(
    mock_session_factory,
    mock_get_settings,
    mock_create_storage_backend,
    job_id,
    workspace_id,
    document_id,
) -> None:
    session = MagicMock()
    mock_session_factory.return_value = MagicMock(return_value=session)
    mock_get_settings.return_value = MagicMock(
        CHUNK_SIZE_TOKENS=1000,
        CHUNK_OVERLAP_TOKENS=150,
    )
    storage_backend = MagicMock()
    storage_backend.get.return_value = (FIXTURES_DIR / "sample.txt").read_bytes()
    mock_create_storage_backend.return_value = storage_backend

    job = _build_job(job_id=job_id, workspace_id=workspace_id, document_id=document_id)
    document = _build_document(document_id=document_id, workspace_id=workspace_id)
    document.title = "Sample Text"
    document.source_type = "general"

    job_repository = MagicMock()
    job_repository.get_by_id.return_value = job
    document_repository = MagicMock()
    document_repository.get_by_id.return_value = document

    with patch(
        "app.modules.ingestion.tasks.IngestionJobRepository",
        return_value=job_repository,
    ), patch(
        "app.modules.ingestion.tasks.DocumentRepository",
        return_value=document_repository,
    ), patch(
        "app.modules.ingestion.tasks.chunk_extraction_result",
    ) as mock_chunk:
        mock_chunk.return_value = [MagicMock(chunk_index=0)]

        process_ingestion_job(
            str(job_id),
            str(workspace_id),
            str(document_id),
        )

    mock_chunk.assert_called_once()
    chunk_kwargs = mock_chunk.call_args.kwargs
    assert chunk_kwargs["workspace_id"] == workspace_id
    assert chunk_kwargs["document_id"] == document_id
    assert chunk_kwargs["document_title"] == "Sample Text"
    assert chunk_kwargs["source_type"] == "general"
    assert chunk_kwargs["chunk_size_tokens"] == 1000
    assert chunk_kwargs["chunk_overlap_tokens"] == 150


@patch("app.modules.ingestion.tasks.create_storage_backend")
@patch("app.modules.ingestion.tasks.get_settings")
@patch("app.modules.ingestion.tasks.get_session_factory")
def test_process_ingestion_job_fails_on_corrupt_pdf(
    mock_session_factory,
    mock_get_settings,
    mock_create_storage_backend,
    job_id,
    workspace_id,
    document_id,
) -> None:
    session = MagicMock()
    mock_session_factory.return_value = MagicMock(return_value=session)
    mock_get_settings.return_value = MagicMock(
        CHUNK_SIZE_TOKENS=1000,
        CHUNK_OVERLAP_TOKENS=150,
    )
    storage_backend = MagicMock()
    storage_backend.get.return_value = (FIXTURES_DIR / "corrupt.pdf").read_bytes()
    mock_create_storage_backend.return_value = storage_backend

    job = _build_job(job_id=job_id, workspace_id=workspace_id, document_id=document_id)
    document = _build_document(
        document_id=document_id,
        workspace_id=workspace_id,
        file_type="pdf",
        storage_key=f"{workspace_id}/{document_id}/corrupt.pdf",
    )

    job_repository = MagicMock()
    job_repository.get_by_id.return_value = job
    document_repository = MagicMock()
    document_repository.get_by_id.return_value = document

    with patch(
        "app.modules.ingestion.tasks.IngestionJobRepository",
        return_value=job_repository,
    ), patch(
        "app.modules.ingestion.tasks.DocumentRepository",
        return_value=document_repository,
    ):
        process_ingestion_job(
            str(job_id),
            str(workspace_id),
            str(document_id),
        )

    assert job_repository.update.call_count == 2
    failure_update = job_repository.update.call_args_list[1].kwargs
    assert failure_update["status"] == IngestionJobStatus.FAILED
    assert failure_update["error_message"] is not None
    assert "Failed to read PDF" in failure_update["error_message"]
    assert isinstance(failure_update["completed_at"], datetime)

    document_repository.update_status.assert_any_call(
        document=document,
        status=DocumentStatus.PROCESSING,
    )
    document_repository.update_status.assert_any_call(
        document=document,
        status=DocumentStatus.FAILED,
    )


@patch("app.modules.ingestion.tasks.get_session_factory")
def test_process_ingestion_job_skips_when_document_id_mismatch(
    mock_session_factory,
    job_id,
    workspace_id,
    document_id,
) -> None:
    session = MagicMock()
    mock_session_factory.return_value = MagicMock(return_value=session)

    job = _build_job(
        job_id=job_id,
        workspace_id=workspace_id,
        document_id=uuid4(),
    )
    job_repository = MagicMock()
    job_repository.get_by_id.return_value = job
    document_repository = MagicMock()

    with patch(
        "app.modules.ingestion.tasks.IngestionJobRepository",
        return_value=job_repository,
    ), patch(
        "app.modules.ingestion.tasks.DocumentRepository",
        return_value=document_repository,
    ):
        process_ingestion_job(
            str(job_id),
            str(workspace_id),
            str(document_id),
        )

    job_repository.update.assert_not_called()
    document_repository.update_status.assert_not_called()


@patch("app.modules.ingestion.tasks.get_session_factory")
def test_process_ingestion_job_skips_terminal_jobs(
    mock_session_factory,
    job_id,
    workspace_id,
    document_id,
) -> None:
    session = MagicMock()
    mock_session_factory.return_value = MagicMock(return_value=session)

    job = _build_job(
        job_id=job_id,
        workspace_id=workspace_id,
        document_id=document_id,
        status=IngestionJobStatus.COMPLETED,
    )
    job_repository = MagicMock()
    job_repository.get_by_id.return_value = job
    document_repository = MagicMock()

    with patch(
        "app.modules.ingestion.tasks.IngestionJobRepository",
        return_value=job_repository,
    ), patch(
        "app.modules.ingestion.tasks.DocumentRepository",
        return_value=document_repository,
    ):
        process_ingestion_job(
            str(job_id),
            str(workspace_id),
            str(document_id),
        )

    job_repository.update.assert_not_called()
    document_repository.update_status.assert_not_called()


@patch("app.modules.ingestion.tasks.create_storage_backend")
@patch("app.modules.ingestion.tasks.get_settings")
@patch("app.modules.ingestion.tasks.get_session_factory")
def test_process_ingestion_job_fails_on_storage_key_prefix_mismatch(
    mock_session_factory,
    mock_get_settings,
    mock_create_storage_backend,
    job_id,
    workspace_id,
    document_id,
) -> None:
    session = MagicMock()
    mock_session_factory.return_value = MagicMock(return_value=session)
    mock_get_settings.return_value = MagicMock(
        CHUNK_SIZE_TOKENS=1000,
        CHUNK_OVERLAP_TOKENS=150,
    )
    mock_create_storage_backend.return_value = MagicMock()

    job = _build_job(job_id=job_id, workspace_id=workspace_id, document_id=document_id)
    document = _build_document(
        document_id=document_id,
        workspace_id=workspace_id,
        storage_key=f"{uuid4()}/{document_id}/sample.txt",
    )

    job_repository = MagicMock()
    job_repository.get_by_id.return_value = job
    document_repository = MagicMock()
    document_repository.get_by_id.return_value = document

    with patch(
        "app.modules.ingestion.tasks.IngestionJobRepository",
        return_value=job_repository,
    ), patch(
        "app.modules.ingestion.tasks.DocumentRepository",
        return_value=document_repository,
    ):
        process_ingestion_job(
            str(job_id),
            str(workspace_id),
            str(document_id),
        )

    assert job_repository.update.call_count == 2
    failure_update = job_repository.update.call_args_list[1].kwargs
    assert failure_update["status"] == IngestionJobStatus.FAILED
    assert "Storage key does not match" in failure_update["error_message"]
    mock_create_storage_backend.return_value.get.assert_not_called()


@patch("app.modules.ingestion.tasks.create_storage_backend")
@patch("app.modules.ingestion.tasks.get_settings")
@patch("app.modules.ingestion.tasks.get_session_factory")
def test_process_ingestion_job_fails_on_invalid_storage_key(
    mock_session_factory,
    mock_get_settings,
    mock_create_storage_backend,
    job_id,
    workspace_id,
    document_id,
) -> None:
    session = MagicMock()
    mock_session_factory.return_value = MagicMock(return_value=session)
    mock_get_settings.return_value = MagicMock(
        CHUNK_SIZE_TOKENS=1000,
        CHUNK_OVERLAP_TOKENS=150,
    )
    storage_backend = MagicMock()
    storage_backend.get.side_effect = ValueError("Invalid storage key: ../../etc/passwd")
    mock_create_storage_backend.return_value = storage_backend

    job = _build_job(job_id=job_id, workspace_id=workspace_id, document_id=document_id)
    document = _build_document(document_id=document_id, workspace_id=workspace_id)

    job_repository = MagicMock()
    job_repository.get_by_id.return_value = job
    document_repository = MagicMock()
    document_repository.get_by_id.return_value = document

    with patch(
        "app.modules.ingestion.tasks.IngestionJobRepository",
        return_value=job_repository,
    ), patch(
        "app.modules.ingestion.tasks.DocumentRepository",
        return_value=document_repository,
    ):
        process_ingestion_job(
            str(job_id),
            str(workspace_id),
            str(document_id),
        )

    assert job_repository.update.call_count == 2
    failure_update = job_repository.update.call_args_list[1].kwargs
    assert failure_update["status"] == IngestionJobStatus.FAILED
    assert "Invalid storage key" in failure_update["error_message"]


@patch("app.modules.ingestion.tasks.get_session_factory")
def test_process_ingestion_job_fails_on_embedded_parent_in_storage_key(
    mock_session_factory,
    job_id,
    workspace_id,
    document_id,
) -> None:
    session = MagicMock()
    mock_session_factory.return_value = MagicMock(return_value=session)

    job = _build_job(job_id=job_id, workspace_id=workspace_id, document_id=document_id)
    other_workspace = uuid4()
    document = _build_document(
        document_id=document_id,
        workspace_id=workspace_id,
        storage_key=f"{workspace_id}/{document_id}/../{other_workspace}/{document_id}/secret.txt",
    )

    job_repository = MagicMock()
    job_repository.get_by_id.return_value = job
    document_repository = MagicMock()
    document_repository.get_by_id.return_value = document

    with patch(
        "app.modules.ingestion.tasks.IngestionJobRepository",
        return_value=job_repository,
    ), patch(
        "app.modules.ingestion.tasks.DocumentRepository",
        return_value=document_repository,
    ), patch(
        "app.modules.ingestion.tasks.create_storage_backend",
    ) as mock_create_storage_backend:
        process_ingestion_job(
            str(job_id),
            str(workspace_id),
            str(document_id),
        )

    assert job_repository.update.call_count == 2
    failure_update = job_repository.update.call_args_list[1].kwargs
    assert failure_update["status"] == IngestionJobStatus.FAILED
    assert "Invalid storage key" in failure_update["error_message"]
    mock_create_storage_backend.return_value.get.assert_not_called()


@patch("app.modules.ingestion.tasks.get_session_factory")
def test_process_ingestion_job_fails_when_storage_key_missing(
    mock_session_factory,
    job_id,
    workspace_id,
    document_id,
) -> None:
    session = MagicMock()
    mock_session_factory.return_value = MagicMock(return_value=session)

    job = _build_job(job_id=job_id, workspace_id=workspace_id, document_id=document_id)
    document = _build_document(
        document_id=document_id,
        workspace_id=workspace_id,
        storage_key="",
    )

    job_repository = MagicMock()
    job_repository.get_by_id.return_value = job
    document_repository = MagicMock()
    document_repository.get_by_id.return_value = document

    with patch(
        "app.modules.ingestion.tasks.IngestionJobRepository",
        return_value=job_repository,
    ), patch(
        "app.modules.ingestion.tasks.DocumentRepository",
        return_value=document_repository,
    ):
        process_ingestion_job(
            str(job_id),
            str(workspace_id),
            str(document_id),
        )

    failure_update = job_repository.update.call_args_list[1].kwargs
    assert failure_update["status"] == IngestionJobStatus.FAILED
    assert "no storage key" in failure_update["error_message"].lower()


@patch("app.modules.ingestion.tasks.get_session_factory")
def test_process_ingestion_job_fails_when_file_type_missing(
    mock_session_factory,
    job_id,
    workspace_id,
    document_id,
) -> None:
    session = MagicMock()
    mock_session_factory.return_value = MagicMock(return_value=session)

    job = _build_job(job_id=job_id, workspace_id=workspace_id, document_id=document_id)
    document = _build_document(
        document_id=document_id,
        workspace_id=workspace_id,
        file_type="",
    )

    job_repository = MagicMock()
    job_repository.get_by_id.return_value = job
    document_repository = MagicMock()
    document_repository.get_by_id.return_value = document

    with patch(
        "app.modules.ingestion.tasks.IngestionJobRepository",
        return_value=job_repository,
    ), patch(
        "app.modules.ingestion.tasks.DocumentRepository",
        return_value=document_repository,
    ):
        process_ingestion_job(
            str(job_id),
            str(workspace_id),
            str(document_id),
        )

    failure_update = job_repository.update.call_args_list[1].kwargs
    assert failure_update["status"] == IngestionJobStatus.FAILED
    assert "no file type" in failure_update["error_message"].lower()
