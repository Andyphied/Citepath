"""Liveness and readiness health checks."""

from fastapi import APIRouter, Response

from app.infrastructure.health_checks import COMPONENT_OK, readiness_payload

router = APIRouter(tags=["health"])


@router.get("/health")
def liveness() -> dict[str, str]:
    """Return 200 when the API process is running."""
    return {"status": "ok"}


@router.get("/health/ready")
def readiness(response: Response) -> dict[str, str]:
    """Return 200 when PostgreSQL and Redis are reachable; 503 otherwise."""
    payload = readiness_payload()
    if payload["status"] != COMPONENT_OK:
        response.status_code = 503
    return payload
