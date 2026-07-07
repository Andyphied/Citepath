"""Unit tests for application configuration."""

import pytest
from pydantic import ValidationError

from app.infrastructure.config import Settings, get_settings, reset_settings_cache
from app.main import create_app


def _set_minimal_valid_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set the minimum required environment variables for a valid Settings load."""
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+psycopg2://user:pass@localhost:5432/atlasops",
    )
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key-for-jwt-signing")
    monkeypatch.setenv("STORAGE_BACKEND", "local")
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")


def test_settings_loads_with_required_env(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_minimal_valid_env(monkeypatch)

    settings = Settings()

    assert settings.DATABASE_URL.startswith("postgresql")
    assert settings.JWT_SECRET_KEY == "test-secret-key-for-jwt-signing"
    assert settings.EMBEDDING_MODEL == "text-embedding-3-small"
    assert settings.STORAGE_PATH == "/uploads"


def test_missing_jwt_secret_key_fails_with_descriptive_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_minimal_valid_env(monkeypatch)
    monkeypatch.delenv("JWT_SECRET_KEY", raising=False)

    with pytest.raises(ValidationError) as exc_info:
        Settings()

    error_text = str(exc_info.value)
    assert "JWT_SECRET_KEY" in error_text


def test_blank_jwt_secret_key_fails_with_descriptive_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_minimal_valid_env(monkeypatch)
    monkeypatch.setenv("JWT_SECRET_KEY", "   ")

    with pytest.raises(ValidationError) as exc_info:
        Settings()

    error_text = str(exc_info.value)
    assert "JWT_SECRET_KEY" in error_text
    assert "must not be empty" in error_text


def test_create_app_fails_when_jwt_secret_key_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_minimal_valid_env(monkeypatch)
    monkeypatch.delenv("JWT_SECRET_KEY", raising=False)
    reset_settings_cache()

    with pytest.raises(ValidationError) as exc_info:
        create_app()

    assert "JWT_SECRET_KEY" in str(exc_info.value)


def test_s3_backend_requires_bucket_and_region(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_minimal_valid_env(monkeypatch)
    monkeypatch.setenv("STORAGE_BACKEND", "s3")

    with pytest.raises(ValidationError) as exc_info:
        Settings()

    assert "S3_BUCKET" in str(exc_info.value)


def test_anthropic_provider_requires_api_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_minimal_valid_env(monkeypatch)
    monkeypatch.setenv("LLM_PROVIDER", "anthropic")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    with pytest.raises(ValidationError) as exc_info:
        Settings()

    assert "ANTHROPIC_API_KEY" in str(exc_info.value)


def test_get_settings_returns_cached_instance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_minimal_valid_env(monkeypatch)

    first = get_settings()
    second = get_settings()

    assert first is second


def test_settings_ignores_unknown_env_vars(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_minimal_valid_env(monkeypatch)
    monkeypatch.setenv("UNKNOWN_FUTURE_VAR", "ignored")

    settings = Settings()

    assert not hasattr(settings, "UNKNOWN_FUTURE_VAR")


def test_settings_chunk_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_minimal_valid_env(monkeypatch)

    settings = Settings()

    assert settings.CHUNK_SIZE_TOKENS == 1000
    assert settings.CHUNK_OVERLAP_TOKENS == 150


def test_settings_rejects_overlap_greater_than_chunk_size(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_minimal_valid_env(monkeypatch)
    monkeypatch.setenv("CHUNK_SIZE_TOKENS", "500")
    monkeypatch.setenv("CHUNK_OVERLAP_TOKENS", "500")

    with pytest.raises(ValidationError) as exc_info:
        Settings()

    assert "CHUNK_OVERLAP_TOKENS" in str(exc_info.value)
