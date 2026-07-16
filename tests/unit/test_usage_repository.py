"""Unit tests for ingestion usage event aggregation."""

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from app.modules.usage.repository import UsageRepository
from app.modules.usage.service import UsageService


@pytest.fixture
def workspace_id():
    return uuid4()


@pytest.fixture
def job_id():
    return uuid4()


def test_sum_embedding_tokens_for_job_sums_document_embedding_events(
    workspace_id,
    job_id,
) -> None:
    session = MagicMock()
    repository = UsageRepository(session)
    session.scalar.return_value = 240

    total = repository.sum_embedding_tokens_for_job(
        workspace_id=workspace_id,
        job_id=job_id,
    )

    assert total == 240
    session.scalar.assert_called_once()


def test_usage_service_delegates_sum_embedding_tokens_for_job(
    workspace_id,
    job_id,
) -> None:
    session = MagicMock()
    service = UsageService(session)

    with patch.object(
        service._repository,
        "sum_embedding_tokens_for_job",
        return_value=200,
    ) as mock_sum:
        total = service.sum_embedding_tokens_for_job(
            workspace_id=workspace_id,
            job_id=job_id,
        )

    assert total == 200
    mock_sum.assert_called_once_with(
        workspace_id=workspace_id,
        job_id=job_id,
    )
