"""Workspace-related HTTP exception handlers."""

from fastapi import Request, status
from fastapi.responses import JSONResponse

from app.modules.workspaces.exceptions import DuplicateSlugError, InvalidSlugError


async def duplicate_slug_handler(
    _request: Request,
    _exc: DuplicateSlugError,
) -> JSONResponse:
    """Return 409 when workspace slug is already taken."""
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={
            "error": {
                "code": "duplicate_slug",
                "message": "A workspace with this slug already exists",
                "details": {},
            }
        },
    )


async def invalid_slug_handler(
    _request: Request,
    _exc: InvalidSlugError,
) -> JSONResponse:
    """Return 422 when workspace slug format is invalid."""
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "code": "invalid_slug",
                "message": (
                    "Slug must contain only lowercase letters, numbers, and hyphens"
                ),
                "details": {},
            }
        },
    )
