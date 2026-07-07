"""Unit tests for process_ingestion_job Celery task."""

from datetime import datetime
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from app.infrastructure.db.enums import DocumentStatus, IngestionJobStatus
from app.modules.ingestion.tasks import process_ingestion_job


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


def _build_document(*, document_id, workspace_id):
    document = MagicMock()
    document.id = document_id
    document.workspace_id = workspace_id
    document.status = DocumentStatus.UPLOADED
    return document


@patch("app.modules.ingestion.tasks.get_session_factory")
def test_process_ingestion_job_sets_processing_status(
    mock_session_factory,
    job_id,
    workspace_id,
    document_id,
) -> None:
    session = MagicMock()
    mock_session_factory.return_value = MagicMock(return_value=session)

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
    session.close.assert_called_once()


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
