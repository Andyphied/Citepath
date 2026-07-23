"""Unit tests for RAG citation mapping."""

from uuid import uuid4

from app.modules.rag.citation_mapper import build_citations
from app.modules.rag.schemas import ContextChunk


def test_build_citations_returns_document_title_and_preview() -> None:
    chunk_id = uuid4()
    document_id = uuid4()
    chunks = [
        ContextChunk(
            chunk_id=chunk_id,
            content="Billing API 502 runbook step one.",
            content_preview="Billing API 502 runbook",
            score=0.88,
            document_id=document_id,
            document_title="Billing Runbook",
            chunk_metadata={"page_number": 3, "section": "502"},
        )
    ]

    citations = build_citations(
        context_chunks=chunks,
        cited_chunk_ids=[str(chunk_id)],
    )

    assert len(citations) == 1
    assert citations[0].document_id == document_id
    assert citations[0].document_title == "Billing Runbook"
    assert citations[0].chunk_preview.startswith("Billing API 502")
    assert citations[0].metadata == {"page_number": 3, "section": "502"}


def test_build_citations_ignores_invalid_llm_chunk_ids() -> None:
    chunk_id = uuid4()
    chunks = [
        ContextChunk(
            chunk_id=chunk_id,
            content="Valid chunk content",
            content_preview="Valid chunk",
            score=0.8,
            document_id=uuid4(),
            document_title="Runbook",
        )
    ]

    citations = build_citations(
        context_chunks=chunks,
        cited_chunk_ids=["not-a-uuid", str(uuid4())],
    )

    assert citations == []
