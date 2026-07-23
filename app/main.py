"""FastAPI application factory."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError

from app.api.auth_errors import (
    duplicate_email_handler,
    invalid_credentials_handler,
    rate_limited_handler,
    token_expired_handler,
    token_invalid_handler,
    unauthorized_handler,
)
from app.api.document_errors import (
    document_not_found_handler,
    document_reindex_in_progress_handler,
    empty_file_handler,
    file_too_large_handler,
    invalid_file_content_handler,
    unsupported_file_type_handler,
)
from app.api.ingestion_errors import ingestion_job_not_found_handler
from app.api.rag_errors import (
    chat_completion_error_handler,
    conversation_not_found_handler,
    empty_question_handler,
    query_embedding_error_handler,
)
from app.api.routes import auth, documents, health, ingestion, queries, workspaces
from app.api.workspace_errors import (
    already_member_handler,
    duplicate_slug_handler,
    invalid_slug_handler,
    last_owner_handler,
    member_not_found_handler,
    user_not_found_handler,
    workspace_forbidden_handler,
)
from app.infrastructure.config import get_settings
from app.infrastructure.rate_limit import RateLimitedError
from app.modules.auth.exceptions import (
    DuplicateEmailError,
    InvalidCredentialsError,
    TokenExpiredError,
    TokenInvalidError,
    UnauthorizedError,
)
from app.modules.documents.exceptions import (
    DocumentNotFoundError,
    DocumentReindexInProgressError,
    EmptyFileError,
    FileTooLargeError,
    InvalidFileContentError,
    UnsupportedFileTypeError,
)
from app.modules.ingestion.exceptions import IngestionJobNotFoundError
from app.modules.observability.errors import (
    request_validation_exception_handler,
    unhandled_exception_handler,
)
from app.modules.observability.logging import configure_logging
from app.modules.observability.middleware import RequestIdMiddleware
from app.modules.observability.request_logging import RequestLoggingMiddleware
from app.modules.rag.exceptions import (
    ChatCompletionError,
    ConversationNotFoundError,
    EmptyQuestionError,
)
from app.modules.retrieval.exceptions import QueryEmbeddingError
from app.modules.workspaces.exceptions import (
    AlreadyMemberError,
    DuplicateSlugError,
    InvalidSlugError,
    LastOwnerError,
    MemberNotFoundError,
    UserNotFoundError,
    WorkspaceForbiddenError,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load and validate configuration on startup."""
    get_settings()
    yield


def create_app() -> FastAPI:
    """Create the FastAPI application with validated settings."""
    configure_logging()
    get_settings()
    app = FastAPI(
        title="AtlasOps AI",
        description="Workspace-scoped RAG and incident investigation platform",
        lifespan=lifespan,
    )
    # RequestLoggingMiddleware is inner; RequestIdMiddleware is outer (runs first on ingress).
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(RequestIdMiddleware)
    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(workspaces.router)
    app.include_router(documents.router)
    app.include_router(queries.router)
    app.include_router(ingestion.router)
    app.add_exception_handler(DuplicateEmailError, duplicate_email_handler)
    app.add_exception_handler(InvalidCredentialsError, invalid_credentials_handler)
    app.add_exception_handler(RateLimitedError, rate_limited_handler)
    app.add_exception_handler(UnauthorizedError, unauthorized_handler)
    app.add_exception_handler(TokenExpiredError, token_expired_handler)
    app.add_exception_handler(TokenInvalidError, token_invalid_handler)
    app.add_exception_handler(DuplicateSlugError, duplicate_slug_handler)
    app.add_exception_handler(InvalidSlugError, invalid_slug_handler)
    app.add_exception_handler(WorkspaceForbiddenError, workspace_forbidden_handler)
    app.add_exception_handler(UserNotFoundError, user_not_found_handler)
    app.add_exception_handler(AlreadyMemberError, already_member_handler)
    app.add_exception_handler(MemberNotFoundError, member_not_found_handler)
    app.add_exception_handler(LastOwnerError, last_owner_handler)
    app.add_exception_handler(UnsupportedFileTypeError, unsupported_file_type_handler)
    app.add_exception_handler(EmptyFileError, empty_file_handler)
    app.add_exception_handler(InvalidFileContentError, invalid_file_content_handler)
    app.add_exception_handler(FileTooLargeError, file_too_large_handler)
    app.add_exception_handler(DocumentNotFoundError, document_not_found_handler)
    app.add_exception_handler(
        DocumentReindexInProgressError,
        document_reindex_in_progress_handler,
    )
    app.add_exception_handler(
        IngestionJobNotFoundError,
        ingestion_job_not_found_handler,
    )
    app.add_exception_handler(EmptyQuestionError, empty_question_handler)
    app.add_exception_handler(
        ConversationNotFoundError,
        conversation_not_found_handler,
    )
    app.add_exception_handler(QueryEmbeddingError, query_embedding_error_handler)
    app.add_exception_handler(ChatCompletionError, chat_completion_error_handler)
    app.add_exception_handler(
        RequestValidationError,
        request_validation_exception_handler,
    )
    app.add_exception_handler(Exception, unhandled_exception_handler)
    return app
