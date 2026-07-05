"""FastAPI application factory."""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.auth_errors import (
    duplicate_email_handler,
    invalid_credentials_handler,
    rate_limited_handler,
    token_expired_handler,
    token_invalid_handler,
    unauthorized_handler,
)
from app.api.routes import auth, health, workspaces
from app.api.workspace_errors import (
    already_member_handler,
    duplicate_slug_handler,
    invalid_slug_handler,
    last_owner_handler,
    member_not_found_handler,
    user_not_found_handler,
    workspace_forbidden_handler,
)
from app.infrastructure.config import get_settings
from app.infrastructure.rate_limit import RateLimitedError
from app.modules.observability.logging import configure_logging
from app.modules.observability.middleware import RequestIdMiddleware
from app.modules.observability.request_logging import RequestLoggingMiddleware
from app.modules.auth.exceptions import (
    DuplicateEmailError,
    InvalidCredentialsError,
    TokenExpiredError,
    TokenInvalidError,
    UnauthorizedError,
)
from app.modules.workspaces.exceptions import (
    AlreadyMemberError,
    DuplicateSlugError,
    InvalidSlugError,
    LastOwnerError,
    MemberNotFoundError,
    UserNotFoundError,
    WorkspaceForbiddenError,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load and validate configuration on startup."""
    get_settings()
    yield


def create_app() -> FastAPI:
    """Create the FastAPI application with validated settings."""
    configure_logging()
    get_settings()
    app = FastAPI(
        title="AtlasOps AI",
        description="Workspace-scoped RAG and incident investigation platform",
        lifespan=lifespan,
    )
    # RequestLoggingMiddleware is inner; RequestIdMiddleware is outer (runs first on ingress).
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(RequestIdMiddleware)
    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(workspaces.router)
    app.add_exception_handler(DuplicateEmailError, duplicate_email_handler)
    app.add_exception_handler(InvalidCredentialsError, invalid_credentials_handler)
    app.add_exception_handler(RateLimitedError, rate_limited_handler)
    app.add_exception_handler(UnauthorizedError, unauthorized_handler)
    app.add_exception_handler(TokenExpiredError, token_expired_handler)
    app.add_exception_handler(TokenInvalidError, token_invalid_handler)
    app.add_exception_handler(DuplicateSlugError, duplicate_slug_handler)
    app.add_exception_handler(InvalidSlugError, invalid_slug_handler)
    app.add_exception_handler(WorkspaceForbiddenError, workspace_forbidden_handler)
    app.add_exception_handler(UserNotFoundError, user_not_found_handler)
    app.add_exception_handler(AlreadyMemberError, already_member_handler)
    app.add_exception_handler(MemberNotFoundError, member_not_found_handler)
    app.add_exception_handler(LastOwnerError, last_owner_handler)
    return app
