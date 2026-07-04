"""JWT access token creation and verification."""

from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt

from app.infrastructure.config import Settings
from app.modules.auth.exceptions import TokenExpiredError, TokenInvalidError


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


def decode_access_token(token: str, settings: Settings) -> UUID:
    """Decode and verify an HS256 JWT; return the user id from `sub`."""
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=["HS256"],
            options={"require": ["exp", "sub"]},
        )
    except jwt.ExpiredSignatureError as exc:
        raise TokenExpiredError() from exc
    except jwt.InvalidTokenError as exc:
        raise TokenInvalidError() from exc

    sub = payload.get("sub")
    if not sub:
        raise TokenInvalidError()

    try:
        return UUID(str(sub))
    except ValueError as exc:
        raise TokenInvalidError() from exc
