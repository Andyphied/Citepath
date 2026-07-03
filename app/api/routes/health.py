"""Liveness health check (readiness deferred to OBS-001)."""

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
def liveness() -> dict[str, str]:
    """Return 200 when the API process is running."""
    return {"status": "ok"}
