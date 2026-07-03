"""Auth-related HTTP exception handlers."""

from fastapi import Request, status
from fastapi.responses import JSONResponse

from app.modules.auth.exceptions import DuplicateEmailError


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
