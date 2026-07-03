"""FastAPI dependencies."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.infrastructure.config import Settings, get_settings
from app.infrastructure.db.session import get_db
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
