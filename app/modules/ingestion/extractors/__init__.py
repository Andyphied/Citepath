"""Document text extractors by file type."""

from app.modules.ingestion.extractors.exceptions import ExtractionError
from app.modules.ingestion.extractors.json_extractor import extract_json_content
from app.modules.ingestion.extractors.pdf import extract_pdf_content
from app.modules.ingestion.extractors.text import extract_text_content
from app.modules.ingestion.extractors.types import ExtractedSegment, ExtractionResult

_SUPPORTED_FILE_TYPES = frozenset({"md", "txt", "json", "pdf"})


def extract_document_text(*, file_type: str, content: bytes) -> ExtractionResult:
    """Extract structured text from raw document bytes."""
    normalized_type = file_type.lower().lstrip(".")
    if normalized_type not in _SUPPORTED_FILE_TYPES:
        raise ExtractionError(f"Unsupported file type for extraction: {file_type}")

    if normalized_type in {"md", "txt"}:
        return extract_text_content(content)
    if normalized_type == "json":
        return extract_json_content(content)
    return extract_pdf_content(content)


__all__ = [
    "ExtractedSegment",
    "ExtractionError",
    "ExtractionResult",
    "extract_document_text",
]
