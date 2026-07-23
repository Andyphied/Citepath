"""RAG query orchestration: retrieve, generate, cite, persist."""

from __future__ import annotations

from typing import Any
from uuid import UUID

import structlog
from sqlalchemy.orm import Session

from app.infrastructure.config import Settings, get_settings
from app.infrastructure.db.enums import ConversationMode, MessageRole
from app.infrastructure.llm.completion import ChatCompletionProvider
from app.modules.ingestion.repository import IngestionRepository
from app.modules.rag.citation_mapper import build_citations, citations_to_metadata
from app.modules.rag.completion import complete_rag_answer
from app.modules.rag.exceptions import (
    ChatCompletionError,
    ConversationNotFoundError,
    EmptyQuestionError,
)
from app.modules.rag.models import Conversation
from app.modules.rag.prompt_builder import (
    PROMPT_VERSION,
    build_grounded_prompt,
    parse_completion_payload,
)
from app.modules.rag.repository import RAGRepository
from app.modules.rag.schemas import (
    ConfidenceLevel,
    ContextChunk,
    QueryResponse,
)
from app.modules.retrieval.exceptions import EmptyQueryError
from app.modules.retrieval.schemas import RetrievedChunk, RetrievalFilters
from app.modules.retrieval.service import RetrievalService
from app.modules.usage.service import UsageService
from app.modules.workspaces.context import WorkspaceContext
from app.modules.workspaces.permissions import PermissionAction, PermissionService

logger = structlog.get_logger(__name__)

CONTEXT_MAX_CHUNKS = 5
INSUFFICIENT_CONTEXT_MESSAGE = (
    "I couldn't find enough relevant information in your workspace documentation "
    "to answer this question. Consider uploading runbooks or documentation related "
    "to your topic."
)
INSUFFICIENT_FOLLOWUPS = [
    "Which documents cover this topic?",
    "Can I upload a runbook for this service?",
]


class RagQueryService:
    """Orchestrate retrieval, grounded generation, citations, and persistence."""

    def __init__(
        self,
        session: Session,
        *,
        retrieval_service: RetrievalService,
        completion_provider: ChatCompletionProvider,
        permission_service: PermissionService,
        usage_service: UsageService,
        settings: Settings | None = None,
    ) -> None:
        self._session = session
        self._retrieval_service = retrieval_service
        self._completion_provider = completion_provider
        self._permission_service = permission_service
        self._usage_service = usage_service
        self._settings = settings or get_settings()
        self._rag_repository = RAGRepository(session)
        self._ingestion_repository = IngestionRepository(session)

    def ask(
        self,
        *,
        context: WorkspaceContext,
        question: str,
        conversation_id: UUID | None = None,
        ip_address: str | None = None,
        filters: RetrievalFilters | None = None,
    ) -> QueryResponse:
        """Answer a workspace question with retrieval-grounded context."""
        self._permission_service.require(
            context,
            PermissionAction.QUERY_RAG,
            ip_address=ip_address,
        )

        normalized_question = question.strip()
        if not normalized_question:
            raise EmptyQuestionError()

        conversation = self._resolve_conversation(
            context=context,
            conversation_id=conversation_id,
            question=normalized_question,
        )
        history = self._load_conversation_history(
            workspace_id=context.workspace_id,
            conversation_id=conversation.id,
        )

        self._rag_repository.add_message(
            workspace_id=context.workspace_id,
            conversation_id=conversation.id,
            role=MessageRole.USER,
            content=normalized_question,
        )

        try:
            retrieval = self._retrieval_service.search(
                query=normalized_question,
                workspace_id=context.workspace_id,
                user_id=context.user_id,
                metadata={"conversation_id": str(conversation.id)},
                filters=filters,
            )
        except EmptyQueryError as exc:
            raise EmptyQuestionError() from exc

        if retrieval.insufficient_context:
            return self._insufficient_context_response(
                context=context,
                conversation=conversation,
                question=normalized_question,
            )

        context_chunks = self._select_context_chunks(
            workspace_id=context.workspace_id,
            retrieved_chunks=retrieval.chunks,
        )
        confidence = self._compute_confidence(context_chunks)

        prompt = build_grounded_prompt(
            question=normalized_question,
            chunks=context_chunks,
            history=history,
        )

        raw_content = complete_rag_answer(
            messages=prompt.messages,
            completion_provider=self._completion_provider,
            usage_service=self._usage_service,
            workspace_id=context.workspace_id,
            user_id=context.user_id,
            prompt_version=prompt.prompt_version,
            response_format={"type": "json_object"},
            metadata={"conversation_id": str(conversation.id)},
        )

        payload = parse_completion_payload(raw_content)
        answer = str(payload.get("answer", "")).strip()
        if not answer:
            answer = (
                "I found relevant documentation but could not format a grounded answer. "
                "Please try rephrasing your question."
            )

        citations = build_citations(
            context_chunks=context_chunks,
            cited_chunk_ids=payload.get("cited_chunk_ids"),
        )
        if not citations and context_chunks:
            citations = build_citations(context_chunks=context_chunks)

        followups = self._normalize_followups(payload.get("suggested_followups"))

        assistant_metadata = {
            "confidence": confidence,
            "insufficient_context": False,
            "prompt_version": PROMPT_VERSION,
            "citations": citations_to_metadata(citations),
            "facts": payload.get("facts") or [],
            "recommendations": payload.get("recommendations") or [],
            "retrieved_chunk_ids": [str(chunk.chunk_id) for chunk in context_chunks],
        }
        assistant_message = self._rag_repository.add_message(
            workspace_id=context.workspace_id,
            conversation_id=conversation.id,
            role=MessageRole.ASSISTANT,
            content=answer,
            metadata_=assistant_metadata,
        )

        logger.info(
            "rag_query_completed",
            workspace_id=str(context.workspace_id),
            conversation_id=str(conversation.id),
            confidence=confidence,
            citation_count=len(citations),
        )

        return QueryResponse(
            conversation_id=conversation.id,
            message_id=assistant_message.id,
            answer=answer,
            confidence=confidence,
            citations=citations,
            suggested_followups=followups,
            insufficient_context=False,
        )

    def _resolve_conversation(
        self,
        *,
        context: WorkspaceContext,
        conversation_id: UUID | None,
        question: str,
    ) -> Conversation:
        if conversation_id is None:
            title = question[:80] + ("..." if len(question) > 80 else "")
            return self._rag_repository.create_conversation(
                workspace_id=context.workspace_id,
                user_id=context.user_id,
                mode=ConversationMode.RAG,
                title=title,
            )

        conversation = self._rag_repository.get_conversation_by_id(
            workspace_id=context.workspace_id,
            id=conversation_id,
        )
        if conversation is None or conversation.user_id != context.user_id:
            raise ConversationNotFoundError()
        return conversation

    def _load_conversation_history(
        self,
        *,
        workspace_id: UUID,
        conversation_id: UUID,
    ) -> list[tuple[str, str]]:
        messages = self._rag_repository.list_messages_for_conversation(
            workspace_id=workspace_id,
            conversation_id=conversation_id,
        )
        history: list[tuple[str, str]] = []
        for message in messages:
            history.append((message.role.value, message.content))
        return history

    def _select_context_chunks(
        self,
        *,
        workspace_id: UUID,
        retrieved_chunks: list[RetrievedChunk],
    ) -> list[ContextChunk]:
        selected = retrieved_chunks[:CONTEXT_MAX_CHUNKS]

        context_chunks: list[ContextChunk] = []
        for chunk in selected:
            stored = self._ingestion_repository.get_chunk_by_id(
                workspace_id=workspace_id,
                id=chunk.chunk_id,
            )
            content = stored.content if stored is not None else chunk.content_preview
            context_chunks.append(
                ContextChunk(
                    chunk_id=chunk.chunk_id,
                    content=content,
                    content_preview=chunk.content_preview,
                    score=chunk.score,
                    document_id=chunk.document_metadata.document_id,
                    document_title=chunk.document_metadata.title,
                    chunk_metadata=chunk.document_metadata.chunk_metadata,
                )
            )
        return context_chunks

    def _insufficient_context_response(
        self,
        *,
        context: WorkspaceContext,
        conversation: Conversation,
        question: str,
    ) -> QueryResponse:
        assistant_metadata = {
            "confidence": "low",
            "insufficient_context": True,
            "prompt_version": PROMPT_VERSION,
            "citations": [],
        }
        assistant_message = self._rag_repository.add_message(
            workspace_id=context.workspace_id,
            conversation_id=conversation.id,
            role=MessageRole.ASSISTANT,
            content=INSUFFICIENT_CONTEXT_MESSAGE,
            metadata_=assistant_metadata,
        )

        logger.info(
            "rag_insufficient_context",
            workspace_id=str(context.workspace_id),
            conversation_id=str(conversation.id),
            question_length=len(question),
        )

        return QueryResponse(
            conversation_id=conversation.id,
            message_id=assistant_message.id,
            answer=INSUFFICIENT_CONTEXT_MESSAGE,
            confidence="low",
            citations=[],
            suggested_followups=list(INSUFFICIENT_FOLLOWUPS),
            insufficient_context=True,
        )

    @staticmethod
    def _compute_confidence(chunks: list[ContextChunk]) -> ConfidenceLevel:
        if not chunks:
            return "low"
        top_score = chunks[0].score
        if top_score >= 0.85 and len(chunks) >= 2:
            return "high"
        if top_score >= 0.72:
            return "medium"
        return "low"

    @staticmethod
    def _normalize_followups(raw_followups: Any) -> list[str]:
        if not isinstance(raw_followups, list):
            return []
        followups = [str(item).strip() for item in raw_followups if str(item).strip()]
        return followups[:3]
