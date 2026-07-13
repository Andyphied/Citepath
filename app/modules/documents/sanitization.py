"""Sanitize ingestion error messages for client-facing APIs."""

import re

_STORAGE_NOT_FOUND_PREFIX = "Storage object not found:"
_INVALID_STORAGE_KEY_PREFIX = "Invalid storage key:"
_STORAGE_KEY_PATTERN = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/",
    re.IGNORECASE,
)


def sanitize_ingestion_error_message(message: str | None) -> str | None:
    """Return a client-safe ingestion error message without storage paths."""
    if message is None:
        return None

    trimmed = message.strip()
    if not trimmed:
        return None
    if trimmed.startswith(_STORAGE_NOT_FOUND_PREFIX):
        return "Stored file could not be read"
    if trimmed.startswith(_INVALID_STORAGE_KEY_PREFIX):
        return "Invalid stored file reference"
    if _STORAGE_KEY_PATTERN.search(trimmed):
        return "Document ingestion failed"
    return trimmed
