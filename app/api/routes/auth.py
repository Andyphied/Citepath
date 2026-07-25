"""Authentication routes."""

from fastapi import APIRouter, Response, status

from app.api.deps import AuthServiceDep, CurrentUserDep, LoginRateLimitDep
from app.modules.auth.schemas import (
    LoginRequest,
    LoginResponse,
    RegisterRequest,
    RegisterResponse,
    UserResponse,
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


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
def logout(
    _current_user: CurrentUserDep,
    auth_service: AuthServiceDep,
) -> Response:
    """Acknowledge logout for an authenticated session.

    MVP uses stateless JWTs with no Redis blocklist. Clients must discard the
    access token after a successful logout response.
    """
    auth_service.logout()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/me", response_model=UserResponse)
def get_current_user_profile(current_user: CurrentUserDep) -> UserResponse:
    """Return the authenticated user's profile."""
    return UserResponse.model_validate(current_user)
