"""RAG-related HTTP exception handlers."""

from fastapi import Request, status

from app.modules.observability.errors import error_response
from app.modules.rag.exceptions import (
    ChatCompletionError,
    ConversationNotFoundError,
    EmptyQuestionError,
)
from app.modules.retrieval.exceptions import QueryEmbeddingError


async def empty_question_handler(
    request: Request,
    _exc: EmptyQuestionError,
):
    """Return 422 when the question is empty."""
    return error_response(
        request=request,
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        code="empty_question",
        message="Question must not be empty",
    )


async def conversation_not_found_handler(
    request: Request,
    _exc: ConversationNotFoundError,
):
    """Return 404 when a conversation is missing or not accessible."""
    return error_response(
        request=request,
        status_code=status.HTTP_404_NOT_FOUND,
        code="not_found",
        message="Conversation not found",
    )


async def query_embedding_error_handler(
    request: Request,
    _exc: QueryEmbeddingError,
):
    """Return 502 without exposing provider error details."""
    return error_response(
        request=request,
        status_code=status.HTTP_502_BAD_GATEWAY,
        code="embedding_failed",
        message="Unable to process your question at this time",
    )


async def chat_completion_error_handler(
    request: Request,
    _exc: ChatCompletionError,
):
    """Return 503 without exposing provider error details."""
    return error_response(
        request=request,
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        code="completion_failed",
        message="Unable to generate an answer at this time",
    )
