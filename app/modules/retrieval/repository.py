"""Retrieval read access delegating to workspace-scoped ingestion search."""

from uuid import UUID

from sqlalchemy.orm import Session

from app.modules.ingestion.repository import IngestionRepository, SimilarChunkResult


class RetrievalRepository:
    """Workspace-scoped vector search for retrieval callers."""

    def __init__(self, session: Session) -> None:
        self._ingestion_repository = IngestionRepository(session)

    def search_similar_with_scores(
        self,
        *,
        workspace_id: UUID,
        embedding: list[float],
        top_k: int,
    ) -> list[SimilarChunkResult]:
        """Return top-k chunks with scores, always scoped to workspace."""
        return self._ingestion_repository.search_similar_with_scores(
            workspace_id=workspace_id,
            embedding=embedding,
            top_k=top_k,
        )
