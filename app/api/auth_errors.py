"""Auth-related HTTP exception handlers."""

from fastapi import Request, status

from app.infrastructure.rate_limit import RateLimitedError
from app.modules.auth.exceptions import (
    DuplicateEmailError,
    InvalidCredentialsError,
    TokenExpiredError,
    TokenInvalidError,
    UnauthorizedError,
)
from app.modules.observability.errors import error_response


async def duplicate_email_handler(
    request: Request,
    _exc: DuplicateEmailError,
):
    """Return 409 when email is already registered."""
    return error_response(
        request=request,
        status_code=status.HTTP_409_CONFLICT,
        code="duplicate_email",
        message="A user with this email address is already registered",
    )


async def invalid_credentials_handler(
    request: Request,
    _exc: InvalidCredentialsError,
):
    """Return 401 for failed login without revealing whether the email exists."""
    return error_response(
        request=request,
        status_code=status.HTTP_401_UNAUTHORIZED,
        code="invalid_credentials",
        message="Invalid email or password",
    )


async def rate_limited_handler(
    request: Request,
    exc: RateLimitedError,
):
    """Return 429 when login rate limit is exceeded."""
    return error_response(
        request=request,
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        code="rate_limited",
        message="Too many login attempts. Please try again later.",
        headers={"Retry-After": str(exc.retry_after)},
    )


async def unauthorized_handler(
    request: Request,
    _exc: UnauthorizedError,
):
    """Return 401 when no Bearer token is provided."""
    return error_response(
        request=request,
        status_code=status.HTTP_401_UNAUTHORIZED,
        code="unauthorized",
        message="Authentication required",
    )


async def token_expired_handler(
    request: Request,
    _exc: TokenExpiredError,
):
    """Return 401 when the JWT has expired."""
    return error_response(
        request=request,
        status_code=status.HTTP_401_UNAUTHORIZED,
        code="token_expired",
        message="Access token has expired",
    )


async def token_invalid_handler(
    request: Request,
    _exc: TokenInvalidError,
):
    """Return 401 when the JWT is malformed or invalid."""
    return error_response(
        request=request,
        status_code=status.HTTP_401_UNAUTHORIZED,
        code="token_invalid",
        message="Invalid access token",
    )
