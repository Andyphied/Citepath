"""PDF text extraction with per-page metadata."""

from io import BytesIO

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from app.modules.ingestion.extractors.exceptions import ExtractionError
from app.modules.ingestion.extractors.types import ExtractedSegment, ExtractionResult


def extract_pdf_content(content: bytes) -> ExtractionResult:
    """Extract text from each PDF page with 1-based page_number metadata."""
    try:
        reader = PdfReader(BytesIO(content), strict=True)
    except PdfReadError as exc:
        raise ExtractionError(f"Failed to read PDF: {exc}") from exc
    except Exception as exc:
        raise ExtractionError(f"Failed to read PDF: {exc}") from exc

    if reader.is_encrypted:
        try:
            decrypt_result = reader.decrypt("")
        except Exception as exc:
            raise ExtractionError("Encrypted PDF is not supported") from exc
        if decrypt_result == 0:
            raise ExtractionError("Encrypted PDF is not supported")

    if len(reader.pages) == 0:
        raise ExtractionError("PDF contains no pages")

    segments: list[ExtractedSegment] = []
    for page_index, page in enumerate(reader.pages, start=1):
        page_text = page.extract_text() or ""
        segments.append(
            ExtractedSegment(
                text=page_text,
                metadata={"page_number": page_index},
            )
        )

    if not any(segment.text.strip() for segment in segments):
        raise ExtractionError("PDF contains no extractable text")

    return ExtractionResult(segments=segments)
