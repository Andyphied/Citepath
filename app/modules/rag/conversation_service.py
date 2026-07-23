"""RAG conversation list and detail orchestration."""

from uuid import UUID

from sqlalchemy.orm import Session

from app.infrastructure.db.enums import ConversationMode
from app.modules.rag.exceptions import ConversationNotFoundError
from app.modules.rag.models import Conversation, Message
from app.modules.rag.repository import RAGRepository
from app.modules.rag.schemas import (
    CitationResponse,
    ConversationDetailResponse,
    ConversationListResponse,
    ConversationSummaryResponse,
    MessageResponse,
)
from app.modules.workspaces.context import WorkspaceContext
from app.modules.workspaces.permissions import PermissionAction, PermissionService


class ConversationService:
    """List and retrieve RAG conversations for the authenticated creator."""

    def __init__(
        self,
        session: Session,
        permission_service: PermissionService,
    ) -> None:
        self._rag_repository = RAGRepository(session)
        self._permission_service = permission_service

    def list_conversations(
        self,
        *,
        context: WorkspaceContext,
        page: int,
        page_size: int,
        ip_address: str | None = None,
    ) -> ConversationListResponse:
        """Return paginated conversations owned by the caller."""
        self._permission_service.require(
            context,
            PermissionAction.QUERY_RAG,
            ip_address=ip_address,
        )

        conversations, total = self._rag_repository.list_conversations_for_user_paginated(
            workspace_id=context.workspace_id,
            user_id=context.user_id,
            page=page,
            page_size=page_size,
        )
        return ConversationListResponse(
            items=[self._to_summary(conversation) for conversation in conversations],
            total=total,
            page=page,
            page_size=page_size,
        )

    def get_conversation_detail(
        self,
        *,
        context: WorkspaceContext,
        conversation_id: UUID,
        ip_address: str | None = None,
    ) -> ConversationDetailResponse:
        """Return a conversation with full message history and citations."""
        self._permission_service.require(
            context,
            PermissionAction.QUERY_RAG,
            ip_address=ip_address,
        )

        conversation = self._rag_repository.get_conversation_by_id(
            workspace_id=context.workspace_id,
            id=conversation_id,
        )
        if conversation is None or conversation.user_id != context.user_id:
            raise ConversationNotFoundError()

        messages = self._rag_repository.list_messages_for_conversation(
            workspace_id=context.workspace_id,
            conversation_id=conversation_id,
        )
        return ConversationDetailResponse(
            conversation=self._to_summary(conversation),
            messages=[self._to_message(message) for message in messages],
        )

    @staticmethod
    def _to_summary(conversation: Conversation) -> ConversationSummaryResponse:
        mode = (
            conversation.mode.value
            if isinstance(conversation.mode, ConversationMode)
            else str(conversation.mode)
        )
        return ConversationSummaryResponse(
            id=conversation.id,
            title=conversation.title,
            mode=mode,
            created_at=conversation.created_at,
            updated_at=conversation.updated_at,
        )

    @staticmethod
    def _to_message(message: Message) -> MessageResponse:
        metadata = message.metadata_
        citations = _citations_from_metadata(metadata)
        role = message.role.value if hasattr(message.role, "value") else str(message.role)
        return MessageResponse(
            id=message.id,
            role=role,
            content=message.content,
            metadata=metadata,
            citations=citations,
            created_at=message.created_at,
        )


def _citations_from_metadata(
    metadata: dict[str, object] | None,
) -> list[CitationResponse]:
    if not metadata:
        return []
    raw_citations = metadata.get("citations")
    if not isinstance(raw_citations, list):
        return []

    citations: list[CitationResponse] = []
    for item in raw_citations:
        if isinstance(item, dict):
            citations.append(CitationResponse(**item))
    return citations
