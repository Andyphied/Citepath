"""Workspace slug generation and validation."""

import re

SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
MAX_SLUG_LENGTH = 128


def generate_slug_from_name(name: str) -> str:
    """Derive a URL-safe slug from a workspace display name."""
    slug = name.lower().strip()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = slug.strip("-")
    if not slug:
        slug = "workspace"
    return slug[:MAX_SLUG_LENGTH].rstrip("-")


def is_valid_slug(slug: str) -> bool:
    """Return True when slug matches lowercase-hyphen format."""
    if not slug or len(slug) > MAX_SLUG_LENGTH:
        return False
    return SLUG_PATTERN.match(slug) is not None


def append_slug_suffix(base_slug: str, suffix: int) -> str:
    """Append a numeric suffix while keeping slug within max length."""
    suffix_text = f"-{suffix}"
    trimmed_base = base_slug[: MAX_SLUG_LENGTH - len(suffix_text)].rstrip("-")
    return f"{trimmed_base}{suffix_text}"
