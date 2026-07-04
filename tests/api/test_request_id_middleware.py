"""API tests for request ID middleware."""

from fastapi.testclient import TestClient

from app.main import create_app
from app.modules.observability.request_context import (
    REQUEST_ID_HEADER,
    is_valid_uuid,
)


def test_health_response_includes_request_id_header(minimal_env) -> None:
    client = TestClient(create_app())

    response = client.get("/health")

    assert response.status_code == 200
    assert REQUEST_ID_HEADER in response.headers
    assert is_valid_uuid(response.headers[REQUEST_ID_HEADER])


def test_health_ready_response_includes_request_id_header(minimal_env) -> None:
    client = TestClient(create_app())

    response = client.get("/health/ready")

    assert REQUEST_ID_HEADER in response.headers
    assert response.headers[REQUEST_ID_HEADER]


def test_client_provided_request_id_is_echoed(minimal_env) -> None:
    client = TestClient(create_app())
    client_id = "upstream-trace-id-001"

    response = client.get("/health", headers={REQUEST_ID_HEADER: client_id})

    assert response.headers[REQUEST_ID_HEADER] == client_id


def test_error_response_includes_request_id_header(minimal_env) -> None:
    client = TestClient(create_app())

    response = client.get("/auth/me")

    assert response.status_code == 401
    assert REQUEST_ID_HEADER in response.headers
    assert is_valid_uuid(response.headers[REQUEST_ID_HEADER])
