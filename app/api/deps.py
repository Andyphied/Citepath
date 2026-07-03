"""FastAPI dependencies."""

from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.infrastructure.config import Settings, get_settings
from app.infrastructure.db.session import get_db
from app.infrastructure.rate_limit import RateLimitedError, check_login_rate_limit
from app.modules.auth.repository import AuthRepository
from app.modules.auth.service import AuthService

DbSession = Annotated[Session, Depends(get_db)]


def get_settings_dep() -> Settings:
    """Provide application settings."""
    return get_settings()


SettingsDep = Annotated[Settings, Depends(get_settings_dep)]


def get_auth_service(
    db: DbSession,
    settings: SettingsDep,
) -> AuthService:
    """Provide AuthService with database session and settings."""
    return AuthService(AuthRepository(db), settings)


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]


def enforce_login_rate_limit(request: Request) -> None:
    """Reject login when the client IP exceeds 10 requests per minute."""
    client_ip = request.client.host if request.client else "unknown"
    retry_after = check_login_rate_limit(client_ip)
    if retry_after is not None:
        raise RateLimitedError(retry_after)


LoginRateLimitDep = Annotated[None, Depends(enforce_login_rate_limit)]
