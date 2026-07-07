"""Shared helpers for ingestion pipeline steps."""

MAX_ERROR_MESSAGE_LENGTH = 2048


def truncate_error_message(message: str) -> str:
    """Truncate failure messages to the ingestion job storage limit."""
    if len(message) <= MAX_ERROR_MESSAGE_LENGTH:
        return message
    return message[: MAX_ERROR_MESSAGE_LENGTH - 3] + "..."
