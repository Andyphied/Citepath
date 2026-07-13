"""API tests for structured request-completion logging."""

import json
import logging

import structlog
from fastapi.testclient import TestClient

from app.main import create_app
from app.modules.observability.request_context import REQUEST_ID_HEADER


def _reset_logging() -> None:
    structlog.reset_defaults()
    logging.root.handlers.clear()


def _parse_request_completion_log(captured_out: str) -> dict:
    """Return the request_completed log entry from captured stdout."""
    for line in reversed(captured_out.strip().split("\n")):
        if not line or not line.startswith("{"):
            continue
        entry = json.loads(line)
        if entry.get("message") == "request_completed":
            return entry
    raise AssertionError("No request_completed log line found in captured output")


def test_health_request_emits_structured_completion_log(minimal_env, capsys) -> None:
    _reset_logging()
    client = TestClient(create_app())
    client_id = "trace-logging-001"

    response = client.get("/health", headers={REQUEST_ID_HEADER: client_id})

    assert response.status_code == 200
    log_entry = _parse_request_completion_log(capsys.readouterr().out)
    assert log_entry["request_id"] == client_id
    assert log_entry["status_code"] == 200
    assert log_entry["level"] == "info"
    assert log_entry["message"] == "request_completed"
    assert log_entry["method"] == "GET"
    assert log_entry["path"] == "/health"
    assert isinstance(log_entry["duration_ms"], int)
    assert "timestamp" in log_entry


def test_error_response_emits_structured_completion_log(minimal_env, capsys) -> None:
    _reset_logging()
    client = TestClient(create_app())
    client_id = "trace-logging-401"

    response = client.get("/auth/me", headers={REQUEST_ID_HEADER: client_id})

    assert response.status_code == 401
    log_entry = _parse_request_completion_log(capsys.readouterr().out)
    assert log_entry["request_id"] == client_id
    assert log_entry["status_code"] == 401
    assert log_entry["path"] == "/auth/me"
