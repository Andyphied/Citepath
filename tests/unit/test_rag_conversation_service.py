"""Unit tests for RAG conversation service."""

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from app.infrastructure.db.enums import ConversationMode, MessageRole, WorkspaceRole
from app.modules.rag.conversation_service import ConversationService
from app.modules.rag.exceptions import ConversationNotFoundError
from app.modules.rag.models import Conversation, Message
from app.modules.workspaces.context import WorkspaceContext
from app.modules.workspaces.permissions import PermissionService


class StubRAGRepository:
    def __init__(
        self,
        *,
        conversations: list[Conversation] | None = None,
        messages: list[Message] | None = None,
        conversation: Conversation | None = None,
    ) -> None:
        self._conversations = conversations or []
        self._messages = messages or []
        self._conversation = conversation

    def list_conversations_for_user_paginated(
        self,
        *,
        workspace_id,
        user_id,
        page,
        page_size,
    ):
        _ = workspace_id, user_id, page, page_size
        return self._conversations, len(self._conversations)

    def get_conversation_by_id(self, *, workspace_id, id):
        _ = workspace_id
        if self._conversation is not None and self._conversation.id == id:
            return self._conversation
        return None

    def list_messages_for_conversation(self, *, workspace_id, conversation_id):
        _ = workspace_id, conversation_id
        return self._messages


def _context(*, user_id=None) -> WorkspaceContext:
    return WorkspaceContext(
        workspace_id=uuid4(),
        user_id=user_id or uuid4(),
        role=WorkspaceRole.MEMBER,
    )


def test_list_conversations_maps_summaries() -> None:
    context = _context()
    conversation = Conversation(
        id=uuid4(),
        workspace_id=context.workspace_id,
        user_id=context.user_id,
        title="Billing 502 guidance",
        mode=ConversationMode.RAG,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    service = ConversationService(None, PermissionService(None))
    service._rag_repository = StubRAGRepository(conversations=[conversation])

    response = service.list_conversations(context=context, page=1, page_size=20)

    assert response.total == 1
    assert response.items[0].title == "Billing 502 guidance"
    assert response.items[0].mode == "rag"


def test_get_conversation_detail_returns_messages_with_citations() -> None:
    context = _context()
    conversation_id = uuid4()
    conversation = Conversation(
        id=conversation_id,
        workspace_id=context.workspace_id,
        user_id=context.user_id,
        title="Billing 502 guidance",
        mode=ConversationMode.RAG,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    messages = [
        Message(
            id=uuid4(),
            workspace_id=context.workspace_id,
            conversation_id=conversation_id,
            role=MessageRole.USER,
            content="billing 502",
            metadata_=None,
            created_at=datetime.now(timezone.utc),
        ),
        Message(
            id=uuid4(),
            workspace_id=context.workspace_id,
            conversation_id=conversation_id,
            role=MessageRole.ASSISTANT,
            content="Restart billing-api.",
            metadata_={
                "citations": [
                    {
                        "chunk_id": str(uuid4()),
                        "document_id": str(uuid4()),
                        "document_title": "Billing Runbook",
                        "chunk_preview": "Restart billing-api.",
                        "score": 0.91,
                        "metadata": {"section": "502"},
                    }
                ]
            },
            created_at=datetime.now(timezone.utc),
        ),
    ]
    service = ConversationService(None, PermissionService(None))
    service._rag_repository = StubRAGRepository(
        conversation=conversation,
        messages=messages,
    )

    response = service.get_conversation_detail(
        context=context,
        conversation_id=conversation_id,
    )

    assert response.conversation.id == conversation_id
    assert len(response.messages) == 2
    assert response.messages[1].citations[0].document_title == "Billing Runbook"


def test_get_conversation_detail_rejects_foreign_conversation() -> None:
    context = _context()
    foreign_conversation = Conversation(
        id=uuid4(),
        workspace_id=context.workspace_id,
        user_id=uuid4(),
        title="Foreign",
        mode=ConversationMode.RAG,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    service = ConversationService(None, PermissionService(None))
    service._rag_repository = StubRAGRepository(conversation=foreign_conversation)

    with pytest.raises(ConversationNotFoundError):
        service.get_conversation_detail(
            context=context,
            conversation_id=foreign_conversation.id,
        )
