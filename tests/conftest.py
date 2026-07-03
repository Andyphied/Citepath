"""Shared pytest fixtures."""

import os

import pytest

from app.infrastructure.config import reset_settings_cache
from app.infrastructure.db.session import reset_db_engine


@pytest.fixture(autouse=True)
def clear_settings_cache(tmp_path, monkeypatch):
    """Ensure each test gets a fresh settings cache and no local .env bleed."""
    monkeypatch.chdir(tmp_path)
    reset_settings_cache()
    reset_db_engine()
    yield
    reset_settings_cache()
    reset_db_engine()


@pytest.fixture
def minimal_env(monkeypatch):
    """Set required environment variables for settings validation."""
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost:5432/atlasops")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key")
    monkeypatch.setenv("STORAGE_BACKEND", "local")
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    reset_settings_cache()
    reset_db_engine()
