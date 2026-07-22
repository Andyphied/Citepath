"""Retrieval domain schemas."""

from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

DEFAULT_TOP_K = 8
CONTENT_PREVIEW_MAX_LENGTH = 200


class DocumentMetadata(BaseModel):
    """Document metadata attached to a retrieved chunk."""

    model_config = ConfigDict(from_attributes=True)

    document_id: UUID
    title: str | None = None
    source_type: str | None = None
    file_type: str | None = None
    chunk_metadata: dict[str, Any] | None = None


class RetrievedChunk(BaseModel):
    """A workspace-scoped chunk match for downstream RAG and agents."""

    chunk_id: UUID
    citation_id: UUID
    content_preview: str
    score: float
    document_metadata: DocumentMetadata


class RetrievalSearchResult(BaseModel):
    """Result of embed → search → score pipeline."""

    query: str
    chunks: list[RetrievedChunk]
    insufficient_context: bool
    top_k: int
    min_score: float


class RetrievalSearchInput(BaseModel):
    """Validated retrieval search request."""

    query: str = Field(min_length=1)
    top_k: int = Field(default=DEFAULT_TOP_K, ge=1, le=50)

    @field_validator("query")
    @classmethod
    def query_not_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Query must not be empty")
        return stripped
