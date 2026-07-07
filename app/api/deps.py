"""FastAPI dependencies."""

from collections.abc import Callable
from typing import Annotated
from uuid import UUID

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.infrastructure.config import Settings, get_settings
from app.infrastructure.db.session import get_db
from app.infrastructure.rate_limit import (
    RateLimitedError,
    check_login_rate_limit,
)
from app.infrastructure.storage import create_storage_backend
from app.modules.audit.repository import AuditRepository
from app.modules.auth.exceptions import TokenInvalidError, UnauthorizedError
from app.modules.auth.jwt import decode_access_token
from app.modules.auth.repository import AuthRepository
from app.modules.auth.service import AuthService
from app.modules.documents.repository import DocumentRepository
from app.modules.documents.service import DocumentService
from app.modules.ingestion.job_repository import IngestionJobRepository
from app.modules.ingestion.service import IngestionService
from app.modules.users.models import User
from app.modules.users.repository import UserRepository
from app.modules.workspaces.context import WorkspaceContext
from app.modules.workspaces.exceptions import WorkspaceForbiddenError
from app.modules.workspaces.permissions import PermissionAction, PermissionService
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


def get_permission_service(db: DbSession) -> PermissionService:
    """Provide PermissionService with audit persistence."""
    return PermissionService(AuditRepository(db))


PermissionServiceDep = Annotated[PermissionService, Depends(get_permission_service)]


def get_workspace_service(db: DbSession) -> WorkspaceService:
    """Provide WorkspaceService with database session."""
    audit_repository = AuditRepository(db)
    permission_service = PermissionService(audit_repository)
    return WorkspaceService(
        WorkspaceRepository(db),
        UserRepository(db),
        permission_service,
    )


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


def _client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


def get_workspace_context_factory(
    denial_action: PermissionAction,
) -> Callable[..., WorkspaceContext]:
    """Build a dependency that resolves workspace context for a route."""

    def _get_workspace_context(
        workspace_id: UUID,
        current_user: CurrentUserDep,
        request: Request,
        db: DbSession,
        permission_service: PermissionServiceDep,
    ) -> WorkspaceContext:
        """Load membership and build workspace context; deny non-members before handlers."""
        ip_address = _client_ip(request)
        workspace_repository = WorkspaceRepository(db)

        membership = workspace_repository.get_member(workspace_id, current_user.id)
        if membership is None:
            permission_service.record_authorization_failure(
                workspace_id=workspace_id,
                user_id=current_user.id,
                action=denial_action,
                reason="non_member",
                ip_address=ip_address,
            )
            raise WorkspaceForbiddenError()

        workspace = workspace_repository.get_by_id(workspace_id)
        if workspace is None:
            permission_service.record_authorization_failure(
                workspace_id=workspace_id,
                user_id=current_user.id,
                action=denial_action,
                reason="non_member",
                ip_address=ip_address,
            )
            raise WorkspaceForbiddenError()

        return WorkspaceContext(
            workspace_id=workspace_id,
            user_id=current_user.id,
            role=membership.role,
        )

    return _get_workspace_context


WorkspaceContextDep = Annotated[
    WorkspaceContext,
    Depends(get_workspace_context_factory(PermissionAction.VIEW_DOCUMENTS)),
]


def require_permission(
    action: PermissionAction,
) -> Callable[..., WorkspaceContext]:
    """Factory for dependencies that enforce a permission on workspace context."""

    def _require_permission(
        context: Annotated[
            WorkspaceContext,
            Depends(get_workspace_context_factory(action)),
        ],
        request: Request,
        permission_service: PermissionServiceDep,
    ) -> WorkspaceContext:
        permission_service.require(
            context,
            action,
            ip_address=_client_ip(request),
        )
        return context

    return _require_permission


RequireManageMembersDep = Annotated[
    WorkspaceContext,
    Depends(require_permission(PermissionAction.MANAGE_MEMBERS)),
]

RequireDocumentMutateDep = Annotated[
    WorkspaceContext,
    Depends(require_permission(PermissionAction.DOCUMENT_MUTATE)),
]


def get_document_service(
    db: DbSession,
    settings: SettingsDep,
) -> DocumentService:
    """Provide DocumentService with repository and storage backend."""
    ingestion_service = IngestionService(IngestionJobRepository(db))
    return DocumentService(
        DocumentRepository(db),
        create_storage_backend(settings),
        settings,
        ingestion_service,
    )


DocumentServiceDep = Annotated[DocumentService, Depends(get_document_service)]
