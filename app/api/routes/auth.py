"""Authentication routes."""

from fastapi import APIRouter, status

from app.api.deps import AuthServiceDep
from app.modules.auth.schemas import RegisterRequest, RegisterResponse

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
