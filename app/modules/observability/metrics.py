"""Prometheus metrics registry and helpers (OBS-006 / OBS-005)."""

from __future__ import annotations

from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

HTTP_REQUESTS_TOTAL = Counter(
    "http_requests_total",
    "Total HTTP requests handled by the API",
    ["method", "path_template", "status"],
)

HTTP_ERRORS_TOTAL = Counter(
    "http_errors_total",
    "Total HTTP responses with status code >= 400",
    ["method", "path_template", "status"],
)

INGESTION_JOBS_TOTAL = Counter(
    "ingestion_jobs_total",
    "Total ingestion job status transitions",
    ["status"],
)

INGESTION_FAILURES_TOTAL = Counter(
    "ingestion_failures_total",
    "Total terminal ingestion job failures",
    ["error_type"],
)

INGESTION_DURATION_SECONDS = Histogram(
    "ingestion_duration_seconds",
    "Ingestion job attempt duration in seconds",
    ["status"],
    buckets=(0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0, 600.0),
)

LLM_CALLS_TOTAL = Counter(
    "llm_calls_total",
    "Total LLM and embedding provider calls",
    ["operation", "status"],
)

# Low-cardinality error_type allowlist for ingestion_failures_total.
_ALLOWED_INGESTION_ERROR_TYPES = frozenset(
    {
        "validation",
        "storage_read",
        "extraction",
        "embedding",
        "chunk_storage",
        "retries_exhausted",
        "unknown",
    }
)

METRICS_CONTENT_TYPE = CONTENT_TYPE_LATEST

# Paths excluded from HTTP request/error counters (scrape feedback loop).
_SKIP_HTTP_PATHS = frozenset({"/metrics"})

# Fixed label when no Starlette/FastAPI route template is bound (cardinality).
UNMATCHED_PATH_TEMPLATE = "unmatched"

_ALLOWED_HTTP_METHODS = frozenset(
    {"GET", "HEAD", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"}
)


def render_metrics() -> bytes:
    """Return Prometheus text exposition format for the default registry."""
    return generate_latest()


def path_template_for_request(request) -> str:
    """Prefer FastAPI/Starlette route template over raw path (cardinality)."""
    route = request.scope.get("route")
    template = getattr(route, "path", None) if route is not None else None
    if isinstance(template, str) and template:
        return template
    return UNMATCHED_PATH_TEMPLATE


def normalize_http_method(method: str) -> str:
    """Map request method to a small allowlist; everything else is OTHER."""
    upper = (method or "").upper()
    if upper in _ALLOWED_HTTP_METHODS:
        return upper
    return "OTHER"


def should_observe_http_path(path: str) -> bool:
    """Return False for scrape/self paths that should not inflate counters."""
    return path not in _SKIP_HTTP_PATHS


def observe_http_request(
    *,
    method: str,
    path_template: str,
    status_code: int,
) -> None:
    """Increment HTTP request (and error) counters for a completed response."""
    status = str(status_code)
    method_label = normalize_http_method(method)
    HTTP_REQUESTS_TOTAL.labels(
        method=method_label,
        path_template=path_template,
        status=status,
    ).inc()
    if status_code >= 400:
        HTTP_ERRORS_TOTAL.labels(
            method=method_label,
            path_template=path_template,
            status=status,
        ).inc()


def observe_ingestion_job(*, status: str) -> None:
    """Increment ingestion job counter for a status transition."""
    INGESTION_JOBS_TOTAL.labels(status=status).inc()


def normalize_ingestion_error_type(error_type: str) -> str:
    """Map failure class to a bounded Prometheus label."""
    if error_type in _ALLOWED_INGESTION_ERROR_TYPES:
        return error_type
    return "unknown"


def observe_ingestion_failure(*, error_type: str) -> None:
    """Increment terminal ingestion failure counter."""
    INGESTION_FAILURES_TOTAL.labels(
        error_type=normalize_ingestion_error_type(error_type),
    ).inc()


def observe_ingestion_duration(*, status: str, seconds: float) -> None:
    """Observe ingestion attempt duration for a terminal status."""
    if seconds < 0:
        return
    INGESTION_DURATION_SECONDS.labels(status=status).observe(seconds)


def observe_llm_call(*, operation: str, status: str) -> None:
    """Increment LLM/embedding call counter (no workspace labels)."""
    LLM_CALLS_TOTAL.labels(operation=operation, status=status).inc()
