"""Unit tests for document status enum, labels, and response mapping."""

from datetime import datetime
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from app.infrastructure.db.enums import DocumentStatus
from app.modules.documents.schemas import DocumentResponse


@pytest.mark.parametrize(
    ("status", "expected_label"),
    [
        (DocumentStatus.UPLOADED, "Uploaded"),
        (DocumentStatus.PROCESSING, "Processing"),
        (DocumentStatus.INDEXED, "Indexed"),
        (DocumentStatus.FAILED, "Failed"),
    ],
)
def test_document_status_label(status: DocumentStatus, expected_label: str) -> None:
    assert status.label == expected_label


@pytest.mark.parametrize(
    ("status", "expected_value", "expected_label"),
    [
        (DocumentStatus.UPLOADED, "uploaded", "Uploaded"),
        (DocumentStatus.PROCESSING, "processing", "Processing"),
        (DocumentStatus.INDEXED, "indexed", "Indexed"),
        (DocumentStatus.FAILED, "failed", "Failed"),
    ],
)
def test_document_response_from_document_maps_status_and_label(
    status: DocumentStatus,
    expected_value: str,
    expected_label: str,
) -> None:
    document = MagicMock()
    document.id = uuid4()
    document.workspace_id = uuid4()
    document.title = "runbook.md"
    document.source_type = "general"
    document.file_type = "md"
    document.status = status
    document.uploaded_by = uuid4()
    document.created_at = datetime.fromisoformat("2026-07-07T00:00:00+00:00")
    document.updated_at = datetime.fromisoformat("2026-07-07T00:00:00+00:00")

    response = DocumentResponse.from_document(document)

    assert response.status == expected_value
    assert response.status_label == expected_label


def test_document_status_worker_transition_order() -> None:
    """Document lifecycle order exercised by the ingestion worker."""
    expected_order = [
        DocumentStatus.UPLOADED,
        DocumentStatus.PROCESSING,
        DocumentStatus.INDEXED,
    ]
    labels = [status.label for status in expected_order]
    assert labels == ["Uploaded", "Processing", "Indexed"]

    failure_path = [DocumentStatus.UPLOADED, DocumentStatus.PROCESSING, DocumentStatus.FAILED]
    failure_labels = [status.label for status in failure_path]
    assert failure_labels == ["Uploaded", "Processing", "Failed"]
