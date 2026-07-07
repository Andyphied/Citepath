"""Shared pytest fixtures."""

from io import BytesIO
from pathlib import Path

import pytest

from app.infrastructure.config import reset_settings_cache
from app.infrastructure.db.session import reset_db_engine


@pytest.fixture(autouse=True)
def clear_settings_cache(tmp_path, monkeypatch):
    """Ensure each test gets a fresh settings cache and no local .env bleed."""
    monkeypatch.chdir(tmp_path)
    reset_settings_cache()
    reset_db_engine()
    yield
    reset_settings_cache()
    reset_db_engine()


@pytest.fixture
def minimal_env(monkeypatch):
    """Set required environment variables for settings validation."""
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost:5432/atlasops")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key")
    monkeypatch.setenv("STORAGE_BACKEND", "local")
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    reset_settings_cache()
    reset_db_engine()


def _build_pdf_with_pages(page_texts: list[str]) -> bytes:
    from pypdf import PdfWriter
    from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

    writer = PdfWriter()
    font = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        }
    )
    resources = DictionaryObject({NameObject("/Font"): DictionaryObject({NameObject("/F1"): font})})

    for page_text in page_texts:
        page = writer.add_blank_page(width=612, height=792)
        escaped_text = page_text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        content = f"BT /F1 12 Tf 72 720 Td ({escaped_text}) Tj ET"
        stream = DecodedStreamObject()
        stream.set_data(content.encode("latin-1"))
        page[NameObject("/Resources")] = resources
        page[NameObject("/Contents")] = stream

    buffer = BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


@pytest.fixture(scope="session")
def three_page_pdf_bytes() -> bytes:
    """Return a valid three-page PDF with extractable text."""
    fixture_path = Path(__file__).resolve().parent / "fixtures" / "documents" / "sample.pdf"
    if fixture_path.exists():
        return fixture_path.read_bytes()

    pdf_bytes = _build_pdf_with_pages(
        [
            "Page 1 content",
            "Page 2 content",
            "Page 3 content",
        ]
    )
    fixture_path.write_bytes(pdf_bytes)
    return pdf_bytes
