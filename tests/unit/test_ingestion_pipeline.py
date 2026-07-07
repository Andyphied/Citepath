"""Unit tests for ingestion pipeline helpers."""

from app.modules.ingestion.pipeline import MAX_ERROR_MESSAGE_LENGTH, truncate_error_message


def test_truncate_error_message_returns_short_messages_unchanged() -> None:
    message = "extraction failed"

    assert truncate_error_message(message) == message


def test_truncate_error_message_limits_long_messages() -> None:
    message = "x" * (MAX_ERROR_MESSAGE_LENGTH + 50)

    truncated = truncate_error_message(message)

    assert len(truncated) == MAX_ERROR_MESSAGE_LENGTH
    assert truncated.endswith("...")
