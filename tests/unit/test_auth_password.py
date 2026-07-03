"""Unit tests for password hashing."""

import bcrypt

from app.modules.auth.password import BCRYPT_ROUNDS, hash_password


def test_hash_password_uses_bcrypt_cost_12() -> None:
    hashed = hash_password("securepass123")

    assert hashed.startswith("$2b$")
    cost = int(hashed.split("$")[2])
    assert cost == BCRYPT_ROUNDS


def test_hash_password_verifies_with_bcrypt() -> None:
    plain = "securepass123"
    hashed = hash_password(plain)

    assert bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
