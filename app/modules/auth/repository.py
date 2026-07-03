"""Auth-related persistence (user credentials)."""

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modules.auth.exceptions import DuplicateEmailError
from app.modules.users.models import User


class AuthRepository:
    """Credential and registration persistence."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def find_user_by_email(self, email: str) -> User | None:
        """Return a user by normalized email, or None."""
        return self._session.scalar(select(User).where(User.email == email))

    def create_user(
        self,
        *,
        email: str,
        password_hash: str,
        name: str | None,
    ) -> User:
        """Persist a new user with hashed password."""
        user = User(email=email, password_hash=password_hash, name=name)
        self._session.add(user)
        try:
            self._session.commit()
        except IntegrityError:
            self._session.rollback()
            raise DuplicateEmailError from None
        self._session.refresh(user)
        return user
