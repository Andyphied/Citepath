"""RAG conversation persistence with workspace scoping."""

from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.infrastructure.db.enums import ConversationMode, MessageRole
from app.infrastructure.db.scoped_repository import WorkspaceScopedRepository
from app.modules.rag.models import Conversation, Message
from app.modules.users.models import User


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

    def list_conversations_for_user_paginated(
        self,
        *,
        workspace_id: UUID,
        user_id: UUID,
        page: int,
        page_size: int,
    ) -> tuple[list[Conversation], int]:
        """Return a paginated conversation list for a user within a workspace."""
        conditions = [
            Conversation.workspace_id == workspace_id,
            Conversation.user_id == user_id,
        ]

        total = self._session.scalar(
            select(func.count()).select_from(Conversation).where(*conditions)
        )
        total = int(total or 0)

        offset = (page - 1) * page_size
        stmt = (
            select(Conversation)
            .where(*conditions)
            .order_by(Conversation.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        items = list(self._session.scalars(stmt).all())
        return items, total

    def list_recent_user_questions_paginated(
        self,
        *,
        workspace_id: UUID,
        page: int,
        page_size: int,
    ) -> tuple[list[tuple[Message, Conversation, str | None, str]], int]:
        """Return recent user messages with conversation and user identity.

        Joins ``users`` for display name/email. Does not return assistant/system
        messages (avoids exposing full LLM prompts).
        """
        conditions = [
            Message.workspace_id == workspace_id,
            Message.role == MessageRole.USER,
        ]

        total = self._session.scalar(
            select(func.count()).select_from(Message).where(*conditions)
        )
        total = int(total or 0)

        offset = (page - 1) * page_size
        stmt = (
            select(Message, Conversation, User.name, User.email)
            .join(Conversation, Conversation.id == Message.conversation_id)
            .join(User, User.id == Conversation.user_id)
            .where(*conditions)
            .order_by(Message.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        rows = list(self._session.execute(stmt).all())
        return [
            (message, conversation, user_name, user_email)
            for message, conversation, user_name, user_email in rows
        ], total

