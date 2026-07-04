"""Auth-related HTTP exception handlers."""

from fastapi import Request, status
from fastapi.responses import JSONResponse

from app.infrastructure.rate_limit import RateLimitedError
from app.modules.auth.exceptions import (
    DuplicateEmailError,
    InvalidCredentialsError,
    TokenExpiredError,
    TokenInvalidError,
    UnauthorizedError,
)


async def duplicate_email_handler(
    _request: Request,
    _exc: DuplicateEmailError,
) -> JSONResponse:
    """Return 409 when email is already registered."""
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={
            "error": {
                "code": "duplicate_email",
                "message": "A user with this email address is already registered",
                "details": {},
            }
        },
    )


async def invalid_credentials_handler(
    _request: Request,
    _exc: InvalidCredentialsError,
) -> JSONResponse:
    """Return 401 for failed login without revealing whether the email exists."""
    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={
            "error": {
                "code": "invalid_credentials",
                "message": "Invalid email or password",
                "details": {},
            }
        },
    )


async def rate_limited_handler(
    _request: Request,
    exc: RateLimitedError,
) -> JSONResponse:
    """Return 429 when login rate limit is exceeded."""
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={
            "error": {
                "code": "rate_limited",
                "message": "Too many login attempts. Please try again later.",
                "details": {},
            }
        },
        headers={"Retry-After": str(exc.retry_after)},
    )


async def unauthorized_handler(
    _request: Request,
    _exc: UnauthorizedError,
) -> JSONResponse:
    """Return 401 when no Bearer token is provided."""
    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={
            "error": {
                "code": "unauthorized",
                "message": "Authentication required",
                "details": {},
            }
        },
    )


async def token_expired_handler(
    _request: Request,
    _exc: TokenExpiredError,
) -> JSONResponse:
    """Return 401 when the JWT has expired."""
    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={
            "error": {
                "code": "token_expired",
                "message": "Access token has expired",
                "details": {},
            }
        },
    )


async def token_invalid_handler(
    _request: Request,
    _exc: TokenInvalidError,
) -> JSONResponse:
    """Return 401 when the JWT is malformed or invalid."""
    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={
            "error": {
                "code": "token_invalid",
                "message": "Invalid access token",
                "details": {},
            }
        },
    )
