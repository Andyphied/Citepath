"""Unit tests for IngestionService job creation and enqueue."""

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from app.infrastructure.db.enums import IngestionJobStatus
from app.modules.ingestion.exceptions import IngestionJobNotFoundError
from app.modules.ingestion.service import IngestionService


@pytest.fixture
def workspace_id():
    return uuid4()


@pytest.fixture
def document_id():
    return uuid4()


def test_create_job_for_document_persists_pending_and_enqueues(
    workspace_id,
    document_id,
) -> None:
    repository = MagicMock()
    job = MagicMock()
    job.id = uuid4()
    job.workspace_id = workspace_id
    job.document_id = document_id
    job.status = IngestionJobStatus.PENDING
    job.attempt_count = 0
    job.error_message = None
    job.started_at = None
    job.completed_at = None
    job.created_at = "2026-07-07T00:00:00Z"
    repository.create.return_value = job

    service = IngestionService(repository)

    with patch("app.modules.ingestion.tasks.process_ingestion_job") as mock_task:
        result = service.create_job_for_document(
            workspace_id=workspace_id,
            document_id=document_id,
        )

    repository.create.assert_called_once_with(
        workspace_id=workspace_id,
        document_id=document_id,
    )
    mock_task.delay.assert_called_once_with(
        str(job.id),
        str(workspace_id),
        str(document_id),
    )
    assert result.status == "pending"
    assert result.document_id == document_id
    assert result.workspace_id == workspace_id


def test_get_job_returns_sanitized_response(workspace_id) -> None:
    job_id = uuid4()
    repository = MagicMock()
    job = MagicMock()
    job.id = job_id
    job.workspace_id = workspace_id
    job.document_id = uuid4()
    job.status = IngestionJobStatus.FAILED
    job.attempt_count = 1
    job.error_message = "Storage object not found: workspace/doc/file.pdf"
    job.started_at = datetime(2026, 7, 12, tzinfo=UTC)
    job.completed_at = datetime(2026, 7, 12, tzinfo=UTC)
    job.created_at = datetime(2026, 7, 12, tzinfo=UTC)
    repository.get_by_id.return_value = job

    service = IngestionService(repository)
    result = service.get_job(workspace_id=workspace_id, job_id=job_id)

    repository.get_by_id.assert_called_once_with(
        workspace_id=workspace_id,
        id=job_id,
    )
    assert result.status == "failed"
    assert result.error_message == "Stored file could not be read"


def test_get_job_raises_when_missing(workspace_id) -> None:
    repository = MagicMock()
    repository.get_by_id.return_value = None
    service = IngestionService(repository)

    with pytest.raises(IngestionJobNotFoundError):
        service.get_job(workspace_id=workspace_id, job_id=uuid4())
