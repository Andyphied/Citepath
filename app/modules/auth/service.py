"""Authentication domain service."""

from app.infrastructure.config import Settings
from app.modules.auth.exceptions import DuplicateEmailError, InvalidCredentialsError
from app.modules.auth.jwt import create_access_token
from app.modules.auth.password import DUMMY_PASSWORD_HASH, hash_password, verify_password
from app.modules.auth.repository import AuthRepository
from app.modules.auth.schemas import LoginResponse, RegisterResponse, UserResponse


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

    def login(self, *, email: str, password: str) -> LoginResponse:
        """Authenticate credentials and issue a JWT access token."""
        user = self._auth_repository.find_user_by_email(email)
        password_hash = user.password_hash if user is not None else DUMMY_PASSWORD_HASH
        if not verify_password(password, password_hash) or user is None:
            raise InvalidCredentialsError()

        access_token, expires_in = create_access_token(user.id, self._settings)

        return LoginResponse(
            user=UserResponse.model_validate(user),
            access_token=access_token,
            expires_in=expires_in,
        )
