"""RAG conversation routes."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, Request

from app.api.deps import ConversationServiceDep, RequireQueryRagDep
from app.modules.rag.schemas import ConversationDetailResponse, ConversationListResponse

router = APIRouter(prefix="/workspaces", tags=["conversations"])


@router.get(
    "/{workspace_id}/conversations",
    response_model=ConversationListResponse,
)
async def list_conversations(
    workspace_id: UUID,
    workspace_context: RequireQueryRagDep,
    conversation_service: ConversationServiceDep,
    request: Request,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> ConversationListResponse:
    """List the caller's RAG conversations in the workspace."""
    _ = workspace_id
    client_ip = request.client.host if request.client else None
    return conversation_service.list_conversations(
        context=workspace_context,
        page=page,
        page_size=page_size,
        ip_address=client_ip,
    )


@router.get(
    "/{workspace_id}/conversations/{conversation_id}",
    response_model=ConversationDetailResponse,
)
async def get_conversation(
    workspace_id: UUID,
    conversation_id: UUID,
    workspace_context: RequireQueryRagDep,
    conversation_service: ConversationServiceDep,
    request: Request,
) -> ConversationDetailResponse:
    """Return a conversation with full message history and citations."""
    _ = workspace_id
    client_ip = request.client.host if request.client else None
    return conversation_service.get_conversation_detail(
        context=workspace_context,
        conversation_id=conversation_id,
        ip_address=client_ip,
    )
