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
from app.api.workspace_errors import duplicate_slug_handler, invalid_slug_handler
from app.infrastructure.config import get_settings
from app.infrastructure.rate_limit import RateLimitedError
from app.modules.auth.exceptions import (
    DuplicateEmailError,
    InvalidCredentialsError,
    TokenExpiredError,
    TokenInvalidError,
    UnauthorizedError,
)
from app.modules.workspaces.exceptions import DuplicateSlugError, InvalidSlugError


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load and validate configuration on startup."""
    get_settings()
    yield


def create_app() -> FastAPI:
    """Create the FastAPI application with validated settings."""
    get_settings()
    app = FastAPI(
        title="AtlasOps AI",
        description="Workspace-scoped RAG and incident investigation platform",
        lifespan=lifespan,
    )
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
    return app
