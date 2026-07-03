"""Unit tests for in-memory rate limiting."""

from app.infrastructure.rate_limit import InMemoryRateLimiter, RateLimitedError


def test_rate_limiter_allows_requests_up_to_limit() -> None:
    limiter = InMemoryRateLimiter(max_requests=3, window_seconds=60)

    assert limiter.check("127.0.0.1") is None
    assert limiter.check("127.0.0.1") is None
    assert limiter.check("127.0.0.1") is None


def test_rate_limiter_blocks_request_over_limit() -> None:
    limiter = InMemoryRateLimiter(max_requests=2, window_seconds=60)

    assert limiter.check("127.0.0.1") is None
    assert limiter.check("127.0.0.1") is None
    retry_after = limiter.check("127.0.0.1")

    assert retry_after is not None
    assert retry_after >= 1


def test_rate_limiter_tracks_keys_independently() -> None:
    limiter = InMemoryRateLimiter(max_requests=1, window_seconds=60)

    assert limiter.check("1.1.1.1") is None
    assert limiter.check("2.2.2.2") is None
    assert limiter.check("1.1.1.1") is not None
    assert limiter.check("2.2.2.2") is not None


def test_rate_limited_error_stores_retry_after() -> None:
    exc = RateLimitedError(42)

    assert exc.retry_after == 42
