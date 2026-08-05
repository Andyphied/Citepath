"""FastAPI application factory."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi

from app.api.agent_errors import (
    agent_completion_error_handler,
    agent_orchestration_error_handler,
    agent_run_not_found_handler,
    empty_objective_handler,
)
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
from app.api.routes import (
    admin,
    agent_runs,
    auth,
    conversations,
    documents,
    health,
    ingestion,
    metrics,
    queries,
    workspaces,
)
from app.api.audit_errors import invalid_audit_range_handler
from app.api.usage_errors import invalid_usage_range_handler
from app.api.workspace_errors import (
    already_member_handler,
    duplicate_slug_handler,
    invalid_slug_handler,
    last_owner_handler,
    member_not_found_handler,
    user_not_found_handler,
    workspace_forbidden_handler,
)
from app.infrastructure.config import Environment, get_settings
from app.infrastructure.rate_limit import RateLimitedError
from app.modules.agents.exceptions import (
    AgentCompletionError,
    AgentOrchestrationError,
    AgentRunNotFoundError,
    EmptyObjectiveError,
)
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
from app.modules.observability.metrics_middleware import MetricsMiddleware
from app.modules.observability.middleware import RequestIdMiddleware
from app.modules.observability.request_logging import RequestLoggingMiddleware
from app.modules.rag.exceptions import (
    ChatCompletionError,
    ConversationNotFoundError,
    EmptyQuestionError,
)
from app.modules.retrieval.exceptions import QueryEmbeddingError
from app.modules.audit.exceptions import InvalidAuditRangeError
from app.modules.usage.exceptions import InvalidUsageRangeError
from app.modules.workspaces.exceptions import (
    AlreadyMemberError,
    DuplicateSlugError,
    InvalidSlugError,
    LastOwnerError,
    MemberNotFoundError,
    UserNotFoundError,
    WorkspaceForbiddenError,
)


OPENAPI_TAGS = [
    {"name": "health", "description": "Liveness and readiness probes"},
    {"name": "metrics", "description": "Prometheus metrics scrape endpoint"},
    {
        "name": "auth",
        "description": "Registration, login, logout, and current user profile",
    },
    {
        "name": "workspaces",
        "description": "Workspace CRUD and membership (RBAC)",
    },
    {
        "name": "documents",
        "description": "Document upload, list, detail, delete, and re-index",
    },
    {
        "name": "ingestion",
        "description": "Ingestion job status and retry",
    },
    {
        "name": "queries",
        "description": "Workspace-scoped RAG question answering with citations",
    },
    {
        "name": "conversations",
        "description": "RAG conversation history",
    },
    {
        "name": "agent-runs",
        "description": "Controlled incident investigation agent runs and tool calls",
    },
    {
        "name": "admin",
        "description": "Owner/Admin dashboard aggregates (usage, jobs, audit)",
    },
]

OPENAPI_DESCRIPTION = """
Workspace-scoped RAG and incident investigation API for AtlasOps AI.

## Authentication

Most endpoints require a Bearer JWT:

1. `POST /auth/register` or `POST /auth/login` → `access_token`
2. Click **Authorize** in Swagger UI and paste the token (or send
   `Authorization: Bearer <token>`)
3. Call workspace-scoped routes with a workspace you belong to

Tokens are **HS256** JWTs (`sub` = user id, `exp`, `iat`). Logout is
acknowledgment-only in MVP — clients must discard the token (no server
blocklist). Swagger UI `persistAuthorization` keeps the JWT in browser
storage until cleared — fine for local demo; do not rely on it for shared
or internet-facing deploys.

## Workspace isolation

Every `{workspace_id}` route checks membership before the handler runs
(non-members get **403**). Tenant-owned queries (documents, chunks,
conversations, agent runs, usage, audit) are scoped by `workspace_id` at
the repository layer. Cross-workspace resource access returns **404**
(not 403) to avoid enumeration.

## Docs (local demo)

- Swagger UI: `/docs`
- ReDoc: `/redoc`
- OpenAPI JSON: `/openapi.json`

These surfaces are intended for **local demo**. Restrict at the network
edge before any shared or internet-facing deploy. Architecture package:
see repository `docs/README.md`.
""".strip()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load and validate configuration on startup."""
    get_settings()
    yield


def custom_openapi(app: FastAPI):
    """Build OpenAPI schema once; keep BearerJWT metadata explicit."""

    def _openapi() -> dict:
        if app.openapi_schema:
            return app.openapi_schema
        schema = get_openapi(
            title=app.title,
            version=app.version,
            description=app.description,
            routes=app.routes,
            tags=app.openapi_tags,
        )
        schema.setdefault("components", {}).setdefault("securitySchemes", {})
        schema["components"]["securitySchemes"]["BearerJWT"] = {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": (
                "HS256 JWT from POST /auth/login or POST /auth/register. "
                "Header: Authorization: Bearer <access_token>"
            ),
        }
        app.openapi_schema = schema
        return app.openapi_schema

    return _openapi


def create_app() -> FastAPI:
    """Create the FastAPI application with validated settings."""
    configure_logging()
    settings = get_settings()
    app = FastAPI(
        title="AtlasOps AI",
        description=OPENAPI_DESCRIPTION,
        version="0.1.0",
        lifespan=lifespan,
        openapi_tags=OPENAPI_TAGS,
        swagger_ui_parameters={"persistAuthorization": True},
    )
    app.openapi = custom_openapi(app)  # type: ignore[method-assign]
    # Innermost first: Metrics → RequestLogging; RequestId then CORS outermost.
    app.add_middleware(MetricsMiddleware)
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(RequestIdMiddleware)
    cors_origins = [
        origin.strip()
        for origin in settings.CORS_ORIGINS.split(",")
        if origin.strip()
    ]
    if settings.ENVIRONMENT == Environment.DEVELOPMENT and not cors_origins:
        cors_origins = [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ]
    if cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=cors_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    app.include_router(health.router)
    app.include_router(metrics.router)
    app.include_router(auth.router)
    app.include_router(workspaces.router)
    app.include_router(documents.router)
    app.include_router(queries.router)
    app.include_router(conversations.router)
    app.include_router(agent_runs.router)
    app.include_router(ingestion.router)
    app.include_router(admin.router)
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
    app.add_exception_handler(EmptyObjectiveError, empty_objective_handler)
    app.add_exception_handler(AgentRunNotFoundError, agent_run_not_found_handler)
    app.add_exception_handler(
        AgentOrchestrationError,
        agent_orchestration_error_handler,
    )
    app.add_exception_handler(AgentCompletionError, agent_completion_error_handler)
    app.add_exception_handler(InvalidUsageRangeError, invalid_usage_range_handler)
    app.add_exception_handler(InvalidAuditRangeError, invalid_audit_range_handler)
    app.add_exception_handler(
        RequestValidationError,
        request_validation_exception_handler,
    )
    app.add_exception_handler(Exception, unhandled_exception_handler)
    return app
