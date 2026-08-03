"""Unit tests for AdminService helpers and overview composition."""

from datetime import UTC, datetime
from unittest.mock import MagicMock
from uuid import uuid4

from app.infrastructure.db.enums import DocumentStatus, IngestionJobStatus
from app.modules.admin.service import AdminService, _preview
from app.modules.documents.models import Document
from app.modules.ingestion.models import IngestionJob


def test_preview_truncates_long_questions() -> None:
    short = "How do we restart?"
    assert _preview(short) == short
    long = "x" * 250
    result = _preview(long)
    assert result.endswith("…")
    assert len(result) == 201


def test_get_documents_overview_maps_counts(monkeypatch) -> None:
    workspace_id = uuid4()
    service = AdminService(MagicMock())
    now = datetime.now(UTC)
    doc = Document(
        id=uuid4(),
        workspace_id=workspace_id,
        uploaded_by=uuid4(),
        title="runbook.md",
        source_type="upload",
        file_type="md",
        storage_key="k",
        status=DocumentStatus.INDEXED,
        created_at=now,
        updated_at=now,
    )
    monkeypatch.setattr(
        service._documents,
        "count_by_status_for_workspace",
        lambda **_: {
            DocumentStatus.UPLOADED: 1,
            DocumentStatus.PROCESSING: 0,
            DocumentStatus.INDEXED: 2,
            DocumentStatus.FAILED: 1,
        },
    )
    monkeypatch.setattr(
        service._documents,
        "list_for_workspace_paginated",
        lambda **_: ([doc], 1),
    )

    overview = service.get_documents_overview(workspace_id=workspace_id)
    assert overview.total == 4
    assert overview.by_status.indexed == 2
    assert overview.by_status.failed == 1
    assert overview.recent_uploads[0].title == "runbook.md"
    assert overview.recent_uploads[0].status == "indexed"


def test_failed_jobs_widget_empty_message(monkeypatch) -> None:
    workspace_id = uuid4()
    service = AdminService(MagicMock())
    monkeypatch.setattr(
        service._ingestion_jobs,
        "count_failed_since",
        lambda **_: 0,
    )
    monkeypatch.setattr(
        service._ingestion_jobs,
        "list_for_workspace_paginated",
        lambda **_: ([], 0),
    )
    widget = service.get_failed_jobs_widget(workspace_id=workspace_id)
    assert widget.failed_last_24h == 0
    assert widget.failed_last_7d == 0
    assert widget.empty_message == "No failed jobs."
    assert widget.items == []


def test_list_ingestion_jobs_includes_document_title(monkeypatch) -> None:
    workspace_id = uuid4()
    document_id = uuid4()
    now = datetime.now(UTC)
    job = IngestionJob(
        id=uuid4(),
        workspace_id=workspace_id,
        document_id=document_id,
        status=IngestionJobStatus.FAILED,
        attempt_count=2,
        error_message="parse error",
        started_at=now,
        completed_at=now,
        created_at=now,
    )
    service = AdminService(MagicMock())
    monkeypatch.setattr(
        service._ingestion_jobs,
        "list_for_workspace_paginated",
        lambda **_: ([(job, "incident.md")], 1),
    )
    monkeypatch.setattr(
        service._ingestion_jobs,
        "count_by_status",
        lambda **_: 3,
    )
    result = service.list_ingestion_jobs(
        workspace_id=workspace_id,
        page=1,
        page_size=20,
        status=IngestionJobStatus.FAILED,
    )
    assert result.total == 1
    assert result.items[0].document_title == "incident.md"
    assert result.items[0].error_message == "parse error"
    assert result.items[0].status == "failed"
    assert result.pending_count == 3


def test_list_ingestion_jobs_sanitizes_error_message(monkeypatch) -> None:
    """Defense-in-depth: admin serialization re-sanitizes persisted errors."""
    workspace_id = uuid4()
    document_id = uuid4()
    now = datetime.now(UTC)
    path_bearing = (
        f"Storage object not found: /var/data/{workspace_id}/{document_id}/file.pdf"
    )
    job = IngestionJob(
        id=uuid4(),
        workspace_id=workspace_id,
        document_id=document_id,
        status=IngestionJobStatus.FAILED,
        attempt_count=1,
        error_message=path_bearing,
        started_at=now,
        completed_at=now,
        created_at=now,
    )
    service = AdminService(MagicMock())
    monkeypatch.setattr(
        service._ingestion_jobs,
        "list_for_workspace_paginated",
        lambda **_: ([(job, "file.pdf")], 1),
    )
    monkeypatch.setattr(
        service._ingestion_jobs,
        "count_by_status",
        lambda **_: 0,
    )
    result = service.list_ingestion_jobs(
        workspace_id=workspace_id,
        page=1,
        page_size=20,
        status=IngestionJobStatus.FAILED,
    )
    assert result.items[0].error_message == "Stored file could not be read"
    assert "/var/data" not in (result.items[0].error_message or "")
