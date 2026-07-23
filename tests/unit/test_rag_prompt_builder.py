"""Unit tests for RAG prompt builder."""

from uuid import uuid4

from app.modules.rag.prompt_builder import (
    PROMPT_VERSION,
    build_grounded_prompt,
    parse_completion_payload,
)
from app.modules.rag.schemas import ContextChunk


def test_build_grounded_prompt_labels_chunks_and_question() -> None:
    chunk_id = uuid4()
    chunks = [
        ContextChunk(
            chunk_id=chunk_id,
            content="Restart billing-api after deploy when 502 occurs.",
            content_preview="Restart billing-api",
            score=0.91,
            document_id=uuid4(),
            document_title="Billing Runbook",
            chunk_metadata={"section": "502"},
        )
    ]

    built = build_grounded_prompt(
        question="What should I check for billing 502 errors?",
        chunks=chunks,
        history=[("user", "Earlier question"), ("assistant", "Earlier answer")],
    )

    assert built.prompt_version == PROMPT_VERSION
    assert built.messages[0]["role"] == "system"
    user_content = built.messages[1]["content"]
    assert "What should I check for billing 502 errors?" in user_content
    assert f"[CHUNK:{chunk_id}]" in user_content
    assert "Restart billing-api after deploy when 502 occurs." in user_content
    assert "CONVERSATION HISTORY:" in user_content


def test_parse_completion_payload_reads_json() -> None:
    payload = parse_completion_payload(
        '{"answer":"Check logs [1]","cited_chunk_ids":[],"suggested_followups":["Next?"]}'
    )
    assert payload["answer"] == "Check logs [1]"
    assert payload["suggested_followups"] == ["Next?"]


def test_parse_completion_payload_raises_on_invalid_json() -> None:
    import pytest

    from app.modules.rag.exceptions import ChatCompletionError

    with pytest.raises(ChatCompletionError, match="Chat completion failed"):
        parse_completion_payload("not json")


def test_parse_completion_payload_raises_on_non_object_json() -> None:
    import pytest

    from app.modules.rag.exceptions import ChatCompletionError

    with pytest.raises(ChatCompletionError, match="Chat completion failed"):
        parse_completion_payload('["not", "an", "object"]')


def test_build_grounded_prompt_limits_history_to_max_turns() -> None:
    from app.modules.rag.prompt_builder import MAX_HISTORY_TURNS, build_grounded_prompt

    history = []
    for turn in range(1, 8):
        history.append(("user", f"Question {turn}"))
        history.append(("assistant", f"Answer {turn}"))

    built = build_grounded_prompt(
        question="Latest question",
        chunks=[
            ContextChunk(
                chunk_id=uuid4(),
                content="Chunk content",
                content_preview="Chunk preview",
                score=0.9,
                document_id=uuid4(),
            )
        ],
        history=history,
    )
    user_content = built.messages[1]["content"]
    assert "Question 1" not in user_content
    assert "Answer 1" not in user_content
    assert "Question 2" not in user_content
    assert "Answer 2" not in user_content
    assert "Question 3" in user_content
    assert "Question 7" in user_content
    assert "Answer 7" in user_content
    assert MAX_HISTORY_TURNS == 5
