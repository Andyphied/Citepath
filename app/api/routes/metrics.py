"""Prometheus metrics exposition endpoint."""

from fastapi import APIRouter, Response

from app.modules.observability.metrics import METRICS_CONTENT_TYPE, render_metrics

router = APIRouter(tags=["metrics"])


@router.get("/metrics")
def metrics() -> Response:
    """Expose Prometheus text format counters for internal scraping.

    Unauthenticated by design for MVP scrapers; restrict at the network edge.
    """
    return Response(content=render_metrics(), media_type=METRICS_CONTENT_TYPE)
