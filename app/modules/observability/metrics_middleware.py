"""HTTP middleware that increments Prometheus request counters."""

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.modules.observability.metrics import (
    observe_http_request,
    path_template_for_request,
    should_observe_http_path,
)


class MetricsMiddleware(BaseHTTPMiddleware):
    """Record http_requests_total / http_errors_total after each response."""

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        response = await call_next(request)
        if should_observe_http_path(request.url.path):
            observe_http_request(
                method=request.method,
                path_template=path_template_for_request(request),
                status_code=response.status_code,
            )
        return response
