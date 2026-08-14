"""Unit tests for RAG suggested-followup normalization."""

from app.modules.rag.query_service import RagQueryService


def test_normalize_followups_keeps_operational_questions() -> None:
    followups = RagQueryService._normalize_followups(
        [
            "What was the gateway timeout during the incident?",
            "How do I restart billing-api after a 502?",
            "Who owns the payments on-call rotation?",
        ]
    )
    assert len(followups) == 3
    assert followups[0].startswith("What was the gateway")


def test_normalize_followups_drops_product_capability_questions() -> None:
    followups = RagQueryService._normalize_followups(
        [
            "Can I upload a runbook for this service?",
            "Which documents cover this topic?",
            "What should I check for billing 502 errors after deployment?",
            "Does this app support PDF uploads?",
        ]
    )
    assert followups == [
        "What should I check for billing 502 errors after deployment?",
    ]


def test_normalize_followups_handles_invalid_payload() -> None:
    assert RagQueryService._normalize_followups(None) == []
    assert RagQueryService._normalize_followups("not-a-list") == []
    assert RagQueryService._normalize_followups(["", "  "]) == []
