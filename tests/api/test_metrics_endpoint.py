"""API tests for GET /metrics (OBS-006)."""

from fastapi.testclient import TestClient

from app.main import create_app
from app.modules.observability.metrics import UNMATCHED_PATH_TEMPLATE, render_metrics


def _sample_value(metric_name: str, labels: dict[str, str]) -> float:
    body = render_metrics().decode("utf-8")
    for line in body.splitlines():
        if not line.startswith(f"{metric_name}{{"):
            continue
        if all(f'{key}="{value}"' in line for key, value in labels.items()):
            return float(line.split()[-1])
    return 0.0


def test_metrics_endpoint_returns_prometheus_text(minimal_env) -> None:
    client = TestClient(create_app())

    response = client.get("/metrics")

    assert response.status_code == 200
    assert "text/plain" in response.headers["content-type"]
    body = response.text
    assert "http_requests_total" in body
    assert "http_errors_total" in body
    assert "ingestion_jobs_total" in body
    assert "llm_calls_total" in body


def test_http_request_increments_on_traffic(minimal_env) -> None:
    client = TestClient(create_app())
    labels = {
        "method": "GET",
        "path_template": "/health",
        "status": "200",
    }
    before = _sample_value("http_requests_total", labels)

    health = client.get("/health")
    assert health.status_code == 200

    after = _sample_value("http_requests_total", labels)
    assert after == before + 1

    scrape = client.get("/metrics")
    assert scrape.status_code == 200
    assert 'http_requests_total{method="GET",path_template="/health",status="200"}' in (
        scrape.text
    ) or all(
        part in scrape.text
        for part in (
            "http_requests_total{",
            'method="GET"',
            'path_template="/health"',
            'status="200"',
        )
    )


def test_http_error_increments_on_unauthorized(minimal_env) -> None:
    client = TestClient(create_app())
    labels = {
        "method": "GET",
        "path_template": "/auth/me",
        "status": "401",
    }
    before_req = _sample_value("http_requests_total", labels)
    before_err = _sample_value("http_errors_total", labels)

    response = client.get("/auth/me")
    assert response.status_code == 401

    assert _sample_value("http_requests_total", labels) == before_req + 1
    assert _sample_value("http_errors_total", labels) == before_err + 1


def test_metrics_scrape_does_not_increment_http_counters(minimal_env) -> None:
    client = TestClient(create_app())
    labels = {
        "method": "GET",
        "path_template": "/metrics",
        "status": "200",
    }
    before = _sample_value("http_requests_total", labels)

    client.get("/metrics")
    client.get("/metrics")

    assert _sample_value("http_requests_total", labels) == before


def test_unmatched_path_uses_fixed_path_template_label(minimal_env) -> None:
    client = TestClient(create_app())
    raw_path = "/no-such-route-obs006-xyz-4242"
    labels = {
        "method": "GET",
        "path_template": UNMATCHED_PATH_TEMPLATE,
        "status": "404",
    }
    before_req = _sample_value("http_requests_total", labels)
    before_err = _sample_value("http_errors_total", labels)

    response = client.get(raw_path)
    assert response.status_code == 404

    assert _sample_value("http_requests_total", labels) == before_req + 1
    assert _sample_value("http_errors_total", labels) == before_err + 1

    scrape = client.get("/metrics")
    assert scrape.status_code == 200
    assert f'path_template="{raw_path}"' not in scrape.text
    assert f'path_template="{UNMATCHED_PATH_TEMPLATE}"' in scrape.text
