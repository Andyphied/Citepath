"""HTTP middleware for request ID propagation."""

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.modules.observability.request_context import (
    REQUEST_ID_HEADER,
    clear_request_id,
    resolve_request_id,
    set_request_id,
)


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Assign a request ID and return it on every HTTP response."""

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        request_id = resolve_request_id(request)
        request.state.request_id = request_id
        set_request_id(request_id)
        try:
            response = await call_next(request)
        finally:
            clear_request_id()
        response.headers[REQUEST_ID_HEADER] = request_id
        return response
