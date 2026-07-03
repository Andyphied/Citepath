"""Password hashing utilities."""

import bcrypt

BCRYPT_ROUNDS = 12

# Fixed salt for a deterministic dummy hash used when the user is not found,
# so login still runs bcrypt verification and avoids timing side-channels.
_DUMMY_SALT = b"$2b$12$LQv3c1yqBWVHxkd0LHAkCO"
DUMMY_PASSWORD_HASH = bcrypt.hashpw(
    b"dummy-timing-password-not-used-for-login",
    _DUMMY_SALT,
).decode("utf-8")


def hash_password(plain_password: str) -> str:
    """Hash a plaintext password with bcrypt (cost factor 12)."""
    password_bytes = plain_password.encode("utf-8")
    salt = bcrypt.gensalt(rounds=BCRYPT_ROUNDS)
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, password_hash: str) -> bool:
    """Return True if the plaintext password matches the bcrypt hash."""
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            password_hash.encode("utf-8"),
        )
    except (ValueError, TypeError):
        return False
