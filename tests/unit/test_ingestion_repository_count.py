"""Unit tests for ingestion chunk count queries."""

from unittest.mock import MagicMock
from uuid import uuid4

from app.modules.ingestion.repository import IngestionRepository


def test_count_chunks_for_document_returns_scalar_count() -> None:
    workspace_id = uuid4()
    document_id = uuid4()
    session = MagicMock()
    session.scalar.return_value = 7
    repository = IngestionRepository(session)

    result = repository.count_chunks_for_document(
        workspace_id=workspace_id,
        document_id=document_id,
    )

    assert result == 7
    session.scalar.assert_called_once()
