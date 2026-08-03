"""Unit tests for Prometheus metrics helpers (OBS-006)."""

from unittest.mock import MagicMock

from app.modules.observability.metrics import (
    HTTP_ERRORS_TOTAL,
    HTTP_REQUESTS_TOTAL,
    INGESTION_DURATION_SECONDS,
    INGESTION_FAILURES_TOTAL,
    INGESTION_JOBS_TOTAL,
    LLM_CALLS_TOTAL,
    UNMATCHED_PATH_TEMPLATE,
    normalize_http_method,
    normalize_ingestion_error_type,
    observe_http_request,
    observe_ingestion_duration,
    observe_ingestion_failure,
    observe_ingestion_job,
    observe_llm_call,
    path_template_for_request,
    render_metrics,
    should_observe_http_path,
)


def _sample_value(metric_name: str, labels: dict[str, str]) -> float:
    body = render_metrics().decode("utf-8")
    label_parts = ",".join(f'{key}="{value}"' for key, value in sorted(labels.items()))
    needle = f"{metric_name}{{{label_parts}}} "
    for line in body.splitlines():
        if line.startswith(needle):
            return float(line.split()[-1])
    # Labels may appear in different order in exposition format.
    for line in body.splitlines():
        if not line.startswith(f"{metric_name}{{"):
            continue
        if all(f'{key}="{value}"' in line for key, value in labels.items()):
            return float(line.split()[-1])
    return 0.0


def test_required_counters_are_registered() -> None:
    body = render_metrics().decode("utf-8")

    assert "# HELP http_requests_total" in body
    assert "# TYPE http_requests_total counter" in body
    assert "# HELP http_errors_total" in body
    assert "# TYPE http_errors_total counter" in body
    assert "# HELP ingestion_jobs_total" in body
    assert "# TYPE ingestion_jobs_total counter" in body
    assert "# HELP ingestion_failures_total" in body
    assert "# TYPE ingestion_failures_total counter" in body
    assert "# HELP ingestion_duration_seconds" in body
    assert "# TYPE ingestion_duration_seconds histogram" in body
    assert "# HELP llm_calls_total" in body
    assert "# TYPE llm_calls_total counter" in body

    # Ensure metric objects are the module-level counters (import sanity).
    assert HTTP_REQUESTS_TOTAL._name == "http_requests"
    assert HTTP_ERRORS_TOTAL._name == "http_errors"
    assert INGESTION_JOBS_TOTAL._name == "ingestion_jobs"
    assert INGESTION_FAILURES_TOTAL._name == "ingestion_failures"
    assert INGESTION_DURATION_SECONDS._name == "ingestion_duration_seconds"
    assert LLM_CALLS_TOTAL._name == "llm_calls"


def test_observe_http_request_increments_request_and_error_counters() -> None:
    labels_ok = {
        "method": "GET",
        "path_template": "/health",
        "status": "200",
    }
    labels_err = {
        "method": "GET",
        "path_template": "/auth/me",
        "status": "401",
    }
    before_ok = _sample_value("http_requests_total", labels_ok)
    before_err_req = _sample_value("http_requests_total", labels_err)
    before_err = _sample_value("http_errors_total", labels_err)

    observe_http_request(method="GET", path_template="/health", status_code=200)
    observe_http_request(method="GET", path_template="/auth/me", status_code=401)

    assert _sample_value("http_requests_total", labels_ok) == before_ok + 1
    assert _sample_value("http_requests_total", labels_err) == before_err_req + 1
    assert _sample_value("http_errors_total", labels_err) == before_err + 1


def test_observe_ingestion_and_llm_helpers_increment() -> None:
    job_labels = {"status": "pending"}
    llm_labels = {"operation": "chat_completion", "status": "success"}
    before_job = _sample_value("ingestion_jobs_total", job_labels)
    before_llm = _sample_value("llm_calls_total", llm_labels)

    observe_ingestion_job(status="pending")
    observe_llm_call(operation="chat_completion", status="success")

    assert _sample_value("ingestion_jobs_total", job_labels) == before_job + 1
    assert _sample_value("llm_calls_total", llm_labels) == before_llm + 1


def test_observe_ingestion_failure_and_duration() -> None:
    failure_labels = {"error_type": "extraction"}
    before_failures = _sample_value("ingestion_failures_total", failure_labels)
    before_count = _sample_value(
        "ingestion_duration_seconds_count",
        {"status": "failed"},
    )

    observe_ingestion_failure(error_type="extraction")
    observe_ingestion_duration(status="failed", seconds=1.25)

    assert (
        _sample_value("ingestion_failures_total", failure_labels)
        == before_failures + 1
    )
    assert (
        _sample_value(
            "ingestion_duration_seconds_count",
            {"status": "failed"},
        )
        == before_count + 1
    )
    assert normalize_ingestion_error_type("not-a-real-type") == "unknown"


def test_path_template_prefers_route_template() -> None:
    request = MagicMock()
    request.scope = {"route": MagicMock(path="/workspaces/{workspace_id}/query")}
    request.url.path = "/workspaces/abc/query"

    assert path_template_for_request(request) == "/workspaces/{workspace_id}/query"


def test_path_template_unmatched_never_uses_raw_path() -> None:
    request = MagicMock()
    request.scope = {}
    request.url.path = "/totally/random/path-xyz-999"

    assert path_template_for_request(request) == UNMATCHED_PATH_TEMPLATE
    assert path_template_for_request(request) != request.url.path


def test_normalize_http_method_allowlist() -> None:
    assert normalize_http_method("get") == "GET"
    assert normalize_http_method("POST") == "POST"
    assert normalize_http_method("PROPFIND") == "OTHER"
    assert normalize_http_method("") == "OTHER"


def test_should_not_observe_metrics_path() -> None:
    assert should_observe_http_path("/health") is True
    assert should_observe_http_path("/metrics") is False
