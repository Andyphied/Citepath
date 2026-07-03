"""Authentication domain service."""

from app.infrastructure.config import Settings
from app.modules.auth.exceptions import DuplicateEmailError
from app.modules.auth.jwt import create_access_token
from app.modules.auth.password import hash_password
from app.modules.auth.repository import AuthRepository
from app.modules.auth.schemas import RegisterResponse, UserResponse


class AuthService:
    """Registration, login, and token issuance."""

    def __init__(self, auth_repository: AuthRepository, settings: Settings) -> None:
        self._auth_repository = auth_repository
        self._settings = settings

    def register(
        self,
        *,
        email: str,
        password: str,
        name: str | None,
    ) -> RegisterResponse:
        """Create a user account and issue a JWT access token."""
        if self._auth_repository.find_user_by_email(email) is not None:
            raise DuplicateEmailError()

        password_hash = hash_password(password)
        user = self._auth_repository.create_user(
            email=email,
            password_hash=password_hash,
            name=name,
        )
        access_token, expires_in = create_access_token(user.id, self._settings)

        return RegisterResponse(
            user=UserResponse.model_validate(user),
            access_token=access_token,
            expires_in=expires_in,
        )
