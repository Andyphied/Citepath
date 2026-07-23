"""Grounded RAG prompt construction."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.modules.rag.exceptions import ChatCompletionError
from app.modules.rag.schemas import ContextChunk

PROMPT_VERSION = "rag-grounded-v1"
MAX_HISTORY_TURNS = 4

SYSTEM_PROMPT = """You are an operational assistant for engineering teams.
Answer ONLY using facts from the provided CHUNK blocks.
Do not invent service names, configuration values, or procedures not present in the chunks.
If the chunks do not contain enough information, say so explicitly.
Separate operational facts from recommendations.
Return valid JSON with keys:
- answer: string (engineering tone; optional inline citation markers like [1])
- facts: array of strings
- recommendations: array of strings
- cited_chunk_ids: array of chunk UUID strings referenced in the answer
- suggested_followups: array of 2-3 follow-up questions
Do not include markdown code fences."""


@dataclass(frozen=True)
class BuiltPrompt:
    """Messages payload for the chat completion provider."""

    messages: list[dict[str, str]]
    prompt_version: str


def build_grounded_prompt(
    *,
    question: str,
    chunks: list[ContextChunk],
    history: list[tuple[str, str]] | None = None,
) -> BuiltPrompt:
    """Build system and user messages with labeled chunk boundaries."""
    chunk_blocks: list[str] = []
    for index, chunk in enumerate(chunks, start=1):
        chunk_blocks.append(
            "\n".join(
                [
                    f"[CHUNK:{chunk.chunk_id}]",
                    f"[CITATION_INDEX:{index}]",
                    chunk.content,
                    f"[/CHUNK:{chunk.chunk_id}]",
                ]
            )
        )

    history_blocks: list[str] = []
    if history:
        for role, content in history[-MAX_HISTORY_TURNS * 2 :]:
            history_blocks.append(f"{role.upper()}: {content}")

    user_sections = [
        "QUESTION:",
        question,
    ]
    if history_blocks:
        user_sections.extend(["", "CONVERSATION HISTORY:", *history_blocks])
    user_sections.extend(["", "RETRIEVED CONTEXT:", *chunk_blocks])

    return BuiltPrompt(
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": "\n".join(user_sections)},
        ],
        prompt_version=PROMPT_VERSION,
    )


def parse_completion_payload(content: str) -> dict[str, Any]:
    """Parse JSON completion content from the provider."""
    import json

    try:
        payload = json.loads(content)
    except json.JSONDecodeError as exc:
        raise ChatCompletionError("Chat completion failed") from exc

    if not isinstance(payload, dict):
        raise ChatCompletionError("Chat completion failed")

    return payload
