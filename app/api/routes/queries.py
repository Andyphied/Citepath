"""RAG query routes."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Body, Request

from app.api.deps import RagQueryServiceDep, RequireQueryRagDep
from app.modules.rag.schemas import QueryRequest, QueryResponse

router = APIRouter(prefix="/workspaces", tags=["queries"])

_QUERY_EXAMPLES = {
    "demo_billing_502": {
        "summary": "Northstar Cloud demo question",
        "description": (
            "Typical incident question after `python -m scripts.seed_demo` "
            "and ingestion complete."
        ),
        "value": {
            "question": (
                "What should I check for billing 502 errors after deployment?"
            ),
        },
    },
    "with_source_filter": {
        "summary": "Filter retrieval by source type",
        "value": {
            "question": "How do we roll back a billing deploy?",
            "filters": {"source_type": "runbook"},
        },
    },
    "continue_conversation": {
        "summary": "Continue an existing conversation",
        "value": {
            "question": "Which services should I check next?",
            "conversation_id": "11111111-1111-1111-1111-111111111111",
        },
    },
}


@router.post(
    "/{workspace_id}/query",
    response_model=QueryResponse,
    summary="Ask a grounded workspace question",
    response_description=(
        "Grounded answer with citations (or insufficient-context)"
    ),
)
async def ask_question(
    workspace_id: UUID,
    body: Annotated[
        QueryRequest,
        Body(openapi_examples=_QUERY_EXAMPLES),
    ],
    workspace_context: RequireQueryRagDep,
    rag_query_service: RagQueryServiceDep,
    request: Request,
) -> QueryResponse:
    """Ask a natural-language question grounded in workspace documentation.

    Retrieval is always scoped to `workspace_id`. Factual answers include
    citations; weak retrieval returns `insufficient_context: true` instead of
    inventing facts.
    """
    _ = workspace_id
    client_ip = request.client.host if request.client else None
    return rag_query_service.ask(
        context=workspace_context,
        question=body.question,
        conversation_id=body.conversation_id,
        ip_address=client_ip,
        filters=body.filters,
    )
