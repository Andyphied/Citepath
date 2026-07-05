"""Unit tests for standard API error helpers."""

import asyncio
from unittest.mock import MagicMock

import pytest
from fastapi.exceptions import RequestValidationError

from app.modules.observability.errors import (
    build_error_body,
    request_validation_exception_handler,
    unhandled_exception_handler,
    validation_details_from_errors,
)
from app.modules.observability.request_context import set_request_id


@pytest.fixture
def mock_request():
    request = MagicMock()
    request.state.request_id = "test-request-id-1234"
    request.url.path = "/test/path"
    request.method = "GET"
    return request


def test_build_error_body_includes_request_id_from_request(mock_request) -> None:
    body = build_error_body(
        code="validation_error",
        message="Request validation failed",
        details={"email": "invalid"},
        request=mock_request,
    )

    assert body == {
        "error": {
            "code": "validation_error",
            "message": "Request validation failed",
            "details": {"email": "invalid"},
            "request_id": "test-request-id-1234",
        }
    }


def test_validation_details_from_errors_maps_fields() -> None:
    errors = [
        {
            "loc": ("body", "password"),
            "msg": "String should have at least 8 characters",
            "type": "string_too_short",
        },
        {
            "loc": ("body", "email"),
            "msg": "value is not a valid email address",
            "type": "value_error",
        },
    ]

    details = validation_details_from_errors(errors)

    assert details["password"] == "String should have at least 8 characters"
    assert details["email"] == "value is not a valid email address"


def test_request_validation_exception_handler_returns_422(mock_request) -> None:
    exc = RequestValidationError(
        errors=[
            {
                "loc": ("body", "password"),
                "msg": "String should have at least 8 characters",
                "type": "string_too_short",
            }
        ]
    )

    response = asyncio.run(
        request_validation_exception_handler(mock_request, exc)
    )

    assert response.status_code == 422
    body = response.body.decode()
    assert '"code":"validation_error"' in body.replace(" ", "")
    assert "password" in body
    assert "test-request-id-1234" in body


def test_unhandled_exception_handler_returns_500_without_stack(
    mock_request,
) -> None:
    set_request_id("test-request-id-1234")

    response = asyncio.run(
        unhandled_exception_handler(
            mock_request,
            RuntimeError("secret internal detail"),
        )
    )

    assert response.status_code == 500
    body = response.body.decode()
    assert '"code":"internal_error"' in body.replace(" ", "")
    assert "secret" not in body
    assert "traceback" not in body.lower()
