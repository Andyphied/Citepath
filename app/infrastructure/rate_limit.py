"""In-memory rate limiting (single-process; not shared across replicas)."""

from __future__ import annotations

import time
from collections import defaultdict, deque
from threading import Lock


class RateLimitedError(Exception):
    """Raised when a client exceeds a configured request rate."""

    def __init__(self, retry_after: int) -> None:
        self.retry_after = retry_after
        super().__init__()


class InMemoryRateLimiter:
    """Fixed-window rate limiter keyed by client identifier (e.g. IP)."""

    def __init__(self, *, max_requests: int, window_seconds: int) -> None:
        self._max_requests = max_requests
        self._window_seconds = window_seconds
        self._requests: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def check(self, key: str) -> int | None:
        """Record a request; return retry-after seconds if limited."""
        now = time.monotonic()
        with self._lock:
            timestamps = self._requests[key]
            cutoff = now - self._window_seconds
            while timestamps and timestamps[0] <= cutoff:
                timestamps.popleft()
            if len(timestamps) >= self._max_requests:
                oldest = timestamps[0]
                retry_after = int(oldest + self._window_seconds - now) + 1
                return max(retry_after, 1)
            timestamps.append(now)
            return None

    def reset(self) -> None:
        """Clear all counters (test helper)."""
        with self._lock:
            self._requests.clear()


_login_rate_limiter = InMemoryRateLimiter(max_requests=10, window_seconds=60)


def check_login_rate_limit(client_ip: str) -> int | None:
    """Enforce 10 login attempts per minute per client IP."""
    return _login_rate_limiter.check(client_ip)


def reset_login_rate_limiter() -> None:
    """Reset login rate limiter state (tests only)."""
    _login_rate_limiter.reset()
