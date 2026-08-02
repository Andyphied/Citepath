"""Plain-text and Markdown extractors."""

from app.modules.ingestion.extractors.exceptions import ExtractionError
from app.modules.ingestion.extractors.types import ExtractedSegment, ExtractionResult


def extract_text_content(content: bytes) -> ExtractionResult:
    """Decode UTF-8 text/markdown and return a single segment."""
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ExtractionError("File is not valid UTF-8 text") from exc

    if not text.strip():
        raise ExtractionError("no extractable text")

    return ExtractionResult(segments=[ExtractedSegment(text=text, metadata={})])
