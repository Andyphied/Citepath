"""Dependency probes for readiness checks."""

from __future__ import annotations

from typing import Any

from sqlalchemy import text

from app.infrastructure.config import get_settings
from app.infrastructure.db.session import get_engine

COMPONENT_OK = "ok"
COMPONENT_ERROR = "error"


def check_database() -> bool:
    """Return True if PostgreSQL accepts a simple query."""
    try:
        with get_engine().connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


def check_redis() -> bool:
    """Return True if Redis responds to PING."""
    try:
        import redis

        settings = get_settings()
        client = redis.from_url(
            settings.REDIS_URL,
            socket_connect_timeout=2,
            socket_timeout=2,
        )
        try:
            return bool(client.ping())
        finally:
            client.close()
    except Exception:
        return False


def get_celery_queue_depth() -> int | None:
    """Return Redis list length for the Celery default queue, or None on error."""
    try:
        import redis

        settings = get_settings()
        client = redis.from_url(
            settings.REDIS_URL,
            socket_connect_timeout=2,
            socket_timeout=2,
        )
        try:
            depth = client.llen(settings.CELERY_DEFAULT_QUEUE)
            return int(depth)
        finally:
            client.close()
    except Exception:
        return None


def readiness_payload() -> dict[str, Any]:
    """Build component status JSON for readiness (includes worker queue depth).

    ``worker.status`` reflects Redis queue probe success only — not Celery process
    liveness. When the probe fails, ``queue_depth`` is coerced to ``0`` (sentinel)
    with ``worker.status=error``; a true empty queue is ``0`` with ``status=ok``.
    """
    database_ok = check_database()
    redis_ok = check_redis()
    queue_depth = get_celery_queue_depth() if redis_ok else None
    worker_ok = redis_ok and queue_depth is not None
    overall_ok = database_ok and redis_ok
    return {
        "status": COMPONENT_OK if overall_ok else COMPONENT_ERROR,
        "database": COMPONENT_OK if database_ok else COMPONENT_ERROR,
        "redis": COMPONENT_OK if redis_ok else COMPONENT_ERROR,
        "queue_depth": queue_depth if queue_depth is not None else 0,
        "worker": {
            "status": COMPONENT_OK if worker_ok else COMPONENT_ERROR,
            "queue_depth": queue_depth if queue_depth is not None else 0,
        },
    }
