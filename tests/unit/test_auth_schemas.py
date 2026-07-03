"""Unit tests for auth request schemas."""

import pytest
from pydantic import ValidationError

from app.modules.auth.schemas import RegisterRequest


def test_register_request_normalizes_email() -> None:
    request = RegisterRequest(email="User@Example.COM", password="password123")

    assert request.email == "user@example.com"


def test_register_request_rejects_short_password() -> None:
    with pytest.raises(ValidationError) as exc_info:
        RegisterRequest(email="user@example.com", password="short")

    errors = exc_info.value.errors()
    assert any(error["loc"] == ("password",) for error in errors)


def test_register_request_rejects_long_password() -> None:
    with pytest.raises(ValidationError) as exc_info:
        RegisterRequest(email="user@example.com", password="a" * 129)

    errors = exc_info.value.errors()
    assert any(error["loc"] == ("password",) for error in errors)


def test_register_request_rejects_invalid_email() -> None:
    with pytest.raises(ValidationError):
        RegisterRequest(email="not-an-email", password="password123")


def test_register_request_accepts_optional_name() -> None:
    request = RegisterRequest(
        email="user@example.com",
        password="password123",
        name="Jane Doe",
    )

    assert request.name == "Jane Doe"
