"""RAG request and response schemas."""

from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

ConfidenceLevel = Literal["high", "medium", "low"]


class QueryRequest(BaseModel):
    """Workspace-scoped RAG query request."""

    question: str = Field(min_length=1)
    conversation_id: UUID | None = None

    @field_validator("question")
    @classmethod
    def question_not_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Question must not be empty")
        return stripped


class CitationResponse(BaseModel):
    """Source citation returned with a grounded answer."""

    model_config = ConfigDict(from_attributes=True)

    chunk_id: UUID
    document_id: UUID
    document_title: str | None = None
    chunk_preview: str
    score: float
    metadata: dict[str, Any] | None = None


class QueryResponse(BaseModel):
    """Workspace-scoped RAG query response."""

    conversation_id: UUID
    message_id: UUID
    answer: str
    confidence: ConfidenceLevel
    citations: list[CitationResponse]
    suggested_followups: list[str]
    insufficient_context: bool


class ContextChunk(BaseModel):
    """Full chunk content selected for LLM grounding."""

    chunk_id: UUID
    content: str
    content_preview: str
    score: float
    document_id: UUID
    document_title: str | None = None
    chunk_metadata: dict[str, Any] | None = None
