"""FastAPI dependencies."""

from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.infrastructure.config import Settings, get_settings
from app.infrastructure.db.session import get_db
from app.infrastructure.rate_limit import (
    RateLimitedError,
    check_login_rate_limit,
)
from app.modules.auth.exceptions import TokenInvalidError, UnauthorizedError
from app.modules.auth.jwt import decode_access_token
from app.modules.auth.repository import AuthRepository
from app.modules.auth.service import AuthService
from app.modules.users.models import User
from app.modules.users.repository import UserRepository
from app.modules.workspaces.repository import WorkspaceRepository
from app.modules.workspaces.service import WorkspaceService

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


def get_workspace_service(db: DbSession) -> WorkspaceService:
    """Provide WorkspaceService with database session."""
    return WorkspaceService(WorkspaceRepository(db))


WorkspaceServiceDep = Annotated[WorkspaceService, Depends(get_workspace_service)]


def enforce_login_rate_limit(request: Request) -> None:
    """Reject login when the client IP exceeds 10 requests per minute."""
    client_ip = request.client.host if request.client else "unknown"
    retry_after = check_login_rate_limit(client_ip)
    if retry_after is not None:
        raise RateLimitedError(retry_after)


LoginRateLimitDep = Annotated[None, Depends(enforce_login_rate_limit)]

_bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(_bearer_scheme),
    ],
    db: DbSession,
    settings: SettingsDep,
) -> User:
    """Validate Bearer JWT and return the authenticated user."""
    if credentials is None:
        raise UnauthorizedError()

    user_id = decode_access_token(credentials.credentials, settings)
    user = UserRepository(db).get_by_id(user_id)
    if user is None:
        raise TokenInvalidError()

    return user


CurrentUserDep = Annotated[User, Depends(get_current_user)]
