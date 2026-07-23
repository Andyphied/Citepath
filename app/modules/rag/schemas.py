"""RAG request and response schemas."""

from datetime import datetime
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


class ConversationSummaryResponse(BaseModel):
    """Summary row for a user's RAG conversation."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str | None
    mode: str
    created_at: datetime
    updated_at: datetime


class ConversationListResponse(BaseModel):
    """Paginated list of the caller's conversations in a workspace."""

    items: list[ConversationSummaryResponse]
    total: int
    page: int
    page_size: int


class MessageResponse(BaseModel):
    """Persisted conversation message with optional citation metadata."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    role: str
    content: str
    metadata: dict[str, Any] | None = None
    citations: list[CitationResponse] = Field(default_factory=list)
    created_at: datetime


class ConversationDetailResponse(BaseModel):
    """Full conversation with ordered messages."""

    conversation: ConversationSummaryResponse
    messages: list[MessageResponse]


class ContextChunk(BaseModel):
    """Full chunk content selected for LLM grounding."""

    chunk_id: UUID
    content: str
    content_preview: str
    score: float
    document_id: UUID
    document_title: str | None = None
    chunk_metadata: dict[str, Any] | None = None
