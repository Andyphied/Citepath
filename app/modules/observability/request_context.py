"""Request ID context for log and error correlation."""

from contextvars import ContextVar
from uuid import UUID, uuid4

from starlette.requests import Request

REQUEST_ID_HEADER = "X-Request-ID"
MAX_REQUEST_ID_LENGTH = 128

_request_id_ctx: ContextVar[str | None] = ContextVar("request_id", default=None)


def set_request_id(request_id: str) -> None:
    """Bind request_id to the current async context."""
    _request_id_ctx.set(request_id)


def clear_request_id() -> None:
    """Clear request_id from the current async context."""
    _request_id_ctx.set(None)


def get_request_id() -> str | None:
    """Return the current request ID from context (middleware-scoped)."""
    return _request_id_ctx.get()


def resolve_request_id(request: Request) -> str:
    """Read client header or generate a new UUID4."""
    client_id = request.headers.get(REQUEST_ID_HEADER)
    if client_id is not None:
        client_id = client_id.strip()
        if client_id and len(client_id) <= MAX_REQUEST_ID_LENGTH:
            return client_id
    return str(uuid4())


def get_request_id_from_request(request: Request) -> str | None:
    """Return request ID from request state or async context."""
    state_id = getattr(request.state, "request_id", None)
    if state_id:
        return state_id
    return get_request_id()


def is_valid_uuid(value: str) -> bool:
    """Return True when value is a valid UUID string."""
    try:
        UUID(value)
    except ValueError:
        return False
    return True
