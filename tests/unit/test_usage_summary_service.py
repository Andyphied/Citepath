"""Unit tests for workspace usage summary aggregation."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from app.modules.usage.exceptions import InvalidUsageRangeError
from app.modules.usage.repository import (
    UsageByDayRow,
    UsageByOperationRow,
    UsageTotalsRow,
)
from app.modules.usage.service import UsageService


@pytest.fixture
def workspace_id():
    return uuid4()


def test_get_workspace_summary_defaults_to_seven_day_window(workspace_id) -> None:
    session = MagicMock()
    service = UsageService(session)
    totals = UsageTotalsRow(
        prompt_tokens=10,
        completion_tokens=5,
        embedding_tokens=20,
        estimated_cost_usd=Decimal("0.001000"),
        call_count=3,
    )
    day = UsageByDayRow(
        day=datetime.now(UTC).date(),
        prompt_tokens=10,
        completion_tokens=5,
        embedding_tokens=20,
        estimated_cost_usd=Decimal("0.001000"),
        call_count=3,
    )
    op = UsageByOperationRow(
        operation="chat_completion",
        prompt_tokens=10,
        completion_tokens=5,
        embedding_tokens=0,
        estimated_cost_usd=Decimal("0.000500"),
        call_count=2,
    )

    with patch.object(
        service._repository,
        "aggregate_workspace_usage",
        return_value=(totals, [day], [op]),
    ) as mock_aggregate:
        summary = service.get_workspace_summary(workspace_id=workspace_id)

    assert summary.workspace_id == workspace_id
    assert summary.totals.call_count == 3
    assert summary.totals.prompt_tokens == 10
    assert summary.totals.estimated_cost_usd == Decimal("0.001000")
    assert len(summary.by_day) == 1
    assert summary.by_operation[0].operation == "chat_completion"

    kwargs = mock_aggregate.call_args.kwargs
    assert kwargs["workspace_id"] == workspace_id
    assert kwargs["end"] - kwargs["start"] == timedelta(days=7)


def test_get_workspace_summary_rejects_inverted_range(workspace_id) -> None:
    session = MagicMock()
    service = UsageService(session)
    start = datetime(2026, 7, 20, tzinfo=UTC)
    end = datetime(2026, 7, 10, tzinfo=UTC)

    with pytest.raises(InvalidUsageRangeError):
        service.get_workspace_summary(
            workspace_id=workspace_id,
            start=start,
            end=end,
        )
