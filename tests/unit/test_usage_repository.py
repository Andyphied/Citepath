"""Unit tests for ingestion usage event aggregation."""

from datetime import UTC, datetime
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


def test_aggregate_workspace_usage_queries_totals_day_and_operation(
    workspace_id,
) -> None:
    session = MagicMock()
    repository = UsageRepository(session)
    start = datetime(2026, 7, 17, tzinfo=UTC)
    end = datetime(2026, 7, 24, tzinfo=UTC)

    totals_result = MagicMock()
    totals_result.one.return_value = (100, 50, 200, "0.012345", 10)
    day_result = MagicMock()
    day_result.all.return_value = [
        (datetime(2026, 7, 20, tzinfo=UTC), 100, 50, 200, "0.012345", 10),
    ]
    op_result = MagicMock()
    op_result.all.return_value = [
        ("chat_completion", 100, 50, 0, "0.010000", 8),
        ("embedding_query", 0, 0, 200, "0.002345", 2),
    ]
    session.execute.side_effect = [totals_result, day_result, op_result]

    totals, by_day, by_operation = repository.aggregate_workspace_usage(
        workspace_id=workspace_id,
        start=start,
        end=end,
    )

    assert totals.call_count == 10
    assert totals.prompt_tokens == 100
    assert by_day[0].day.isoformat() == "2026-07-20"
    assert by_operation[1].operation == "embedding_query"
    assert session.execute.call_count == 3
