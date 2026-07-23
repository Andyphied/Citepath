"""RAG query routes."""

from uuid import UUID

from fastapi import APIRouter, Request

from app.api.deps import RagQueryServiceDep, RequireQueryRagDep
from app.modules.rag.schemas import QueryRequest, QueryResponse

router = APIRouter(prefix="/workspaces", tags=["queries"])


@router.post(
    "/{workspace_id}/query",
    response_model=QueryResponse,
)
async def ask_question(
    workspace_id: UUID,
    body: QueryRequest,
    workspace_context: RequireQueryRagDep,
    rag_query_service: RagQueryServiceDep,
    request: Request,
) -> QueryResponse:
    """Ask a natural-language question grounded in workspace documentation."""
    _ = workspace_id
    client_ip = request.client.host if request.client else None
    return rag_query_service.ask(
        context=workspace_context,
        question=body.question,
        conversation_id=body.conversation_id,
        ip_address=client_ip,
    )
