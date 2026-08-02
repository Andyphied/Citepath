"""Retryable vs permanent failure classification for ingestion jobs (ING-007)."""

from __future__ import annotations

import re
from typing import Final

# Celery task-level retries after the in-batch embedding micro-retry.
INGESTION_MAX_RETRIES: Final[int] = 3
INGESTION_RETRY_BACKOFF_BASE_SECONDS: Final[int] = 2
INGESTION_RETRY_BACKOFF_MAX_SECONDS: Final[int] = 60

_RETRYABLE_EXCEPTION_NAMES: Final[frozenset[str]] = frozenset(
    {
        "APITimeoutError",
        "APIConnectionError",
        "RateLimitError",
        "InternalServerError",
        "ServiceUnavailableError",
        "Timeout",
        "TimeoutError",
        "ConnectTimeout",
        "ReadTimeout",
    }
)

_RETRYABLE_MESSAGE_PATTERN = re.compile(
    r"(timeout|timed out|connection (reset|refused|aborted|error)|"
    r"temporarily unavailable|rate limit|too many requests|\b429\b|\b503\b)",
    re.IGNORECASE,
)

_PERMANENT_MESSAGE_PATTERN = re.compile(
    r"(no extractable text|extracted text is empty|unsupported|"
    r"encrypted pdf|no pages|not valid utf-8|no storage key|"
    r"no file type|invalid storage key|storage key does not match|"
    r"object not found|file not found)",
    re.IGNORECASE,
)


class RetryableIngestionError(Exception):
    """Transient ingestion failure eligible for Celery autoretry."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


def is_retryable_exception(exc: BaseException) -> bool:
    """Return True when the exception represents a transient provider/network fault."""
    if isinstance(exc, RetryableIngestionError):
        return True
    if isinstance(exc, (TimeoutError, ConnectionError, ConnectionResetError, BrokenPipeError)):
        return True
    if type(exc).__name__ in _RETRYABLE_EXCEPTION_NAMES:
        return True
    return is_retryable_message(str(exc))


def is_retryable_message(message: str) -> bool:
    """Classify a failure message as retryable vs permanent."""
    if not message or not message.strip():
        return False
    if _PERMANENT_MESSAGE_PATTERN.search(message):
        return False
    return _RETRYABLE_MESSAGE_PATTERN.search(message) is not None


def retry_countdown_seconds(retries_so_far: int) -> int:
    """Exponential backoff: 2^n seconds, capped for MVP."""
    delay = INGESTION_RETRY_BACKOFF_BASE_SECONDS ** max(retries_so_far, 0)
    return min(delay, INGESTION_RETRY_BACKOFF_MAX_SECONDS)
