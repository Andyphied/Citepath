"""Ingestion persistence with workspace scoping."""

from typing import Any
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.infrastructure.db.scoped_repository import WorkspaceScopedRepository
from app.modules.ingestion.chunker import EmbeddedChunk
from app.modules.ingestion.models import DocumentChunk


class IngestionRepository(WorkspaceScopedRepository[DocumentChunk]):
    """Workspace-scoped document chunk persistence and vector search."""

    _model = DocumentChunk

    def __init__(self, session: Session) -> None:
        super().__init__(session)

    def create_chunk(
        self,
        *,
        workspace_id: UUID,
        document_id: UUID,
        chunk_index: int,
        content: str,
        embedding: list[float] | None = None,
        metadata_: dict[str, Any] | None = None,
        embedding_model: str | None = None,
    ) -> DocumentChunk:
        """Persist a document chunk in the given workspace."""
        chunk = DocumentChunk(
            workspace_id=workspace_id,
            document_id=document_id,
            chunk_index=chunk_index,
            content=content,
            embedding=embedding,
            metadata_=metadata_,
            embedding_model=embedding_model,
        )
        self._session.add(chunk)
        self._session.commit()
        self._session.refresh(chunk)
        return chunk

    def delete_chunks_for_document(
        self,
        *,
        workspace_id: UUID,
        document_id: UUID,
    ) -> None:
        """Delete all chunks for a document in the workspace."""
        delete_stmt = delete(DocumentChunk).where(
            DocumentChunk.workspace_id == workspace_id,
            DocumentChunk.document_id == document_id,
        )
        self._session.execute(delete_stmt)
        self._session.commit()

    def replace_chunks_for_document(
        self,
        *,
        workspace_id: UUID,
        document_id: UUID,
        embedded_chunks: list[EmbeddedChunk],
    ) -> list[DocumentChunk]:
        """Delete existing chunks for a document and bulk-insert replacements."""
        delete_stmt = delete(DocumentChunk).where(
            DocumentChunk.workspace_id == workspace_id,
            DocumentChunk.document_id == document_id,
        )
        self._session.execute(delete_stmt)

        chunks = [
            DocumentChunk(
                workspace_id=workspace_id,
                document_id=document_id,
                chunk_index=embedded.chunk_index,
                content=embedded.content,
                embedding=embedded.embedding,
                metadata_=embedded.metadata,
                embedding_model=embedded.embedding_model,
            )
            for embedded in embedded_chunks
        ]
        if chunks:
            self._session.add_all(chunks)
        self._session.commit()
        for chunk in chunks:
            self._session.refresh(chunk)
        return chunks

    def get_chunk_by_id(
        self,
        *,
        workspace_id: UUID,
        id: UUID,
    ) -> DocumentChunk | None:
        """Return a chunk by id within the given workspace, or None."""
        return self.get_by_id(workspace_id=workspace_id, id=id)

    def list_chunks_for_document(
        self,
        *,
        workspace_id: UUID,
        document_id: UUID,
    ) -> list[DocumentChunk]:
        """Return chunks for a document within the given workspace."""
        stmt = (
            select(DocumentChunk)
            .where(DocumentChunk.document_id == document_id)
            .order_by(DocumentChunk.chunk_index)
        )
        stmt = self._scoped_filter(stmt, workspace_id)
        return list(self._session.scalars(stmt).all())

    def count_chunks_for_document(
        self,
        *,
        workspace_id: UUID,
        document_id: UUID,
    ) -> int:
        """Return the number of stored chunks for a document in the workspace."""
        count = self._session.scalar(
            select(func.count())
            .select_from(DocumentChunk)
            .where(
                DocumentChunk.workspace_id == workspace_id,
                DocumentChunk.document_id == document_id,
            )
        )
        return int(count or 0)

    def search_similar(
        self,
        *,
        workspace_id: UUID,
        embedding: list[float],
        top_k: int,
    ) -> list[DocumentChunk]:
        """Return top-k chunks by cosine similarity in the workspace."""
        stmt = (
            select(DocumentChunk)
            .where(DocumentChunk.embedding.isnot(None))
            .order_by(DocumentChunk.embedding.cosine_distance(embedding))
            .limit(top_k)
        )
        stmt = self._scoped_filter(stmt, workspace_id)
        return list(self._session.scalars(stmt).all())
