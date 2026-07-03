"""FastAPI application factory."""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.auth_errors import duplicate_email_handler
from app.api.routes import auth, health
from app.infrastructure.config import get_settings
from app.modules.auth.exceptions import DuplicateEmailError


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
    return app
