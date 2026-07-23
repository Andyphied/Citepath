"""Agent request and response schemas."""

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.modules.rag.schemas import CitationResponse

ConfidenceLevel = Literal["high", "medium", "low"]


class AgentRunRequest(BaseModel):
    """Start an incident investigation."""

    objective: str = Field(min_length=1)
    conversation_id: UUID | None = None

    @field_validator("objective")
    @classmethod
    def objective_not_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Objective must not be empty")
        return stripped


class InvestigationSummary(BaseModel):
    """Structured investigation result persisted on agent_runs.result."""

    problem_statement: str
    summary: str
    likely_causes: list[str] = Field(default_factory=list)
    likely_related_systems: list[str] = Field(default_factory=list)
    recommended_checks: list[str] = Field(default_factory=list)
    related_documents: list[UUID] = Field(default_factory=list)
    action_items: list[str] = Field(default_factory=list)
    risks_or_unknowns: list[str] = Field(default_factory=list)
    next_steps: list[str] = Field(default_factory=list)


class AgentRunResponse(BaseModel):
    """Synchronous agent run result returned from POST."""

    agent_run_id: UUID
    status: str
    summary: InvestigationSummary | None = None
    citations: list[CitationResponse] = Field(default_factory=list)
    tool_calls_count: int = 0


class AgentRunDetailResponse(BaseModel):
    """Full agent run record for GET."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    workspace_id: UUID
    user_id: UUID
    objective: str
    status: str
    result: dict[str, Any] | None = None
    step_count: int | None = None
    created_at: datetime
    completed_at: datetime | None = None
    citations: list[CitationResponse] = Field(default_factory=list)


class SearchKnowledgeBaseArgs(BaseModel):
    """Arguments for the search_knowledge_base tool."""

    query: str = Field(min_length=1)
    file_type: str | None = None
    source_type: str | None = None
    document_id: UUID | None = None
    top_k: int = Field(default=8, ge=1, le=50)

    @field_validator("query")
    @classmethod
    def query_not_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Query must not be empty")
        return stripped


class AgentPlanAction(BaseModel):
    """LLM planning step parsed from JSON."""

    action: Literal["call_tool", "finish"]
    tool_name: str | None = None
    arguments: dict[str, Any] | None = None
    reason: str | None = None
