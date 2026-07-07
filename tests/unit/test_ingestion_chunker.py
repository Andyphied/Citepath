"""Unit tests for document content chunking."""

from uuid import uuid4

import tiktoken

from app.modules.ingestion.chunker import (
    ENCODING_NAME,
    ContentChunk,
    chunk_extraction_result,
)
from app.modules.ingestion.extractors.types import ExtractedSegment, ExtractionResult


def _encoding():
    return tiktoken.get_encoding(ENCODING_NAME)


def _long_paragraph(token_count: int) -> str:
    encoding = _encoding()
    tokens = list(range(token_count))
    return encoding.decode(tokens)


def _chunk_workspace_context() -> dict:
    return {
        "workspace_id": uuid4(),
        "document_id": uuid4(),
        "document_title": "Incident Report",
        "source_type": "general",
    }


def test_short_document_produces_single_chunk() -> None:
    context = _chunk_workspace_context()
    extraction_result = ExtractionResult(
        segments=[ExtractedSegment(text="Short incident summary.", metadata={})],
    )

    chunks = chunk_extraction_result(
        extraction_result=extraction_result,
        chunk_size_tokens=1000,
        chunk_overlap_tokens=150,
        **context,
    )

    assert len(chunks) == 1
    assert chunks[0].chunk_index == 0
    assert "Short incident summary." in chunks[0].content
    assert chunks[0].metadata["document_title"] == "Incident Report"
    assert chunks[0].metadata["source_type"] == "general"
    assert chunks[0].metadata["workspace_id"] == str(context["workspace_id"])
    assert chunks[0].metadata["document_id"] == str(context["document_id"])
    assert chunks[0].metadata["chunk_index"] == 0


def test_long_document_produces_multiple_overlapping_chunks() -> None:
    context = _chunk_workspace_context()
    paragraph_one = _long_paragraph(700)
    paragraph_two = _long_paragraph(700)
    paragraph_three = _long_paragraph(700)
    extraction_result = ExtractionResult(
        segments=[
            ExtractedSegment(
                text=f"{paragraph_one}\n\n{paragraph_two}\n\n{paragraph_three}",
                metadata={},
            )
        ],
    )

    chunks = chunk_extraction_result(
        extraction_result=extraction_result,
        chunk_size_tokens=1000,
        chunk_overlap_tokens=150,
        **context,
    )

    assert len(chunks) > 1
    assert [chunk.chunk_index for chunk in chunks] == list(range(len(chunks)))

    for index in range(len(chunks) - 1):
        current = chunks[index].content
        nxt = chunks[index + 1].content
        overlap_found = any(
            current[-overlap_size:].strip() in nxt
            for overlap_size in range(20, min(len(current), 400))
        )
        assert overlap_found, f"Expected overlap between chunk {index} and {index + 1}"


def test_pdf_page_number_is_preserved_in_chunk_metadata() -> None:
    context = _chunk_workspace_context()
    extraction_result = ExtractionResult(
        segments=[
            ExtractedSegment(
                text="Content from page two of the incident PDF.",
                metadata={"page_number": 2},
            )
        ],
    )

    chunks = chunk_extraction_result(
        extraction_result=extraction_result,
        chunk_size_tokens=1000,
        chunk_overlap_tokens=150,
        **context,
    )

    assert len(chunks) == 1
    assert chunks[0].metadata["page_number"] == 2


def test_markdown_section_heading_is_detected_and_prepended() -> None:
    context = _chunk_workspace_context()
    extraction_result = ExtractionResult(
        segments=[
            ExtractedSegment(
                text="# Root Cause\n\nThe service failed during deploy.",
                metadata={},
            )
        ],
    )

    chunks = chunk_extraction_result(
        extraction_result=extraction_result,
        chunk_size_tokens=1000,
        chunk_overlap_tokens=150,
        **context,
    )

    assert len(chunks) == 1
    assert chunks[0].content.startswith("# Root Cause")
    assert chunks[0].metadata["section_heading"] == "Root Cause"


def test_chunk_result_type() -> None:
    context = _chunk_workspace_context()
    extraction_result = ExtractionResult(
        segments=[ExtractedSegment(text="typed chunk output", metadata={})],
    )

    chunks = chunk_extraction_result(
        extraction_result=extraction_result,
        **context,
    )

    assert isinstance(chunks[0], ContentChunk)
