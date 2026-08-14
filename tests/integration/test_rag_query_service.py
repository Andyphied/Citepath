"""Integration tests for RagQueryService."""

from pathlib import Path
from uuid import UUID, uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

try:
    from testcontainers.postgres import PostgresContainer
except ImportError:  # pragma: no cover - optional dev dependency
    PostgresContainer = None

from sqlalchemy import select

from app.infrastructure.config import reset_settings_cache
from app.infrastructure.db.enums import ConversationMode, DocumentStatus, MessageRole
from app.infrastructure.db.session import reset_db_engine
from app.infrastructure.llm.types import CompletionResult, EmbeddingResult
from app.modules.auth.repository import AuthRepository
from app.modules.documents.repository import DocumentRepository
from app.modules.ingestion.chunker import EmbeddedChunk
from app.modules.ingestion.repository import IngestionRepository
from app.modules.rag.exceptions import ConversationNotFoundError
from app.modules.rag.query_service import RagQueryService
from app.modules.rag.repository import RAGRepository
from app.modules.retrieval.service import RetrievalService
from app.modules.usage.models import UsageEvent
from app.modules.workspaces.context import WorkspaceContext
from app.modules.workspaces.permissions import PermissionService
from app.modules.workspaces.repository import WorkspaceRepository

EMBEDDING_DIMENSIONS = 1536
REPO_ROOT = Path(__file__).resolve().parents[2]


class FixedEmbeddingProvider:
    def __init__(self, vector: list[float]) -> None:
        self._vector = vector

    @property
    def provider_name(self) -> str:
        return "mock"

    def embed(self, texts: list[str]) -> EmbeddingResult:
        return EmbeddingResult(
            vectors=[self._vector],
            embedding_tokens=8,
            model="mock-embedding",
            latency_ms=5,
        )


class StubCompletionProvider:
    provider_name = "mock"

    def __init__(self, content: str) -> None:
        self._content = content

    def complete(self, *, messages, response_format=None):
        return CompletionResult(
            content=self._content,
            prompt_tokens=120,
            completion_tokens=80,
            model="mock-chat",
            latency_ms=12,
        )


class StubSettings:
    RETRIEVAL_MIN_SCORE = 0.72


def _docker_available() -> bool:
    if PostgresContainer is None:
        return False
    try:
        import docker

        client = docker.from_env()
        client.ping()
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _docker_available(),
    reason="Docker is required for RAG query integration tests",
)


def _embedding(*, primary: float, secondary: float = 0.0) -> list[float]:
    vector = [0.0] * EMBEDDING_DIMENSIONS
    vector[0] = primary
    vector[1] = secondary
    return vector


@pytest.fixture(scope="module")
def postgres_url():
    with PostgresContainer("pgvector/pgvector:pg16") as postgres:
        yield postgres.get_connection_url()


@pytest.fixture
def rag_query_context(postgres_url, minimal_env, monkeypatch):
    monkeypatch.chdir(REPO_ROOT)
    monkeypatch.setenv("DATABASE_URL", postgres_url)
    reset_settings_cache()
    reset_db_engine()

    alembic_cfg = Config(str(REPO_ROOT / "alembic.ini"))
    command.upgrade(alembic_cfg, "head")

    engine = create_engine(postgres_url)
    session_factory = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    session = session_factory()

    yield session

    session.close()
    with engine.begin() as connection:
        connection.execute(text("TRUNCATE users RESTART IDENTITY CASCADE"))
    engine.dispose()
    reset_db_engine()


def _seed_billing_runbook(session: Session) -> tuple[WorkspaceContext, UUID]:
    auth_repo = AuthRepository(session)
    workspace_repo = WorkspaceRepository(session)
    document_repo = DocumentRepository(session)
    ingestion_repo = IngestionRepository(session)

    user = auth_repo.create_user(
        email="rag-int@example.com",
        password_hash="hash",
        name="RAG Integration",
    )
    workspace = workspace_repo.create_workspace_with_owner(
        name="RAG Workspace",
        slug="rag-workspace-int",
        created_by=user.id,
    )
    document = document_repo.create(
        workspace_id=workspace.id,
        status=DocumentStatus.INDEXED,
        title="Billing Runbook",
        source_type="runbook",
        file_type="md",
    )
    ingestion_repo.replace_chunks_for_document(
        workspace_id=workspace.id,
        document_id=document.id,
        embedded_chunks=[
            EmbeddedChunk(
                content="For billing 502 errors, restart billing-api and check upstream health.",
                chunk_index=0,
                metadata={"section": "502", "page_number": 3},
                embedding=_embedding(primary=1.0, secondary=0.0),
                embedding_model="text-embedding-3-small",
            )
        ],
    )
    context = WorkspaceContext(
        workspace_id=workspace.id,
        user_id=user.id,
        role=workspace_repo.get_member(workspace.id, user.id).role,
    )
    return context, document.id


def _build_service(
    session: Session,
    *,
    query_vector: list[float],
    completion_content: str,
) -> RagQueryService:
    from app.modules.usage.service import UsageService

    retrieval_service = RetrievalService(
        session,
        embedding_provider=FixedEmbeddingProvider(query_vector),
        settings=StubSettings(),
    )
    return RagQueryService(
        session,
        retrieval_service=retrieval_service,
        completion_provider=StubCompletionProvider(completion_content),
        permission_service=PermissionService(None),
        usage_service=UsageService(session),
        settings=StubSettings(),
    )


def test_rag_query_service_returns_grounded_answer_with_citations(
    rag_query_context: Session,
) -> None:
    context, document_id = _seed_billing_runbook(rag_query_context)
    chunk_id = IngestionRepository(rag_query_context).list_chunks_for_document(
        workspace_id=context.workspace_id,
        document_id=document_id,
    )[0].id
    completion_payload = (
        '{"answer":"Restart billing-api for billing 502 errors [1].",'
        f'"facts":["502 errors require billing-api restart"],'
        f'"recommendations":["Check upstream health"],'
        f'"cited_chunk_ids":["{chunk_id}"],'
        '"suggested_followups":["What logs should I inspect?","Who owns billing-api?"]}}'
    )
    service = _build_service(
        rag_query_context,
        query_vector=_embedding(primary=1.0),
        completion_content=completion_payload,
    )

    response = service.ask(
        context=context,
        question="What should I check for billing 502 errors?",
    )

    assert response.insufficient_context is False
    assert response.confidence in {"high", "medium"}
    assert len(response.citations) == 1
    assert response.citations[0].document_title == "Billing Runbook"
    assert response.citations[0].chunk_preview.startswith("For billing 502")
    assert "billing-api" in response.answer

    events = rag_query_context.scalars(
        select(UsageEvent).where(UsageEvent.workspace_id == context.workspace_id)
    ).all()
    operations = {event.operation.value for event in events}
    assert "embedding_query" in operations
    assert "chat_completion" in operations


def test_rag_query_service_insufficient_context_skips_llm(
    rag_query_context: Session,
) -> None:
    context, _document_id = _seed_billing_runbook(rag_query_context)
    service = _build_service(
        rag_query_context,
        query_vector=_embedding(primary=0.0),
        completion_content='{"answer":"hallucinated"}',
    )

    response = service.ask(
        context=context,
        question="What about billing 502 errors?",
    )

    assert response.insufficient_context is True
    assert response.confidence == "low"
    assert response.citations == []
    assert "couldn't find enough relevant information" in response.answer.lower()

    events = rag_query_context.scalars(
        select(UsageEvent).where(UsageEvent.workspace_id == context.workspace_id)
    ).all()
    assert all(event.operation.value != "chat_completion" for event in events)


def test_rag_query_service_rejects_foreign_conversation(
    rag_query_context: Session,
) -> None:
    context, _document_id = _seed_billing_runbook(rag_query_context)
    repo = RAGRepository(rag_query_context)
    foreign = repo.create_conversation(
        workspace_id=context.workspace_id,
        user_id=uuid4(),
        mode=ConversationMode.RAG,
        title="Foreign",
    )
    service = _build_service(
        rag_query_context,
        query_vector=_embedding(primary=0.0),
        completion_content="{}",
    )

    with pytest.raises(ConversationNotFoundError):
        service.ask(
            context=context,
            question="billing 502",
            conversation_id=foreign.id,
        )


def test_rag_query_service_stores_citations_on_assistant_message(
    rag_query_context: Session,
) -> None:
    context, document_id = _seed_billing_runbook(rag_query_context)
    chunk_id = IngestionRepository(rag_query_context).list_chunks_for_document(
        workspace_id=context.workspace_id,
        document_id=document_id,
    )[0].id
    completion_payload = (
        '{"answer":"Use the billing runbook.",'
        f'"cited_chunk_ids":["{chunk_id}"],'
        '"suggested_followups":["Next step?","Another?"]}}'
    )
    service = _build_service(
        rag_query_context,
        query_vector=_embedding(primary=1.0),
        completion_content=completion_payload,
    )

    response = service.ask(context=context, question="billing 502 guidance")
    repo = RAGRepository(rag_query_context)
    messages = repo.list_messages_for_conversation(
        workspace_id=context.workspace_id,
        conversation_id=response.conversation_id,
    )
    assistant = messages[-1]
    assert assistant.role == MessageRole.ASSISTANT
    assert assistant.metadata_["citations"]
    assert assistant.metadata_["prompt_version"] == "rag-grounded-v1"
