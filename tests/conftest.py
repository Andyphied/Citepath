"""Shared pytest fixtures."""

import pytest

from app.infrastructure.config import reset_settings_cache


@pytest.fixture(autouse=True)
def clear_settings_cache(tmp_path, monkeypatch):
    """Ensure each test gets a fresh settings cache and no local .env bleed."""
    monkeypatch.chdir(tmp_path)
    reset_settings_cache()
    yield
    reset_settings_cache()
