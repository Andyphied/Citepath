"""RAG conversation persistence with workspace scoping."""

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.infrastructure.db.enums import ConversationMode, MessageRole
from app.infrastructure.db.scoped_repository import WorkspaceScopedRepository
from app.modules.rag.models import Conversation, Message


class RAGRepository(WorkspaceScopedRepository[Conversation]):
    """Workspace-scoped conversation and message persistence."""

    _model = Conversation

    def __init__(self, session: Session) -> None:
        super().__init__(session)

    def create_conversation(
        self,
        *,
        workspace_id: UUID,
        user_id: UUID,
        mode: ConversationMode,
        title: str | None = None,
    ) -> Conversation:
        """Persist a conversation in the given workspace."""
        conversation = Conversation(
            workspace_id=workspace_id,
            user_id=user_id,
            mode=mode,
            title=title,
        )
        self._session.add(conversation)
        self._session.commit()
        self._session.refresh(conversation)
        return conversation

    def get_conversation_by_id(
        self,
        *,
        workspace_id: UUID,
        id: UUID,
    ) -> Conversation | None:
        """Return a conversation by id within the given workspace, or None."""
        return self.get_by_id(workspace_id=workspace_id, id=id)

    def get_message_by_id(self, *, workspace_id: UUID, id: UUID) -> Message | None:
        """Return a message by id within the given workspace, or None."""
        stmt = select(Message).where(Message.id == id)
        stmt = stmt.where(Message.workspace_id == workspace_id)
        return self._session.scalar(stmt)

    def add_message(
        self,
        *,
        workspace_id: UUID,
        conversation_id: UUID,
        role: MessageRole,
        content: str,
        metadata_: dict[str, Any] | None = None,
    ) -> Message:
        """Append a message to a workspace conversation."""
        message = Message(
            workspace_id=workspace_id,
            conversation_id=conversation_id,
            role=role,
            content=content,
            metadata_=metadata_,
        )
        self._session.add(message)
        self._session.commit()
        self._session.refresh(message)
        return message

    def list_messages_for_conversation(
        self,
        *,
        workspace_id: UUID,
        conversation_id: UUID,
    ) -> list[Message]:
        """Return messages for a conversation ordered by creation time."""
        stmt = (
            select(Message)
            .where(
                Message.workspace_id == workspace_id,
                Message.conversation_id == conversation_id,
            )
            .order_by(Message.created_at)
        )
        return list(self._session.scalars(stmt).all())

