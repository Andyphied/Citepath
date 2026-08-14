"""Retrieval service: embed query, workspace-scoped search, score filtering."""

from __future__ import annotations

from typing import Any
from uuid import UUID

import structlog
from sqlalchemy.orm import Session

from app.infrastructure.config import Settings, get_settings
from app.infrastructure.llm.embedding import EmbeddingProvider
from app.modules.documents.repository import DocumentRepository
from app.modules.ingestion.repository import SimilarChunkResult
from app.modules.retrieval.embeddings import (
    QueryEmbeddingError as EmbeddingFailure,
)
from app.modules.retrieval.embeddings import (
    embed_query_text,
)
from app.modules.retrieval.exceptions import (
    EmptyQueryError,
    InvalidRetrievalFilterError,
    QueryEmbeddingError,
)
from app.modules.retrieval.repository import RetrievalRepository
from app.modules.retrieval.schemas import (
    CONTENT_PREVIEW_MAX_LENGTH,
    DEFAULT_TOP_K,
    DocumentMetadata,
    RetrievalFilters,
    RetrievalSearchInput,
    RetrievalSearchResult,
    RetrievedChunk,
)
from app.modules.usage.service import UsageService

logger = structlog.get_logger(__name__)


class RetrievalService:
    """Embed → search → score pipeline for RAG and agent tools."""

    def __init__(
        self,
        session: Session,
        *,
        embedding_provider: EmbeddingProvider,
        settings: Settings | None = None,
    ) -> None:
        self._session = session
        self._embedding_provider = embedding_provider
        self._settings = settings or get_settings()
        self._retrieval_repository = RetrievalRepository(session)
        self._document_repository = DocumentRepository(session)
        self._usage_service = UsageService(session)
        self._embedding_cache: dict[str, list[float]] = {}

    def search(
        self,
        *,
        query: str,
        workspace_id: UUID,
        user_id: UUID | None = None,
        top_k: int = DEFAULT_TOP_K,
        min_score: float | None = None,
        metadata: dict[str, Any] | None = None,
        filters: RetrievalFilters | None = None,
    ) -> RetrievalSearchResult:
        """Embed the query, search workspace chunks, and return scored matches."""
        validated = self._validate_query(query=query, top_k=top_k)
        validated_filters = self._validate_filters(filters)
        threshold = (
            self._settings.RETRIEVAL_MIN_SCORE if min_score is None else min_score
        )

        embedding = self._embed_query(
            query=validated.query,
            workspace_id=workspace_id,
            user_id=user_id,
            metadata=metadata,
        )

        similar_chunks = self._retrieval_repository.search_similar_with_scores(
            workspace_id=workspace_id,
            embedding=embedding,
            top_k=validated.top_k,
            file_type=validated_filters.file_type if validated_filters else None,
            source_type=validated_filters.source_type if validated_filters else None,
            document_id=validated_filters.document_id if validated_filters else None,
        )

        qualifying = [
            match for match in similar_chunks if match.score >= threshold
        ]
        qualifying.sort(key=lambda match: match.score, reverse=True)

        chunks = self._build_retrieved_chunks(
            workspace_id=workspace_id,
            matches=qualifying,
        )
        insufficient_context = len(chunks) == 0

        logger.info(
            "retrieval_search_completed",
            workspace_id=str(workspace_id),
            query_length=len(validated.query),
            top_k=validated.top_k,
            candidate_count=len(similar_chunks),
            qualifying_count=len(chunks),
            insufficient_context=insufficient_context,
            file_type=validated_filters.file_type if validated_filters else None,
            source_type=validated_filters.source_type if validated_filters else None,
            document_id=(
                str(validated_filters.document_id) if validated_filters and validated_filters.document_id else None
            ),
        )

        return RetrievalSearchResult(
            query=validated.query,
            chunks=chunks,
            insufficient_context=insufficient_context,
            top_k=validated.top_k,
            min_score=threshold,
        )

    def _validate_query(self, *, query: str, top_k: int) -> RetrievalSearchInput:
        try:
            return RetrievalSearchInput(query=query, top_k=top_k)
        except ValueError as exc:
            raise EmptyQueryError("Query must not be empty") from exc

    @staticmethod
    def _validate_filters(filters: RetrievalFilters | None) -> RetrievalFilters | None:
        if filters is None:
            return None
        try:
            return RetrievalFilters.model_validate(filters.model_dump())
        except ValueError as exc:
            raise InvalidRetrievalFilterError(str(exc)) from exc

    def _embed_query(
        self,
        *,
        query: str,
        workspace_id: UUID,
        user_id: UUID | None,
        metadata: dict[str, Any] | None,
    ) -> list[float]:
        cached = self._embedding_cache.get(query)
        if cached is not None:
            return cached

        result = embed_query_text(
            query=query,
            embedding_provider=self._embedding_provider,
            usage_service=self._usage_service,
            workspace_id=workspace_id,
            user_id=user_id,
            metadata=metadata,
        )
        if isinstance(result, EmbeddingFailure):
            raise QueryEmbeddingError(result.message)

        self._embedding_cache[query] = result.vector
        return result.vector

    def _build_retrieved_chunks(
        self,
        *,
        workspace_id: UUID,
        matches: list[SimilarChunkResult],
    ) -> list[RetrievedChunk]:
        document_cache: dict[UUID, DocumentMetadata] = {}
        retrieved: list[RetrievedChunk] = []

        for match in matches:
            chunk = match.chunk
            document_metadata = document_cache.get(chunk.document_id)
            if document_metadata is None:
                document_metadata = self._load_document_metadata(
                    workspace_id=workspace_id,
                    document_id=chunk.document_id,
                    chunk_metadata=chunk.metadata_,
                )
                document_cache[chunk.document_id] = document_metadata

            retrieved.append(
                RetrievedChunk(
                    chunk_id=chunk.id,
                    citation_id=chunk.id,
                    content_preview=self._content_preview(chunk.content),
                    score=match.score,
                    document_metadata=document_metadata,
                )
            )

        return retrieved

    def _load_document_metadata(
        self,
        *,
        workspace_id: UUID,
        document_id: UUID,
        chunk_metadata: dict[str, Any] | None,
    ) -> DocumentMetadata:
        document = self._document_repository.get_by_id(
            workspace_id=workspace_id,
            id=document_id,
        )
        if document is None:
            return DocumentMetadata(
                document_id=document_id,
                chunk_metadata=chunk_metadata,
            )

        return DocumentMetadata(
            document_id=document.id,
            title=document.title,
            source_type=document.source_type,
            file_type=document.file_type,
            chunk_metadata=chunk_metadata,
        )

    @staticmethod
    def _content_preview(content: str) -> str:
        if len(content) <= CONTENT_PREVIEW_MAX_LENGTH:
            return content
        return content[:CONTENT_PREVIEW_MAX_LENGTH]
