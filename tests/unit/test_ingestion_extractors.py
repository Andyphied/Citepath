"""Unit tests for ingestion text extractors."""

from pathlib import Path

import pytest

from app.modules.ingestion.extractors import ExtractionError, extract_document_text

FIXTURES_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "documents"


def test_extract_markdown_returns_single_segment() -> None:
    content = (FIXTURES_DIR / "sample.md").read_bytes()

    result = extract_document_text(file_type="md", content=content)

    assert len(result.segments) == 1
    assert "Incident Runbook" in result.segments[0].text
    assert result.segments[0].metadata == {}


def test_extract_txt_returns_single_segment() -> None:
    content = (FIXTURES_DIR / "sample.txt").read_bytes()

    result = extract_document_text(file_type="txt", content=content)

    assert len(result.segments) == 1
    assert "connection pool exhausted" in result.segments[0].text


def test_extract_json_collects_string_fields() -> None:
    content = (FIXTURES_DIR / "sample.json").read_bytes()

    result = extract_document_text(file_type="json", content=content)

    assert len(result.segments) == 1
    text = result.segments[0].text
    assert "API outage summary" in text
    assert "Elevated 503 responses on checkout." in text
    assert "Scale checkout pods to three replicas." in text
    assert "42" not in text


def test_extract_json_stringifies_when_no_string_fields() -> None:
    content = b'{"count": 1, "enabled": true}'

    result = extract_document_text(file_type="json", content=content)

    assert len(result.segments) == 1
    assert '"count": 1' in result.segments[0].text


def test_extract_json_rejects_invalid_json() -> None:
    with pytest.raises(ExtractionError, match="Invalid JSON"):
        extract_document_text(file_type="json", content=b"{not-json")


def test_extract_text_rejects_empty_content() -> None:
    with pytest.raises(ExtractionError, match="empty"):
        extract_document_text(file_type="txt", content=b"   \n\t  ")


def test_extract_pdf_returns_page_metadata(three_page_pdf_bytes: bytes) -> None:
    result = extract_document_text(file_type="pdf", content=three_page_pdf_bytes)

    assert len(result.segments) == 3
    assert [segment.metadata["page_number"] for segment in result.segments] == [1, 2, 3]
    assert "Page 1 content" in result.segments[0].text
    assert "Page 2 content" in result.segments[1].text
    assert "Page 3 content" in result.segments[2].text


def test_extract_pdf_rejects_corrupt_file() -> None:
    content = (FIXTURES_DIR / "corrupt.pdf").read_bytes()

    with pytest.raises(ExtractionError, match="Failed to read PDF"):
        extract_document_text(file_type="pdf", content=content)


def test_extract_pdf_rejects_empty_text(three_page_pdf_bytes: bytes, monkeypatch) -> None:
    class EmptyPage:
        def extract_text(self) -> str:
            return ""

    class EmptyReader:
        is_encrypted = False
        pages = [EmptyPage(), EmptyPage(), EmptyPage()]

    def fake_pdf_reader(*args, **kwargs):
        return EmptyReader()

    monkeypatch.setattr("app.modules.ingestion.extractors.pdf.PdfReader", fake_pdf_reader)

    with pytest.raises(ExtractionError, match="no extractable text"):
        extract_document_text(file_type="pdf", content=three_page_pdf_bytes)


def test_extract_document_text_rejects_unsupported_type() -> None:
    with pytest.raises(ExtractionError, match="Unsupported file type"):
        extract_document_text(file_type="docx", content=b"binary")
