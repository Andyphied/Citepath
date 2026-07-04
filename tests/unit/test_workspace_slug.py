"""Unit tests for workspace slug helpers."""

import pytest

from app.modules.workspaces.slug import (
    append_slug_suffix,
    generate_slug_from_name,
    is_valid_slug,
)


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("Northstar Cloud", "northstar-cloud"),
        ("  Platform Team  ", "platform-team"),
        ("API v2", "api-v2"),
        ("---", "workspace"),
        ("", "workspace"),
    ],
)
def test_generate_slug_from_name(name: str, expected: str) -> None:
    assert generate_slug_from_name(name) == expected


@pytest.mark.parametrize(
    "slug",
    [
        "northstar-cloud",
        "api-v2",
        "a",
        "a-b-c",
        "workspace123",
    ],
)
def test_is_valid_slug_accepts_valid_values(slug: str) -> None:
    assert is_valid_slug(slug) is True


@pytest.mark.parametrize(
    "slug",
    [
        "",
        "Northstar-Cloud",
        "northstar_cloud",
        "northstar cloud",
        "-leading",
        "trailing-",
        "double--hyphen",
    ],
)
def test_is_valid_slug_rejects_invalid_values(slug: str) -> None:
    assert is_valid_slug(slug) is False


def test_append_slug_suffix_respects_max_length() -> None:
    base = "a" * 128
    result = append_slug_suffix(base, 99)
    assert len(result) <= 128
    assert result.endswith("-99")
