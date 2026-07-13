"""Unit tests for IngestionJobRepository."""

from datetime import UTC, datetime
from unittest.mock import MagicMock
from uuid import uuid4

from app.infrastructure.db.enums import IngestionJobStatus
from app.modules.ingestion.job_repository import IngestionJobRepository
from app.modules.ingestion.models import IngestionJob


def test_get_latest_for_document_returns_most_recent_job() -> None:
    workspace_id = uuid4()
    document_id = uuid4()
    latest_job = IngestionJob(
        id=uuid4(),
        workspace_id=workspace_id,
        document_id=document_id,
        status=IngestionJobStatus.COMPLETED,
        attempt_count=1,
        created_at=datetime(2026, 7, 12, tzinfo=UTC),
    )

    session = MagicMock()
    session.scalar.return_value = latest_job
    repository = IngestionJobRepository(session)

    result = repository.get_latest_for_document(
        workspace_id=workspace_id,
        document_id=document_id,
    )

    assert result == latest_job
    stmt = session.scalar.call_args.args[0]
    assert stmt._limit_clause.value == 1
