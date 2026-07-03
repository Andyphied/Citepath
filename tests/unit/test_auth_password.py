"""Unit tests for password hashing."""

import bcrypt

from app.modules.auth.password import (
    BCRYPT_ROUNDS,
    DUMMY_PASSWORD_HASH,
    hash_password,
    verify_password,
)


def test_hash_password_uses_bcrypt_cost_12() -> None:
    hashed = hash_password("securepass123")

    assert hashed.startswith("$2b$")
    cost = int(hashed.split("$")[2])
    assert cost == BCRYPT_ROUNDS


def test_hash_password_verifies_with_bcrypt() -> None:
    plain = "securepass123"
    hashed = hash_password(plain)

    assert bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def test_verify_password_returns_true_for_matching_password() -> None:
    plain = "securepass123"
    hashed = hash_password(plain)

    assert verify_password(plain, hashed) is True


def test_verify_password_returns_false_for_wrong_password() -> None:
    hashed = hash_password("securepass123")

    assert verify_password("wrongpassword", hashed) is False


def test_verify_password_returns_false_for_malformed_hash() -> None:
    assert verify_password("anypassword", "not-a-valid-bcrypt-hash") is False
    assert verify_password("anypassword", "") is False


def test_dummy_password_hash_is_valid_bcrypt() -> None:
    assert DUMMY_PASSWORD_HASH.startswith("$2b$12$")
    assert bcrypt.checkpw(
        b"dummy-timing-password-not-used-for-login",
        DUMMY_PASSWORD_HASH.encode("utf-8"),
    )
