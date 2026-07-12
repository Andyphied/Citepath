"""Unit tests for IngestionRepository chunk persistence."""

from unittest.mock import MagicMock
from uuid import uuid4

from app.modules.ingestion.chunker import EmbeddedChunk
from app.modules.ingestion.repository import IngestionRepository


def _embedding(*, primary: float = 0.1) -> list[float]:
    vector = [0.0] * 1536
    vector[0] = primary
    return vector


def test_replace_chunks_for_document_deletes_and_bulk_inserts() -> None:
    session = MagicMock()
    repository = IngestionRepository(session)
    workspace_id = uuid4()
    document_id = uuid4()
    embedded_chunks = [
        EmbeddedChunk(
            content="first chunk",
            chunk_index=0,
            metadata={"page": 1},
            embedding=_embedding(primary=0.1),
            embedding_model="text-embedding-3-small",
        ),
        EmbeddedChunk(
            content="second chunk",
            chunk_index=1,
            metadata={"page": 2},
            embedding=_embedding(primary=0.2),
            embedding_model="text-embedding-3-small",
        ),
    ]

    result = repository.replace_chunks_for_document(
        workspace_id=workspace_id,
        document_id=document_id,
        embedded_chunks=embedded_chunks,
    )

    session.execute.assert_called_once()
    session.add_all.assert_called_once()
    added_chunks = session.add_all.call_args.args[0]
    assert len(added_chunks) == 2
    assert added_chunks[0].workspace_id == workspace_id
    assert added_chunks[0].document_id == document_id
    assert added_chunks[0].chunk_index == 0
    assert added_chunks[0].content == "first chunk"
    assert added_chunks[0].embedding_model == "text-embedding-3-small"
    session.commit.assert_called_once()
    assert len(result) == 2


def test_replace_chunks_for_document_allows_empty_chunk_list() -> None:
    session = MagicMock()
    repository = IngestionRepository(session)

    result = repository.replace_chunks_for_document(
        workspace_id=uuid4(),
        document_id=uuid4(),
        embedded_chunks=[],
    )

    session.execute.assert_called_once()
    session.add_all.assert_not_called()
    session.commit.assert_called_once()
    assert result == []
