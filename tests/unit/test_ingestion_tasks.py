"""Unit tests for process_ingestion_job Celery task."""

from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from app.infrastructure.db.enums import DocumentStatus, IngestionJobStatus
from app.modules.ingestion.tasks import process_ingestion_job

FIXTURES_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "documents"


def _assert_terminal_failure(
    *,
    job,
    document,
    session,
    error_substring: str | None = None,
) -> None:
    """OBS-005: job + document failed via single session commit."""
    assert job.status == IngestionJobStatus.FAILED
    assert document.status == DocumentStatus.FAILED
    assert job.completed_at is not None
    if error_substring is not None:
        assert error_substring in (job.error_message or "")
    session.commit.assert_called()


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
    job.started_at = None
    job.completed_at = None
    job.error_message = None
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
        EMBEDDING_BATCH_SIZE=64,
        EMBEDDING_MODEL="text-embedding-3-small",
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
    ), patch(
        "app.modules.ingestion.tasks.chunk_extraction_result",
        return_value=[MagicMock(chunk_index=0)],
    ), patch(
        "app.modules.ingestion.tasks.create_embedding_provider",
    ), patch(
        "app.modules.ingestion.tasks.embed_content_chunks",
        return_value=[MagicMock(chunk_index=0)],
    ), patch(
        "app.modules.ingestion.tasks.persist_embedded_chunks",
        return_value=1,
    ):
        process_ingestion_job(
            str(job_id),
            str(workspace_id),
            str(document_id),
        )

    job_repository.update.assert_called()
    update_kwargs = job_repository.update.call_args_list[0].kwargs
    assert update_kwargs["status"] == IngestionJobStatus.PROCESSING
    assert update_kwargs["attempt_count"] == 1
    assert isinstance(update_kwargs["started_at"], datetime)

    document_repository.update_status.assert_any_call(
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
        EMBEDDING_BATCH_SIZE=64,
        EMBEDDING_MODEL="text-embedding-3-small",
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
    ) as mock_chunk, patch(
        "app.modules.ingestion.tasks.create_embedding_provider",
    ), patch(
        "app.modules.ingestion.tasks.embed_content_chunks",
    ) as mock_embed, patch(
        "app.modules.ingestion.tasks.persist_embedded_chunks",
        return_value=1,
    ):
        mock_chunk.return_value = [MagicMock(chunk_index=0)]
        mock_embed.return_value = [MagicMock(chunk_index=0)]

        process_ingestion_job(
            str(job_id),
            str(workspace_id),
            str(document_id),
        )

    mock_chunk.assert_called_once()
    mock_embed.assert_called_once()
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
        EMBEDDING_BATCH_SIZE=64,
        EMBEDDING_MODEL="text-embedding-3-small",
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

    assert job_repository.update.call_count == 1
    document_repository.update_status.assert_any_call(
        document=document,
        status=DocumentStatus.PROCESSING,
    )
    _assert_terminal_failure(
        job=job,
        document=document,
        session=session,
        error_substring="Failed to read PDF",
    )
    assert isinstance(job.completed_at, datetime)


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
        EMBEDDING_BATCH_SIZE=64,
        EMBEDDING_MODEL="text-embedding-3-small",
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

    assert job_repository.update.call_count == 1
    _assert_terminal_failure(
        job=job,
        document=document,
        session=session,
        error_substring="Storage key does not match",
    )
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
        EMBEDDING_BATCH_SIZE=64,
        EMBEDDING_MODEL="text-embedding-3-small",
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

    assert job_repository.update.call_count == 1
    _assert_terminal_failure(
        job=job,
        document=document,
        session=session,
        error_substring="Invalid stored file reference",
    )


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

    assert job_repository.update.call_count == 1
    _assert_terminal_failure(
        job=job,
        document=document,
        session=session,
        error_substring="Invalid stored file reference",
    )
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

    _assert_terminal_failure(
        job=job,
        document=document,
        session=session,
        error_substring="no storage key",
    )


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

    _assert_terminal_failure(
        job=job,
        document=document,
        session=session,
        error_substring="no file type",
    )


@patch("app.modules.ingestion.tasks.create_storage_backend")
@patch("app.modules.ingestion.tasks.get_settings")
@patch("app.modules.ingestion.tasks.get_session_factory")
def test_process_ingestion_job_completes_embedding_and_storage(
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
        EMBEDDING_BATCH_SIZE=64,
        EMBEDDING_MODEL="text-embedding-3-small",
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

    content_chunk = MagicMock(chunk_index=0)
    embedded_chunk = MagicMock(chunk_index=0, embedding=[0.1, 0.2])

    with patch(
        "app.modules.ingestion.tasks.IngestionJobRepository",
        return_value=job_repository,
    ), patch(
        "app.modules.ingestion.tasks.DocumentRepository",
        return_value=document_repository,
    ), patch(
        "app.modules.ingestion.tasks.chunk_extraction_result",
        return_value=[content_chunk],
    ), patch(
        "app.modules.ingestion.tasks.create_embedding_provider",
    ) as mock_create_provider, patch(
        "app.modules.ingestion.tasks.embed_content_chunks",
        return_value=[embedded_chunk],
    ) as mock_embed, patch(
        "app.modules.ingestion.tasks.UsageService",
    ) as mock_usage_service, patch(
        "app.modules.ingestion.tasks.persist_embedded_chunks",
        return_value=1,
    ) as mock_persist:
        process_ingestion_job(
            str(job_id),
            str(workspace_id),
            str(document_id),
        )

    mock_create_provider.assert_called_once()
    mock_usage_service.assert_called_once_with(session)
    embed_kwargs = mock_embed.call_args.kwargs
    assert embed_kwargs["workspace_id"] == workspace_id
    assert embed_kwargs["document_id"] == document_id
    assert embed_kwargs["job_id"] == job_id
    assert embed_kwargs["batch_size"] == 64
    assert embed_kwargs["embedding_model"] == "text-embedding-3-small"
    assert job_repository.update.call_count == 2
    completed_update = job_repository.update.call_args_list[1].kwargs
    assert completed_update["status"] == IngestionJobStatus.COMPLETED
    assert isinstance(completed_update["completed_at"], datetime)
    document_repository.update_status.assert_any_call(
        document=document,
        status=DocumentStatus.INDEXED,
    )
    mock_persist.assert_called_once()
    persist_kwargs = mock_persist.call_args.kwargs
    assert persist_kwargs["workspace_id"] == workspace_id
    assert persist_kwargs["document_id"] == document_id
    assert persist_kwargs["embedded_chunks"] == [embedded_chunk]
    session.commit.assert_called_once()


@patch("app.modules.ingestion.tasks.create_storage_backend")
@patch("app.modules.ingestion.tasks.get_settings")
@patch("app.modules.ingestion.tasks.get_session_factory")
def test_process_ingestion_job_fails_on_permanent_embedding_error(
    mock_session_factory,
    mock_get_settings,
    mock_create_storage_backend,
    job_id,
    workspace_id,
    document_id,
) -> None:
    from app.modules.ingestion.embeddings import EmbeddingError

    session = MagicMock()
    mock_session_factory.return_value = MagicMock(return_value=session)
    mock_get_settings.return_value = MagicMock(
        CHUNK_SIZE_TOKENS=1000,
        CHUNK_OVERLAP_TOKENS=150,
        EMBEDDING_BATCH_SIZE=64,
        EMBEDDING_MODEL="text-embedding-3-small",
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
        return_value=[MagicMock(chunk_index=0)],
    ), patch(
        "app.modules.ingestion.tasks.create_embedding_provider",
    ), patch(
        "app.modules.ingestion.tasks.embed_content_chunks",
        return_value=EmbeddingError(
            message="Embedding provider returned 0 vectors for 1 texts",
            retryable=False,
        ),
    ), patch(
        "app.modules.ingestion.tasks.UsageService",
    ):
        process_ingestion_job(
            str(job_id),
            str(workspace_id),
            str(document_id),
        )

    _assert_terminal_failure(
        job=job,
        document=document,
        session=session,
        error_substring="vectors",
    )


@patch("app.modules.ingestion.tasks.create_storage_backend")
@patch("app.modules.ingestion.tasks.get_settings")
@patch("app.modules.ingestion.tasks.get_session_factory")
def test_process_ingestion_job_retries_transient_embedding_timeout(
    mock_session_factory,
    mock_get_settings,
    mock_create_storage_backend,
    job_id,
    workspace_id,
    document_id,
) -> None:
    from celery.exceptions import Retry

    from app.modules.ingestion.embeddings import EmbeddingError

    session = MagicMock()
    mock_session_factory.return_value = MagicMock(return_value=session)
    mock_get_settings.return_value = MagicMock(
        CHUNK_SIZE_TOKENS=1000,
        CHUNK_OVERLAP_TOKENS=150,
        EMBEDDING_BATCH_SIZE=64,
        EMBEDDING_MODEL="text-embedding-3-small",
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
        return_value=[MagicMock(chunk_index=0)],
    ), patch(
        "app.modules.ingestion.tasks.create_embedding_provider",
    ), patch(
        "app.modules.ingestion.tasks.embed_content_chunks",
        return_value=EmbeddingError(
            message="Embedding generation failed after retry: provider timeout",
            retryable=True,
        ),
    ), patch(
        "app.modules.ingestion.tasks.UsageService",
    ), patch.object(
        process_ingestion_job,
        "retry",
        side_effect=Retry(message="retry"),
    ) as mock_retry:
        with pytest.raises(Retry):
            process_ingestion_job(
                str(job_id),
                str(workspace_id),
                str(document_id),
            )

    mock_retry.assert_called_once()
    retry_kwargs = mock_retry.call_args.kwargs
    assert retry_kwargs["max_retries"] == 3
    assert retry_kwargs["countdown"] == 1
    # Job stays processing — no terminal failed update yet.
    assert job_repository.update.call_count == 1
    assert job_repository.update.call_args.kwargs["status"] == IngestionJobStatus.PROCESSING


@patch("app.modules.ingestion.tasks.create_storage_backend")
@patch("app.modules.ingestion.tasks.get_settings")
@patch("app.modules.ingestion.tasks.get_session_factory")
def test_process_ingestion_job_fails_after_retry_exhaustion(
    mock_session_factory,
    mock_get_settings,
    mock_create_storage_backend,
    job_id,
    workspace_id,
    document_id,
) -> None:
    from celery.exceptions import MaxRetriesExceededError

    from app.modules.ingestion.embeddings import EmbeddingError

    session = MagicMock()
    mock_session_factory.return_value = MagicMock(return_value=session)
    mock_get_settings.return_value = MagicMock(
        CHUNK_SIZE_TOKENS=1000,
        CHUNK_OVERLAP_TOKENS=150,
        EMBEDDING_BATCH_SIZE=64,
        EMBEDDING_MODEL="text-embedding-3-small",
    )
    storage_backend = MagicMock()
    storage_backend.get.return_value = (FIXTURES_DIR / "sample.txt").read_bytes()
    mock_create_storage_backend.return_value = storage_backend

    job = _build_job(
        job_id=job_id,
        workspace_id=workspace_id,
        document_id=document_id,
        attempt_count=3,
    )
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
        return_value=[MagicMock(chunk_index=0)],
    ), patch(
        "app.modules.ingestion.tasks.create_embedding_provider",
    ), patch(
        "app.modules.ingestion.tasks.embed_content_chunks",
        return_value=EmbeddingError(
            message="Embedding generation failed after retry: provider timeout",
            retryable=True,
        ),
    ), patch(
        "app.modules.ingestion.tasks.UsageService",
    ), patch.object(
        process_ingestion_job,
        "retry",
        side_effect=MaxRetriesExceededError("exhausted"),
    ):
        process_ingestion_job(
            str(job_id),
            str(workspace_id),
            str(document_id),
        )

    _assert_terminal_failure(
        job=job,
        document=document,
        session=session,
        error_substring="provider timeout",
    )


@patch("app.modules.ingestion.tasks.create_storage_backend")
@patch("app.modules.ingestion.tasks.get_settings")
@patch("app.modules.ingestion.tasks.get_session_factory")
def test_process_ingestion_job_completes_after_transient_embedding_retry(
    mock_session_factory,
    mock_get_settings,
    mock_create_storage_backend,
    job_id,
    workspace_id,
    document_id,
) -> None:
    """AC: transient embedding timeout retries, then job completes."""
    from celery.exceptions import Retry

    from app.modules.ingestion.embeddings import EmbeddingError

    session = MagicMock()
    mock_session_factory.return_value = MagicMock(return_value=session)
    mock_get_settings.return_value = MagicMock(
        CHUNK_SIZE_TOKENS=1000,
        CHUNK_OVERLAP_TOKENS=150,
        EMBEDDING_BATCH_SIZE=64,
        EMBEDDING_MODEL="text-embedding-3-small",
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

    embed_outcomes = [
        EmbeddingError(
            message="Embedding generation failed after retry: provider timeout",
            retryable=True,
        ),
        [MagicMock(chunk_index=0, embedding=[0.1])],
    ]

    with patch(
        "app.modules.ingestion.tasks.IngestionJobRepository",
        return_value=job_repository,
    ), patch(
        "app.modules.ingestion.tasks.DocumentRepository",
        return_value=document_repository,
    ), patch(
        "app.modules.ingestion.tasks.chunk_extraction_result",
        return_value=[MagicMock(chunk_index=0)],
    ), patch(
        "app.modules.ingestion.tasks.create_embedding_provider",
    ), patch(
        "app.modules.ingestion.tasks.embed_content_chunks",
        side_effect=embed_outcomes,
    ), patch(
        "app.modules.ingestion.tasks.UsageService",
    ), patch(
        "app.modules.ingestion.tasks.persist_embedded_chunks",
        return_value=1,
    ), patch.object(
        process_ingestion_job,
        "retry",
        side_effect=Retry(message="retry"),
    ):
        with pytest.raises(Retry):
            process_ingestion_job(
                str(job_id),
                str(workspace_id),
                str(document_id),
            )

        # Simulate Celery redelivering the same job after backoff.
        job.status = IngestionJobStatus.PROCESSING
        job.attempt_count = 1
        process_ingestion_job(
            str(job_id),
            str(workspace_id),
            str(document_id),
        )

    completed_updates = [
        call.kwargs
        for call in job_repository.update.call_args_list
        if call.kwargs.get("status") == IngestionJobStatus.COMPLETED
    ]
    assert len(completed_updates) == 1
    document_repository.update_status.assert_any_call(
        document=document,
        status=DocumentStatus.INDEXED,
    )


@patch("app.modules.ingestion.tasks.create_storage_backend")
@patch("app.modules.ingestion.tasks.get_settings")
@patch("app.modules.ingestion.tasks.get_session_factory")
def test_process_ingestion_job_fails_permanently_on_no_extractable_text(
    mock_session_factory,
    mock_get_settings,
    mock_create_storage_backend,
    job_id,
    workspace_id,
    document_id,
) -> None:
    from app.modules.ingestion.extractors import ExtractionError

    session = MagicMock()
    mock_session_factory.return_value = MagicMock(return_value=session)
    mock_get_settings.return_value = MagicMock(
        CHUNK_SIZE_TOKENS=1000,
        CHUNK_OVERLAP_TOKENS=150,
        EMBEDDING_BATCH_SIZE=64,
        EMBEDDING_MODEL="text-embedding-3-small",
    )
    storage_backend = MagicMock()
    storage_backend.get.return_value = b"   "
    mock_create_storage_backend.return_value = storage_backend

    job = _build_job(job_id=job_id, workspace_id=workspace_id, document_id=document_id)
    document = _build_document(document_id=document_id, workspace_id=workspace_id)
    document.title = "Empty"
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
        "app.modules.ingestion.tasks.extract_document_text",
        side_effect=ExtractionError("no extractable text"),
    ), patch.object(
        process_ingestion_job,
        "retry",
    ) as mock_retry:
        process_ingestion_job(
            str(job_id),
            str(workspace_id),
            str(document_id),
        )

    mock_retry.assert_not_called()
    _assert_terminal_failure(
        job=job,
        document=document,
        session=session,
        error_substring="no extractable text",
    )


@patch("app.modules.ingestion.tasks.observe_ingestion_duration")
@patch("app.modules.ingestion.tasks.observe_ingestion_failure")
@patch("app.modules.ingestion.tasks.logger")
@patch("app.modules.ingestion.tasks.create_storage_backend")
@patch("app.modules.ingestion.tasks.get_settings")
@patch("app.modules.ingestion.tasks.get_session_factory")
def test_extraction_failure_emits_structured_log_and_metrics(
    mock_session_factory,
    mock_get_settings,
    mock_create_storage_backend,
    mock_logger,
    mock_observe_failure,
    mock_observe_duration,
    job_id,
    workspace_id,
    document_id,
) -> None:
    """OBS-005: extraction failure → failed job + structured log + metrics."""
    from app.modules.ingestion.extractors import ExtractionError

    session = MagicMock()
    mock_session_factory.return_value = MagicMock(return_value=session)
    mock_get_settings.return_value = MagicMock(
        CHUNK_SIZE_TOKENS=1000,
        CHUNK_OVERLAP_TOKENS=150,
        EMBEDDING_BATCH_SIZE=64,
        EMBEDDING_MODEL="text-embedding-3-small",
    )
    storage_backend = MagicMock()
    storage_backend.get.return_value = b"content"
    mock_create_storage_backend.return_value = storage_backend

    job = _build_job(job_id=job_id, workspace_id=workspace_id, document_id=document_id)
    job.started_at = datetime.now()
    document = _build_document(document_id=document_id, workspace_id=workspace_id)

    job_repository = MagicMock()
    job_repository.get_by_id.return_value = job
    document_repository = MagicMock()
    document_repository.get_by_id.return_value = document

    extraction_error = ExtractionError("no extractable text")
    with patch(
        "app.modules.ingestion.tasks.IngestionJobRepository",
        return_value=job_repository,
    ), patch(
        "app.modules.ingestion.tasks.DocumentRepository",
        return_value=document_repository,
    ), patch(
        "app.modules.ingestion.tasks.extract_document_text",
        side_effect=extraction_error,
    ):
        process_ingestion_job(
            str(job_id),
            str(workspace_id),
            str(document_id),
        )

    _assert_terminal_failure(
        job=job,
        document=document,
        session=session,
        error_substring="no extractable text",
    )
    mock_observe_failure.assert_called_with(error_type="extraction")
    mock_observe_duration.assert_called()
    assert mock_observe_duration.call_args.kwargs["status"] == "failed"

    mock_logger.error.assert_called()
    log_kwargs = mock_logger.error.call_args.kwargs
    assert mock_logger.error.call_args.args[0] == "ingestion_job_failed"
    assert log_kwargs["job_id"] == str(job_id)
    assert log_kwargs["document_id"] == str(document_id)
    assert log_kwargs["workspace_id"] == str(workspace_id)
    assert log_kwargs["error_type"] == "extraction"
    assert log_kwargs["exc_info"] is extraction_error


@patch("app.modules.ingestion.tasks.create_storage_backend")
@patch("app.modules.ingestion.tasks.get_settings")
@patch("app.modules.ingestion.tasks.get_session_factory")
def test_process_ingestion_job_sanitizes_path_bearing_file_not_found(
    mock_session_factory,
    mock_get_settings,
    mock_create_storage_backend,
    job_id,
    workspace_id,
    document_id,
) -> None:
    """OBS-005: path-bearing FileNotFoundError is sanitized on persist."""
    session = MagicMock()
    mock_session_factory.return_value = MagicMock(return_value=session)
    mock_get_settings.return_value = MagicMock(
        CHUNK_SIZE_TOKENS=1000,
        CHUNK_OVERLAP_TOKENS=150,
        EMBEDDING_BATCH_SIZE=64,
        EMBEDDING_MODEL="text-embedding-3-small",
    )
    storage_key = f"{workspace_id}/{document_id}/missing-runbook.pdf"
    absolute_path = f"/var/data/citepath/storage/{storage_key}"
    storage_backend = MagicMock()
    storage_backend.get.side_effect = FileNotFoundError(
        f"Storage object not found: {absolute_path}"
    )
    mock_create_storage_backend.return_value = storage_backend

    job = _build_job(job_id=job_id, workspace_id=workspace_id, document_id=document_id)
    document = _build_document(
        document_id=document_id,
        workspace_id=workspace_id,
        storage_key=storage_key,
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

    _assert_terminal_failure(job=job, document=document, session=session)
    assert job.error_message == "Stored file could not be read"
    assert absolute_path not in (job.error_message or "")
    assert "/var/data" not in (job.error_message or "")
    assert storage_key not in (job.error_message or "")


@patch("app.modules.ingestion.tasks.create_storage_backend")
@patch("app.modules.ingestion.tasks.get_settings")
@patch("app.modules.ingestion.tasks.get_session_factory")
def test_process_ingestion_job_retries_transient_storage_read_timeout(
    mock_session_factory,
    mock_get_settings,
    mock_create_storage_backend,
    job_id,
    workspace_id,
    document_id,
) -> None:
    """OBS-005 / ING-007: transient storage I/O schedules Celery retry."""
    from celery.exceptions import Retry

    session = MagicMock()
    mock_session_factory.return_value = MagicMock(return_value=session)
    mock_get_settings.return_value = MagicMock(
        CHUNK_SIZE_TOKENS=1000,
        CHUNK_OVERLAP_TOKENS=150,
        EMBEDDING_BATCH_SIZE=64,
        EMBEDDING_MODEL="text-embedding-3-small",
    )
    storage_backend = MagicMock()
    storage_backend.get.side_effect = TimeoutError("storage read timed out")
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
    ), patch.object(
        process_ingestion_job,
        "retry",
        side_effect=Retry(message="retry"),
    ) as mock_retry:
        with pytest.raises(Retry):
            process_ingestion_job(
                str(job_id),
                str(workspace_id),
                str(document_id),
            )

    mock_retry.assert_called_once()
    assert job.status != IngestionJobStatus.FAILED


@patch("app.modules.ingestion.tasks.create_storage_backend")
@patch("app.modules.ingestion.tasks.get_settings")
@patch("app.modules.ingestion.tasks.get_session_factory")
def test_process_ingestion_job_fails_on_storage_error(
    mock_session_factory,
    mock_get_settings,
    mock_create_storage_backend,
    job_id,
    workspace_id,
    document_id,
) -> None:
    from app.modules.ingestion.chunk_storage import ChunkStorageError

    session = MagicMock()
    mock_session_factory.return_value = MagicMock(return_value=session)
    mock_get_settings.return_value = MagicMock(
        CHUNK_SIZE_TOKENS=1000,
        CHUNK_OVERLAP_TOKENS=150,
        EMBEDDING_BATCH_SIZE=64,
        EMBEDDING_MODEL="text-embedding-3-small",
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
        return_value=[MagicMock(chunk_index=0)],
    ), patch(
        "app.modules.ingestion.tasks.create_embedding_provider",
    ), patch(
        "app.modules.ingestion.tasks.embed_content_chunks",
        return_value=[MagicMock(chunk_index=0, embedding=[0.1])],
    ), patch(
        "app.modules.ingestion.tasks.UsageService",
    ), patch(
        "app.modules.ingestion.tasks.persist_embedded_chunks",
        return_value=ChunkStorageError(message="pgvector insert failed"),
    ):
        process_ingestion_job(
            str(job_id),
            str(workspace_id),
            str(document_id),
        )

    _assert_terminal_failure(
        job=job,
        document=document,
        session=session,
        error_substring="pgvector insert failed",
    )
