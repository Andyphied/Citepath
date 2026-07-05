"""HTTP middleware for structured request-completion logging."""

import time

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.modules.observability.logging import get_logger
from app.modules.observability.request_context import get_request_id_from_request


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Emit one structured JSON log line when an API request completes."""

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - start) * 1000)

        user_id = getattr(request.state, "user_id", None)
        workspace_id = getattr(request.state, "workspace_id", None)

        get_logger(__name__).info(
            "request_completed",
            request_id=get_request_id_from_request(request),
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=duration_ms,
            user_id=str(user_id) if user_id is not None else None,
            workspace_id=str(workspace_id) if workspace_id is not None else None,
        )
        return response
