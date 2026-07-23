"""RAG domain exceptions."""


class RAGError(Exception):
    """Base RAG error."""


class EmptyQuestionError(RAGError):
    """Raised when a question is empty or whitespace-only."""


class ConversationNotFoundError(RAGError):
    """Raised when a conversation is missing or not owned by the caller."""


class ChatCompletionError(RAGError):
    """Raised when chat completion generation fails."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message
