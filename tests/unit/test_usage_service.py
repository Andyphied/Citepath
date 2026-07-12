"""Unit tests for usage event logging."""

from decimal import Decimal
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from app.infrastructure.db.enums import UsageEventStatus, UsageOperation
from app.modules.usage.service import UsageEventInput, UsageService


@pytest.fixture
def workspace_id():
    return uuid4()


def test_usage_service_logs_embedding_event(workspace_id) -> None:
    session = MagicMock()
    service = UsageService(session)

    with patch.object(service._repository, "create") as mock_create:
        service.log_event(
            UsageEventInput(
                workspace_id=workspace_id,
                user_id=None,
                provider="openai",
                model="text-embedding-3-small",
                operation=UsageOperation.EMBEDDING,
                embedding_tokens=120,
                latency_ms=45,
                status=UsageEventStatus.SUCCESS,
                metadata={"document_id": "doc-1", "job_id": "job-1"},
            )
        )

    mock_create.assert_called_once()
    kwargs = mock_create.call_args.kwargs
    assert kwargs["workspace_id"] == workspace_id
    assert kwargs["user_id"] is None
    assert kwargs["operation"] == UsageOperation.EMBEDDING
    assert kwargs["embedding_tokens"] == 120
    assert kwargs["estimated_cost_usd"] == Decimal("0.0000024")


def test_usage_service_swallows_repository_errors(workspace_id) -> None:
    session = MagicMock()
    service = UsageService(session)

    with patch.object(
        service._repository,
        "create",
        side_effect=RuntimeError("db unavailable"),
    ):
        service.log_event(
            UsageEventInput(
                workspace_id=workspace_id,
                user_id=None,
                provider="openai",
                model="text-embedding-3-small",
                operation=UsageOperation.EMBEDDING,
                embedding_tokens=10,
            )
        )

    session.rollback.assert_called_once()
