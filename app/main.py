"""FastAPI application factory."""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.auth_errors import (
    duplicate_email_handler,
    invalid_credentials_handler,
    rate_limited_handler,
)
from app.api.routes import auth, health
from app.infrastructure.config import get_settings
from app.infrastructure.rate_limit import RateLimitedError
from app.modules.auth.exceptions import DuplicateEmailError, InvalidCredentialsError


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
    app.add_exception_handler(DuplicateEmailError, duplicate_email_handler)
    app.add_exception_handler(InvalidCredentialsError, invalid_credentials_handler)
    app.add_exception_handler(RateLimitedError, rate_limited_handler)
    return app
