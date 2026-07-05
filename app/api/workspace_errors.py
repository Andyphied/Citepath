"""Workspace-related HTTP exception handlers."""

from fastapi import Request, status

from app.modules.observability.errors import error_response
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
    request: Request,
    _exc: DuplicateSlugError,
):
    """Return 409 when workspace slug is already taken."""
    return error_response(
        request=request,
        status_code=status.HTTP_409_CONFLICT,
        code="duplicate_slug",
        message="A workspace with this slug already exists",
    )


async def invalid_slug_handler(
    request: Request,
    _exc: InvalidSlugError,
):
    """Return 422 when workspace slug format is invalid."""
    return error_response(
        request=request,
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        code="invalid_slug",
        message=(
            "Slug must contain only lowercase letters, numbers, and hyphens"
        ),
    )


async def workspace_forbidden_handler(
    request: Request,
    _exc: WorkspaceForbiddenError,
):
    """Return 403 when the user is not a workspace member."""
    return error_response(
        request=request,
        status_code=status.HTTP_403_FORBIDDEN,
        code="forbidden",
        message="You do not have permission to perform this action",
    )


async def user_not_found_handler(
    request: Request,
    _exc: UserNotFoundError,
):
    """Return 404 when invite target email is not registered."""
    return error_response(
        request=request,
        status_code=status.HTTP_404_NOT_FOUND,
        code="user_not_found",
        message="No user exists with that email address",
    )


async def already_member_handler(
    request: Request,
    _exc: AlreadyMemberError,
):
    """Return 409 when the user is already a workspace member."""
    return error_response(
        request=request,
        status_code=status.HTTP_409_CONFLICT,
        code="already_member",
        message="User is already a member of this workspace",
    )


async def member_not_found_handler(
    request: Request,
    _exc: MemberNotFoundError,
):
    """Return 404 when the target user is not a workspace member."""
    return error_response(
        request=request,
        status_code=status.HTTP_404_NOT_FOUND,
        code="member_not_found",
        message="User is not a member of this workspace",
    )


async def last_owner_handler(
    request: Request,
    _exc: LastOwnerError,
):
    """Return 400 when the operation would remove the last owner."""
    return error_response(
        request=request,
        status_code=status.HTTP_400_BAD_REQUEST,
        code="last_owner",
        message="Cannot remove or demote the last owner of the workspace",
    )
