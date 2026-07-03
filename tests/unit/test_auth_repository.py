"""Unit tests for AuthRepository."""

from unittest.mock import MagicMock

import pytest
from sqlalchemy.exc import IntegrityError

from app.modules.auth.exceptions import DuplicateEmailError
from app.modules.auth.repository import AuthRepository


def test_create_user_raises_duplicate_email_on_integrity_error() -> None:
    session = MagicMock()
    session.commit.side_effect = IntegrityError("INSERT", {}, Exception())

    repository = AuthRepository(session)

    with pytest.raises(DuplicateEmailError):
        repository.create_user(
            email="user@example.com",
            password_hash="hashed",
            name=None,
        )

    session.rollback.assert_called_once()
