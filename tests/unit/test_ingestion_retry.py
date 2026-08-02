"""Unit tests for ING-007 retryable vs permanent classification."""

from __future__ import annotations

import pytest

from app.modules.ingestion.retry import (
    INGESTION_MAX_RETRIES,
    RetryableIngestionError,
    is_retryable_exception,
    is_retryable_message,
    retry_countdown_seconds,
)


@pytest.mark.parametrize(
    ("message", "expected"),
    [
        ("Embedding generation failed after retry: provider timeout", True),
        ("APITimeoutError: Request timed out", True),
        ("connection refused by peer", True),
        ("Rate limit exceeded (429)", True),
        ("service temporarily unavailable", True),
        ("PDF contains no extractable text", False),
        ("no extractable text", False),
        ("Unsupported file type for extraction: docx", False),
        ("Encrypted PDF is not supported", False),
        ("Document has no storage key", False),
        ("Storage object not found: ws/doc/file.pdf", False),
        ("pgvector insert failed", False),
        ("", False),
    ],
)
def test_is_retryable_message_classification(message: str, expected: bool) -> None:
    assert is_retryable_message(message) is expected


def test_is_retryable_exception_for_timeout_and_connection() -> None:
    assert is_retryable_exception(TimeoutError("provider timeout")) is True
    assert is_retryable_exception(ConnectionError("connection reset")) is True
    assert is_retryable_exception(RetryableIngestionError("provider timeout")) is True
    assert is_retryable_exception(ValueError("PDF contains no extractable text")) is False
    assert is_retryable_exception(RuntimeError("vector shape mismatch")) is False


def test_retry_countdown_is_exponential_and_capped() -> None:
    assert retry_countdown_seconds(0) == 1
    assert retry_countdown_seconds(1) == 2
    assert retry_countdown_seconds(2) == 4
    assert retry_countdown_seconds(3) == 8
    assert retry_countdown_seconds(10) == 60


def test_ingestion_max_retries_is_three() -> None:
    assert INGESTION_MAX_RETRIES == 3
