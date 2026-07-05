"""Standard API error envelope and global exception handlers."""

from __future__ import annotations

from typing import Any

from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.modules.observability.logging import get_logger
from app.modules.observability.request_context import (
    get_request_id_from_request,
)

logger = get_logger(__name__)

_LOC_PREFIXES = frozenset({"body", "query", "path", "header", "cookie"})


def build_error_body(
    *,
    code: str,
    message: str,
    details: dict[str, Any] | None = None,
    request: Request | None = None,
) -> dict[str, Any]:
    """Build standard `{ error: { code, message, details, request_id } }`."""
    request_id = (
        get_request_id_from_request(request) if request is not None else None
    )
    return {
        "error": {
            "code": code,
            "message": message,
            "details": details or {},
            "request_id": request_id,
        }
    }


def error_response(
    *,
    status_code: int,
    code: str,
    message: str,
    details: dict[str, Any] | None = None,
    request: Request | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    """Return a JSONResponse using the standard error envelope."""
    return JSONResponse(
        status_code=status_code,
        content=build_error_body(
            code=code,
            message=message,
            details=details,
            request=request,
        ),
        headers=headers,
    )


def validation_details_from_errors(
    errors: list[dict[str, Any]],
) -> dict[str, str]:
    """Map FastAPI/Pydantic validation errors to field -> reason details."""
    details: dict[str, str] = {}
    for error in errors:
        loc = error.get("loc", ())
        parts = [str(part) for part in loc if part not in _LOC_PREFIXES]
        field = ".".join(parts) if parts else "request"
        msg = str(error.get("msg", "Invalid value"))
        if field in details:
            details[field] = f"{details[field]}; {msg}"
        else:
            details[field] = msg
    return details


async def request_validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    """Return 422 with structured validation error and field details."""
    return error_response(
        request=request,
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        code="validation_error",
        message="Request validation failed",
        details=validation_details_from_errors(exc.errors()),
    )


async def unhandled_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    """Return generic 500 and log full stack trace server-side."""
    request_id = get_request_id_from_request(request)
    logger.exception(
        "unhandled_exception",
        request_id=request_id,
        path=request.url.path,
        method=request.method,
        exc_type=type(exc).__name__,
    )
    return error_response(
        request=request,
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        code="internal_error",
        message="An internal server error occurred",
        details={},
    )
