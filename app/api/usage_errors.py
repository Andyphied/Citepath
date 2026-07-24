"""Usage-related HTTP exception handlers."""

from fastapi import Request, status

from app.modules.observability.errors import error_response
from app.modules.usage.exceptions import InvalidUsageRangeError


async def invalid_usage_range_handler(
    request: Request,
    _exc: InvalidUsageRangeError,
):
    """Return 422 when usage summary from/to is invalid."""
    return error_response(
        request=request,
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        code="invalid_usage_range",
        message="Query parameter 'from' must be earlier than 'to'",
    )
