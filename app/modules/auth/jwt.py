"""JWT access token creation."""

from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt

from app.infrastructure.config import Settings


def create_access_token(user_id: UUID, settings: Settings) -> tuple[str, int]:
    """Create an HS256 JWT and return (token, expires_in_seconds)."""
    now = datetime.now(UTC)
    expires_in = settings.JWT_EXPIRY_HOURS * 3600
    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + timedelta(seconds=expires_in),
    }
    token = jwt.encode(
        payload,
        settings.JWT_SECRET_KEY,
        algorithm="HS256",
    )
    return token, expires_in
