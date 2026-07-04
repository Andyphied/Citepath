"""Unit tests for request ID context helpers."""

from unittest.mock import MagicMock

import pytest
from starlette.requests import Request

from app.modules.observability.request_context import (
    REQUEST_ID_HEADER,
    clear_request_id,
    get_request_id,
    get_request_id_from_request,
    is_valid_uuid,
    resolve_request_id,
    set_request_id,
)


def _make_request(headers: dict[str, str] | None = None) -> Request:
    raw_headers = []
    for key, value in (headers or {}).items():
        raw_headers.append((key.lower().encode(), value.encode()))
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/health",
        "headers": raw_headers,
    }
    return Request(scope)


def test_resolve_request_id_generates_uuid_when_header_absent() -> None:
    request_id = resolve_request_id(_make_request())

    assert is_valid_uuid(request_id)


def test_resolve_request_id_uses_client_header() -> None:
    client_id = "client-trace-abc123"
    request_id = resolve_request_id(
        _make_request({REQUEST_ID_HEADER: client_id}),
    )

    assert request_id == client_id


def test_resolve_request_id_ignores_blank_header() -> None:
    request_id = resolve_request_id(_make_request({REQUEST_ID_HEADER: "   "}))

    assert is_valid_uuid(request_id)


def test_resolve_request_id_ignores_overlong_header() -> None:
    request_id = resolve_request_id(
        _make_request({REQUEST_ID_HEADER: "x" * 129}),
    )

    assert is_valid_uuid(request_id)


def test_context_var_round_trip() -> None:
    set_request_id("ctx-123")
    assert get_request_id() == "ctx-123"
    clear_request_id()
    assert get_request_id() is None


def test_get_request_id_from_request_prefers_state() -> None:
    request = _make_request()
    request.state.request_id = "state-456"
    set_request_id("ctx-789")

    assert get_request_id_from_request(request) == "state-456"


def test_get_request_id_from_request_falls_back_to_context() -> None:
    request = MagicMock()
    request.state = MagicMock(spec=[])
    set_request_id("ctx-fallback")

    assert get_request_id_from_request(request) == "ctx-fallback"

    clear_request_id()


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("550e8400-e29b-41d4-a716-446655440000", True),
        ("not-a-uuid", False),
    ],
)
def test_is_valid_uuid(value: str, expected: bool) -> None:
    assert is_valid_uuid(value) is expected
