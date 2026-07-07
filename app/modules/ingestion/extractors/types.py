"""Types produced by text extraction for downstream chunking."""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ExtractedSegment:
    """A contiguous text segment with optional metadata for chunking."""

    text: str
    metadata: dict[str, Any]


@dataclass(frozen=True)
class ExtractionResult:
    """Structured output from document text extraction."""

    segments: list[ExtractedSegment]

    @property
    def full_text(self) -> str:
        """Concatenate segment text with blank-line separators."""
        return "\n\n".join(segment.text for segment in self.segments if segment.text)
