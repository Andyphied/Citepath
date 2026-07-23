"""Token estimation helpers for agent tool input capping."""

from __future__ import annotations

# Soft cap for document text sent to tool LLM calls (AGENT-004 notes).
# Approximate tokens as chars/4 — avoids runtime tiktoken downloads in CI/tests.
MAX_TOOL_INPUT_TOKENS = 6000
MAX_SUMMARY_BATCHES = 3


def count_tokens(text: str) -> int:
    """Return approximate token count for tool budget checks."""
    if not text:
        return 0
    return max(1, (len(text) + 3) // 4)
