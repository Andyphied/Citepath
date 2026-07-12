"""Unit tests for DocumentRepository pagination."""

from datetime import UTC, datetime
from unittest.mock import MagicMock
from uuid import uuid4

from app.infrastructure.db.enums import DocumentStatus
from app.modules.documents.models import Document
from app.modules.documents.repository import DocumentRepository


def _document(*, workspace_id, title: str, status: DocumentStatus) -> Document:
    return Document(
        id=uuid4(),
        workspace_id=workspace_id,
        uploaded_by=uuid4(),
        title=title,
        source_type="general",
        file_type="md",
        storage_key=f"{workspace_id}/doc/{title}",
        status=status,
        created_at=datetime(2026, 7, 12, tzinfo=UTC),
        updated_at=datetime(2026, 7, 12, tzinfo=UTC),
    )


def test_list_for_workspace_paginated_returns_page_and_total() -> None:
    workspace_id = uuid4()
    session = MagicMock()
    repository = DocumentRepository(session)

    documents = [
        _document(workspace_id=workspace_id, title=f"doc-{index}", status=DocumentStatus.INDEXED)
        for index in range(3)
    ]
    session.scalar.return_value = 5
    session.scalars.return_value.all.return_value = documents

    items, total = repository.list_for_workspace_paginated(
        workspace_id=workspace_id,
        page=2,
        page_size=2,
    )

    assert total == 5
    assert items == documents
    stmt = session.scalars.call_args.args[0]
    assert stmt._limit_clause.value == 2
    assert stmt._offset_clause.value == 2


def test_list_for_workspace_paginated_applies_status_filter() -> None:
    workspace_id = uuid4()
    session = MagicMock()
    repository = DocumentRepository(session)
    session.scalar.return_value = 1
    session.scalars.return_value.all.return_value = []

    repository.list_for_workspace_paginated(
        workspace_id=workspace_id,
        page=1,
        page_size=20,
        status=DocumentStatus.FAILED,
    )

    count_stmt = session.scalar.call_args.args[0]
    where_clauses = [clause for clause in count_stmt._where_criteria]
    assert any(
        getattr(clause.left, "key", None) == "status"
        for clause in where_clauses
    )
