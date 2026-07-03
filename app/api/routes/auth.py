"""Authentication routes."""

from fastapi import APIRouter, status

from app.api.deps import AuthServiceDep, LoginRateLimitDep
from app.modules.auth.schemas import (
    LoginRequest,
    LoginResponse,
    RegisterRequest,
    RegisterResponse,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
)
def register(
    body: RegisterRequest,
    auth_service: AuthServiceDep,
) -> RegisterResponse:
    """Create a new user account and return a JWT access token."""
    return auth_service.register(
        email=body.email,
        password=body.password,
        name=body.name,
    )


@router.post(
    "/login",
    response_model=LoginResponse,
    status_code=status.HTTP_200_OK,
)
def login(
    body: LoginRequest,
    auth_service: AuthServiceDep,
    _rate_limit: LoginRateLimitDep,
) -> LoginResponse:
    """Authenticate with email and password and return a JWT access token."""
    return auth_service.login(
        email=body.email,
        password=body.password,
    )
