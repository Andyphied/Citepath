"""Unit tests for client-facing ingestion error sanitization."""

from uuid import uuid4

from app.modules.documents.sanitization import sanitize_ingestion_error_message


def test_sanitize_returns_none_for_empty_message() -> None:
    assert sanitize_ingestion_error_message(None) is None
    assert sanitize_ingestion_error_message("   ") is None


def test_sanitize_maps_storage_not_found_message() -> None:
    workspace_id = uuid4()
    document_id = uuid4()
    message = f"Storage object not found: {workspace_id}/{document_id}/runbook.md"

    assert sanitize_ingestion_error_message(message) == "Stored file could not be read"


def test_sanitize_maps_invalid_storage_key_message() -> None:
    assert (
        sanitize_ingestion_error_message("Invalid storage key: ../../etc/passwd")
        == "Invalid stored file reference"
    )


def test_sanitize_redacts_embedded_storage_key_pattern() -> None:
    workspace_id = uuid4()
    document_id = uuid4()
    message = f"Unexpected failure at {workspace_id}/{document_id}/secret.txt"

    assert sanitize_ingestion_error_message(message) == "Document ingestion failed"


def test_sanitize_preserves_safe_technical_messages() -> None:
    assert sanitize_ingestion_error_message("PDF contains no pages") == "PDF contains no pages"
