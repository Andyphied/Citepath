"""Retrieval domain exceptions."""


class RetrievalError(Exception):
    """Base retrieval error."""


class EmptyQueryError(RetrievalError):
    """Raised when a search query is empty or whitespace-only."""


class QueryEmbeddingError(RetrievalError):
    """Raised when query embedding generation fails."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message
