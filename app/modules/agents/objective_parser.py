"""Lightweight objective parsing for agent planning hints."""

from __future__ import annotations

import re

_SERVICE_PATTERN = re.compile(
    r"\b([a-z][a-z0-9-]*(?:-[a-z0-9]+)*)\b",
    re.IGNORECASE,
)
_ERROR_CODE_PATTERN = re.compile(r"\b([45]\d{2})\b")
_NOISE_WORDS = frozenset(
    {
        "the",
        "after",
        "before",
        "when",
        "what",
        "should",
        "check",
        "deployment",
        "incident",
        "error",
        "errors",
        "api",
        "service",
    }
)


def parse_objective(objective: str) -> dict[str, list[str]]:
    """Extract service-like tokens and HTTP error codes from an objective."""
    error_codes = sorted(set(_ERROR_CODE_PATTERN.findall(objective)))
    services: list[str] = []
    for match in _SERVICE_PATTERN.findall(objective):
        token = match.lower()
        if token in _NOISE_WORDS:
            continue
        if token.endswith("-api") or token.endswith("-service") or "-" in token:
            if token not in services:
                services.append(token)
    return {
        "error_codes": error_codes,
        "services": services,
    }
