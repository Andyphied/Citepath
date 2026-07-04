"""Dependency probes for readiness checks."""

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


def readiness_payload() -> dict[str, str]:
    """Build component status JSON for readiness."""
    database_ok = check_database()
    redis_ok = check_redis()
    overall_ok = database_ok and redis_ok
    return {
        "status": COMPONENT_OK if overall_ok else COMPONENT_ERROR,
        "database": COMPONENT_OK if database_ok else COMPONENT_ERROR,
        "redis": COMPONENT_OK if redis_ok else COMPONENT_ERROR,
    }
