"""Token-based document chunking for the ingestion pipeline."""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from typing import Any
from uuid import UUID

import tiktoken

from app.modules.ingestion.extractors.types import ExtractionResult

ENCODING_NAME = "cl100k_base"
_HEADING_PATTERN = re.compile(r"^#{1,6}\s+(.+)$")


@dataclass(frozen=True)
class ContentChunk:
    """A text chunk ready for embedding and persistence."""

    content: str
    chunk_index: int
    metadata: dict[str, Any]


@dataclass(frozen=True)
class EmbeddedChunk:
    """A content chunk with generated embedding vectors."""

    content: str
    chunk_index: int
    metadata: dict[str, Any]
    embedding: list[float]
    embedding_model: str


@dataclass(frozen=True)
class _ParagraphUnit:
    text: str
    page_number: int | None
    section_heading: str | None


@lru_cache(maxsize=1)
def _get_encoding() -> tiktoken.Encoding:
    return tiktoken.get_encoding(ENCODING_NAME)


def _count_tokens(text: str, *, encoding: tiktoken.Encoding) -> int:
    return len(encoding.encode(text))


def _decode_tokens(tokens: list[int], *, encoding: tiktoken.Encoding) -> str:
    return encoding.decode(tokens)


def _split_paragraphs(text: str) -> list[str]:
    """Split on blank lines; fall back to whole segment."""
    parts = re.split(r"\n\s*\n", text)
    paragraphs = [part.strip() for part in parts if part.strip()]
    if paragraphs:
        return paragraphs
    stripped = text.strip()
    return [stripped] if stripped else []


def _detect_markdown_heading(paragraph: str) -> str | None:
    match = _HEADING_PATTERN.match(paragraph.strip())
    if match is None:
        return None
    return match.group(1).strip()


def _paragraph_units_from_extraction(
    extraction_result: ExtractionResult,
) -> list[_ParagraphUnit]:
    units: list[_ParagraphUnit] = []
    current_heading: str | None = None

    for segment in extraction_result.segments:
        page_number = segment.metadata.get("page_number")
        if page_number is not None and not isinstance(page_number, int):
            page_number = None

        for paragraph in _split_paragraphs(segment.text):
            heading = _detect_markdown_heading(paragraph)
            if heading is not None:
                current_heading = heading

            units.append(
                _ParagraphUnit(
                    text=paragraph,
                    page_number=page_number,
                    section_heading=current_heading,
                )
            )

    return units


def _format_chunk_content(
    paragraphs: list[_ParagraphUnit],
    *,
    overlap_prefix: str = "",
) -> str:
    body = "\n\n".join(unit.text for unit in paragraphs)
    # Prefer the earliest heading in the chunk. Skip stamping when the body
    # already opens with a markdown heading (avoids "# Escalation\n\n# Title…").
    section_heading = next(
        (unit.section_heading for unit in paragraphs if unit.section_heading),
        None,
    )
    body_opens_with_heading = bool(
        paragraphs and _HEADING_PATTERN.match(paragraphs[0].text.strip())
    )

    parts: list[str] = []
    if section_heading is not None and not body_opens_with_heading:
        parts.append(f"# {section_heading}")
    if overlap_prefix:
        parts.append(overlap_prefix)
    if body:
        parts.append(body)

    return "\n\n".join(parts)


def _build_chunk_metadata(
    *,
    workspace_id: UUID,
    document_id: UUID,
    document_title: str,
    source_type: str,
    chunk_index: int,
    paragraphs: list[_ParagraphUnit],
) -> dict[str, Any]:
    page_number = next(
        (
            unit.page_number
            for unit in paragraphs
            if unit.page_number is not None
        ),
        None,
    )
    section_heading = next(
        (
            unit.section_heading
            for unit in reversed(paragraphs)
            if unit.section_heading
        ),
        None,
    )

    metadata: dict[str, Any] = {
        "workspace_id": str(workspace_id),
        "document_id": str(document_id),
        "document_title": document_title,
        "source_type": source_type,
        "chunk_index": chunk_index,
    }
    if page_number is not None:
        metadata["page_number"] = page_number
    if section_heading is not None:
        metadata["section_heading"] = section_heading
    return metadata


def _take_overlap_suffix(
    text: str,
    overlap_tokens: int,
    *,
    encoding: tiktoken.Encoding,
) -> str:
    if overlap_tokens <= 0 or not text:
        return ""
    tokens = encoding.encode(text)
    if len(tokens) <= overlap_tokens:
        return text
    return _decode_tokens(tokens[-overlap_tokens:], encoding=encoding)


def _hard_split_paragraph(
    paragraph: _ParagraphUnit,
    *,
    chunk_size_tokens: int,
    encoding: tiktoken.Encoding,
) -> list[_ParagraphUnit]:
    tokens = encoding.encode(paragraph.text)
    if len(tokens) <= chunk_size_tokens:
        return [paragraph]

    splits: list[_ParagraphUnit] = []
    for start in range(0, len(tokens), chunk_size_tokens):
        token_slice = tokens[start:start + chunk_size_tokens]
        split_text = _decode_tokens(token_slice, encoding=encoding)
        splits.append(
            _ParagraphUnit(
                text=split_text,
                page_number=paragraph.page_number,
                section_heading=paragraph.section_heading,
            )
        )
    return splits


def chunk_extraction_result(
    *,
    extraction_result: ExtractionResult,
    workspace_id: UUID,
    document_id: UUID,
    document_title: str,
    source_type: str,
    chunk_size_tokens: int = 1000,
    chunk_overlap_tokens: int = 150,
) -> list[ContentChunk]:
    """Split extracted segments into overlapping token-bounded chunks."""
    if chunk_overlap_tokens >= chunk_size_tokens:
        raise ValueError(
            "chunk_overlap_tokens must be less than chunk_size_tokens"
        )

    encoding = _get_encoding()
    units = _paragraph_units_from_extraction(extraction_result)
    if not units:
        return []

    chunks: list[ContentChunk] = []
    current_units: list[_ParagraphUnit] = []
    overlap_prefix = ""

    def emit_chunk() -> None:
        nonlocal overlap_prefix, current_units
        if not current_units:
            return

        content = _format_chunk_content(
            current_units,
            overlap_prefix=overlap_prefix,
        )
        chunk_index = len(chunks)
        chunks.append(
            ContentChunk(
                content=content,
                chunk_index=chunk_index,
                metadata=_build_chunk_metadata(
                    workspace_id=workspace_id,
                    document_id=document_id,
                    document_title=document_title,
                    source_type=source_type,
                    chunk_index=chunk_index,
                    paragraphs=current_units,
                ),
            )
        )
        overlap_prefix = _take_overlap_suffix(
            content,
            chunk_overlap_tokens,
            encoding=encoding,
        )
        current_units = []

    for unit in units:
        expanded_units = _hard_split_paragraph(
            unit,
            chunk_size_tokens=chunk_size_tokens,
            encoding=encoding,
        )
        for split_unit in expanded_units:
            candidate_units = [*current_units, split_unit]
            candidate_content = _format_chunk_content(
                candidate_units,
                overlap_prefix=overlap_prefix,
            )
            candidate_tokens = _count_tokens(
                candidate_content,
                encoding=encoding,
            )

            if candidate_tokens <= chunk_size_tokens:
                current_units = candidate_units
                continue

            if current_units:
                emit_chunk()

            single_content = _format_chunk_content(
                [split_unit],
                overlap_prefix=overlap_prefix,
            )
            single_token_count = _count_tokens(
                single_content,
                encoding=encoding,
            )
            if single_token_count <= chunk_size_tokens:
                current_units = [split_unit]
            else:
                emit_chunk()
                current_units = [split_unit]

    if current_units:
        emit_chunk()

    return chunks
