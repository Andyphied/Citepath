"""JSON document text extraction."""

import json
from typing import Any

from app.modules.ingestion.extractors.exceptions import ExtractionError
from app.modules.ingestion.extractors.types import ExtractedSegment, ExtractionResult


def _collect_string_values(value: Any) -> list[str]:
    strings: list[str] = []
    if isinstance(value, str):
        stripped = value.strip()
        if stripped:
            strings.append(stripped)
    elif isinstance(value, dict):
        for nested in value.values():
            strings.extend(_collect_string_values(nested))
    elif isinstance(value, list):
        for nested in value:
            strings.extend(_collect_string_values(nested))
    return strings


def extract_json_content(content: bytes) -> ExtractionResult:
    """Extract string fields from JSON or stringify structured content."""
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ExtractionError("JSON file is not valid UTF-8") from exc

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ExtractionError(f"Invalid JSON: {exc.msg}") from exc

    string_values = _collect_string_values(parsed)
    if string_values:
        extracted_text = "\n".join(string_values)
    else:
        extracted_text = json.dumps(parsed, indent=2, ensure_ascii=False)

    if not extracted_text.strip():
        raise ExtractionError("Extracted JSON text is empty")

    return ExtractionResult(segments=[ExtractedSegment(text=extracted_text, metadata={})])
