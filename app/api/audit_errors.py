"""Audit-related HTTP exception handlers."""

from fastapi import Request, status

from app.modules.audit.exceptions import InvalidAuditRangeError
from app.modules.observability.errors import error_response


async def invalid_audit_range_handler(
    request: Request,
    _exc: InvalidAuditRangeError,
):
    """Return 422 when audit log from/to is invalid."""
    return error_response(
        request=request,
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        code="invalid_audit_range",
        message="Query parameter 'from' must be earlier than 'to'",
    )
