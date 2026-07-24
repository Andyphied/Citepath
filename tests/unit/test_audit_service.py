"""Unit tests for AuditService list filters and range validation."""

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from app.modules.audit.exceptions import InvalidAuditRangeError
from app.modules.audit.service import AuditService


def test_list_logs_passes_filters_to_repository() -> None:
    session = MagicMock()
    service = AuditService(session)
    workspace_id = uuid4()
    actor_id = uuid4()
    start = datetime(2026, 7, 1, tzinfo=UTC)
    end = datetime(2026, 7, 20, tzinfo=UTC)

    with patch.object(
        service._repository,
        "list_for_workspace",
        return_value=([], 0),
    ) as mock_list:
        result = service.list_logs(
            workspace_id=workspace_id,
            page=2,
            page_size=10,
            event_type="document.uploaded",
            actor_user_id=actor_id,
            start=start,
            end=end,
        )

    assert result.total == 0
    assert result.page == 2
    assert result.page_size == 10
    mock_list.assert_called_once_with(
        workspace_id=workspace_id,
        page=2,
        page_size=10,
        event_type="document.uploaded",
        actor_user_id=actor_id,
        start=start,
        end=end,
    )


def test_list_logs_rejects_inverted_range() -> None:
    service = AuditService(MagicMock())
    with pytest.raises(InvalidAuditRangeError):
        service.list_logs(
            workspace_id=uuid4(),
            page=1,
            page_size=20,
            start=datetime(2026, 7, 20, tzinfo=UTC),
            end=datetime(2026, 7, 10, tzinfo=UTC),
        )
