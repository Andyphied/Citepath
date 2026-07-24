"""Usage summary API schemas."""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class UsageTotalsResponse(BaseModel):
    """Aggregated token and cost totals for a workspace window."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    embedding_tokens: int = 0
    estimated_cost_usd: Decimal = Field(default=Decimal("0.000000"))
    call_count: int = 0


class UsageByDayResponse(BaseModel):
    """Per-day usage rollup (UTC calendar day)."""

    date: date
    prompt_tokens: int = 0
    completion_tokens: int = 0
    embedding_tokens: int = 0
    estimated_cost_usd: Decimal = Field(default=Decimal("0.000000"))
    call_count: int = 0


class UsageByOperationResponse(BaseModel):
    """Per-operation usage rollup."""

    operation: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    embedding_tokens: int = 0
    estimated_cost_usd: Decimal = Field(default=Decimal("0.000000"))
    call_count: int = 0


class WorkspaceUsageSummaryResponse(BaseModel):
    """Admin usage summary for a workspace date range."""

    model_config = ConfigDict(populate_by_name=True)

    workspace_id: UUID
    from_: datetime = Field(alias="from")
    to: datetime
    totals: UsageTotalsResponse
    by_day: list[UsageByDayResponse]
    by_operation: list[UsageByOperationResponse]
