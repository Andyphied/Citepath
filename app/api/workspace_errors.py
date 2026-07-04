"""Workspace-related HTTP exception handlers."""

from fastapi import Request, status
from fastapi.responses import JSONResponse

from app.modules.workspaces.exceptions import (
    AlreadyMemberError,
    DuplicateSlugError,
    InvalidSlugError,
    LastOwnerError,
    MemberNotFoundError,
    UserNotFoundError,
    WorkspaceForbiddenError,
)


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


async def workspace_forbidden_handler(
    _request: Request,
    _exc: WorkspaceForbiddenError,
) -> JSONResponse:
    """Return 403 when the user is not a workspace member."""
    return JSONResponse(
        status_code=status.HTTP_403_FORBIDDEN,
        content={
            "error": {
                "code": "forbidden",
                "message": "You do not have permission to perform this action",
                "details": {},
            }
        },
    )


async def user_not_found_handler(
    _request: Request,
    _exc: UserNotFoundError,
) -> JSONResponse:
    """Return 404 when invite target email is not registered."""
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={
            "error": {
                "code": "user_not_found",
                "message": "No user exists with that email address",
                "details": {},
            }
        },
    )


async def already_member_handler(
    _request: Request,
    _exc: AlreadyMemberError,
) -> JSONResponse:
    """Return 409 when the user is already a workspace member."""
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={
            "error": {
                "code": "already_member",
                "message": "User is already a member of this workspace",
                "details": {},
            }
        },
    )


async def member_not_found_handler(
    _request: Request,
    _exc: MemberNotFoundError,
) -> JSONResponse:
    """Return 404 when the target user is not a workspace member."""
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={
            "error": {
                "code": "member_not_found",
                "message": "User is not a member of this workspace",
                "details": {},
            }
        },
    )


async def last_owner_handler(
    _request: Request,
    _exc: LastOwnerError,
) -> JSONResponse:
    """Return 400 when the operation would remove the last owner."""
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "error": {
                "code": "last_owner",
                "message": (
                    "Cannot remove or demote the last owner of the workspace"
                ),
                "details": {},
            }
        },
    )
