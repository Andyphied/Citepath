"""API tests for standard error envelope (OBS-004)."""

from fastapi.testclient import TestClient

from app.main import create_app
from app.modules.observability.request_context import (
    REQUEST_ID_HEADER,
    is_valid_uuid,
)


def test_validation_error_returns_structured_envelope(minimal_env) -> None:
    client = TestClient(create_app())

    response = client.post(
        "/auth/register",
        json={
            "email": "user@example.com",
            "password": "short",
        },
    )

    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "validation_error"
    assert body["error"]["message"] == "Request validation failed"
    assert "password" in body["error"]["details"]
    assert body["error"]["request_id"]
    assert is_valid_uuid(body["error"]["request_id"])
    assert REQUEST_ID_HEADER in response.headers


def test_domain_error_includes_request_id_in_body(minimal_env) -> None:
    client = TestClient(create_app())

    response = client.get("/auth/me")

    assert response.status_code == 401
    body = response.json()
    assert body["error"]["code"] == "unauthorized"
    assert body["error"]["request_id"]
    assert is_valid_uuid(body["error"]["request_id"])
    assert response.headers[REQUEST_ID_HEADER] == body["error"]["request_id"]


def test_unhandled_exception_returns_generic_500_envelope(minimal_env) -> None:
    app = create_app()

    @app.get("/test-internal-error")
    def _raise_internal_error() -> None:
        raise RuntimeError("secret internal detail")

    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/test-internal-error")

    assert response.status_code == 500
    body = response.json()
    assert body["error"]["code"] == "internal_error"
    assert body["error"]["message"] == "An internal server error occurred"
    assert body["error"]["details"] == {}
    assert body["error"]["request_id"]
    assert is_valid_uuid(body["error"]["request_id"])
    assert "secret" not in str(body)
    assert "traceback" not in str(body).lower()
