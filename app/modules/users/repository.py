"""User profile persistence."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.users.models import User


class UserRepository:
    """User entity lookups (non-auth profile operations)."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_id(self, user_id: UUID) -> User | None:
        """Return a user by primary key, or None."""
        return self._session.get(User, user_id)

    def get_by_email(self, email: str) -> User | None:
        """Return a user by normalized email, or None."""
        return self._session.scalar(select(User).where(User.email == email))
