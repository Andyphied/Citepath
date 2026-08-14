"""Integration tests for multi-turn RAG conversations."""

from pathlib import Path
from uuid import UUID

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session, sessionmaker

try:
    from testcontainers.postgres import PostgresContainer
except ImportError:  # pragma: no cover - optional dev dependency
    PostgresContainer = None

from app.infrastructure.config import reset_settings_cache
from app.infrastructure.db.enums import DocumentStatus, MessageRole
from app.infrastructure.db.session import reset_db_engine
from app.infrastructure.llm.types import CompletionResult, EmbeddingResult
from app.main import create_app
from app.modules.auth.repository import AuthRepository
from app.modules.documents.repository import DocumentRepository
from app.modules.ingestion.chunker import EmbeddedChunk
from app.modules.ingestion.repository import IngestionRepository
from app.modules.rag.query_service import RagQueryService
from app.modules.rag.repository import RAGRepository
from app.modules.retrieval.service import RetrievalService
from app.modules.usage.models import UsageEvent
from app.modules.usage.service import UsageService
from app.modules.workspaces.context import WorkspaceContext
from app.modules.workspaces.permissions import PermissionService
from app.modules.workspaces.repository import WorkspaceRepository

EMBEDDING_DIMENSIONS = 1536
REPO_ROOT = Path(__file__).resolve().parents[2]


class FixedEmbeddingProvider:
    def __init__(self, vector: list[float]) -> None:
        self._vector = vector
        self.call_count = 0

    @property
    def provider_name(self) -> str:
        return "mock"

    def embed(self, texts: list[str]) -> EmbeddingResult:
        self.call_count += 1
        return EmbeddingResult(
            vectors=[self._vector],
            embedding_tokens=8,
            model="mock-embedding",
            latency_ms=5,
        )


class RecordingCompletionProvider:
    provider_name = "mock"

    def __init__(self, content: str) -> None:
        self._content = content
        self.call_count = 0
        self.last_messages: list[dict[str, str]] | None = None

    def complete(self, *, messages, response_format=None):
        self.call_count += 1
        self.last_messages = list(messages)
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
    reason="Docker is required for multi-turn RAG integration tests",
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
def multi_turn_context(postgres_url, minimal_env, monkeypatch):
    monkeypatch.chdir(REPO_ROOT)
    monkeypatch.setenv("DATABASE_URL", postgres_url)
    reset_settings_cache()
    reset_db_engine()

    alembic_cfg = Config(str(REPO_ROOT / "alembic.ini"))
    command.upgrade(alembic_cfg, "head")

    engine = create_engine(postgres_url)
    session_factory = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    session = session_factory()

    embedding_provider = FixedEmbeddingProvider(_embedding(primary=1.0))
    completion_provider = RecordingCompletionProvider(
        '{"answer":"Follow-up answer using prior context.",'
        '"cited_chunk_ids":[],'
        '"suggested_followups":["Next?","Another?"]}'
    )

    import app.api.deps as deps_module
    import app.infrastructure.llm.factory as factory_module

    monkeypatch.setattr(
        factory_module,
        "create_embedding_provider",
        lambda settings: embedding_provider,
    )
    monkeypatch.setattr(
        factory_module,
        "create_completion_provider",
        lambda settings: completion_provider,
    )
    monkeypatch.setattr(
        deps_module,
        "create_embedding_provider",
        lambda settings: embedding_provider,
    )
    monkeypatch.setattr(
        deps_module,
        "create_completion_provider",
        lambda settings: completion_provider,
    )

    with TestClient(create_app()) as client:
        yield client, session, embedding_provider, completion_provider

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
        email="multi-turn@example.com",
        password_hash="hash",
        name="Multi Turn",
    )
    workspace = workspace_repo.create_workspace_with_owner(
        name="Multi Turn Workspace",
        slug="multi-turn-workspace",
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


def _register_api_user(client: TestClient) -> tuple[dict, str, dict]:
    response = client.post(
        "/auth/register",
        json={
            "email": "multi-turn-api@example.com",
            "password": "securepass123",
            "name": "Multi Turn API",
        },
    )
    assert response.status_code == 201
    body = response.json()
    workspace_response = client.post(
        "/workspaces",
        json={"name": "Multi Turn API", "slug": "multi-turn-api"},
        headers={"Authorization": f"Bearer {body['access_token']}"},
    )
    assert workspace_response.status_code == 201
    return body["user"], body["access_token"], workspace_response.json()


def _seed_api_document(session: Session, *, workspace_id: UUID) -> None:
    document_repo = DocumentRepository(session)
    ingestion_repo = IngestionRepository(session)
    document = document_repo.create(
        workspace_id=workspace_id,
        status=DocumentStatus.INDEXED,
        title="Billing Runbook",
        source_type="runbook",
        file_type="md",
    )
    ingestion_repo.replace_chunks_for_document(
        workspace_id=workspace_id,
        document_id=document.id,
        embedded_chunks=[
            EmbeddedChunk(
                content="For billing 502 errors restart billing-api.",
                chunk_index=0,
                metadata={"section": "502"},
                embedding=_embedding(primary=1.0),
                embedding_model="text-embedding-3-small",
            )
        ],
    )


def test_multi_turn_query_logs_separate_usage_events_and_includes_history(
    multi_turn_context,
) -> None:
    client, session, embedding_provider, completion_provider = multi_turn_context
    _user, token, workspace = _register_api_user(client)
    _seed_api_document(session, workspace_id=UUID(workspace["id"]))

    first = client.post(
        f"/workspaces/{workspace['id']}/query",
        json={"question": "What should I check for billing 502 errors?"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert first.status_code == 200
    conversation_id = first.json()["conversation_id"]
    first_answer = first.json()["answer"]

    second = client.post(
        f"/workspaces/{workspace['id']}/query",
        json={
            "question": "What should I do after the restart?",
            "conversation_id": conversation_id,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert second.status_code == 200
    assert second.json()["conversation_id"] == conversation_id

    assert embedding_provider.call_count == 2
    assert completion_provider.call_count == 2
    assert completion_provider.last_messages is not None
    user_prompt = completion_provider.last_messages[1]["content"]
    assert "CONVERSATION HISTORY:" in user_prompt
    assert first_answer in user_prompt

    events = session.scalars(
        select(UsageEvent).where(UsageEvent.workspace_id == UUID(workspace["id"]))
    ).all()
    embedding_events = [event for event in events if event.operation.value == "embedding_query"]
    completion_events = [event for event in events if event.operation.value == "chat_completion"]
    assert len(embedding_events) == 2
    assert len(completion_events) == 2


def test_multi_turn_service_persists_four_messages_and_reruns_retrieval(
    multi_turn_context,
) -> None:
    session = multi_turn_context[1]
    context, _document_id = _seed_billing_runbook(session)
    embedding_provider = FixedEmbeddingProvider(_embedding(primary=1.0))
    completion_provider = RecordingCompletionProvider(
        '{"answer":"Turn answer.",'
        '"cited_chunk_ids":[],'
        '"suggested_followups":["Next?","Another?"]}'
    )
    service = RagQueryService(
        session,
        retrieval_service=RetrievalService(
            session,
            embedding_provider=embedding_provider,
            settings=StubSettings(),
        ),
        completion_provider=completion_provider,
        permission_service=PermissionService(None),
        usage_service=UsageService(session),
        settings=StubSettings(),
    )

    first = service.ask(
        context=context,
        question="What should I check for billing 502 errors?",
    )
    second = service.ask(
        context=context,
        question="What logs should I inspect next?",
        conversation_id=first.conversation_id,
    )
    assert second.conversation_id == first.conversation_id

    messages = RAGRepository(session).list_messages_for_conversation(
        workspace_id=context.workspace_id,
        conversation_id=first.conversation_id,
    )
    assert len(messages) == 4
    assert [message.role for message in messages] == [
        MessageRole.USER,
        MessageRole.ASSISTANT,
        MessageRole.USER,
        MessageRole.ASSISTANT,
    ]

    assert embedding_provider.call_count == 2
    assert completion_provider.call_count == 2
    assert completion_provider.last_messages is not None
    assert first.answer in completion_provider.last_messages[1]["content"]

    events = session.scalars(
        select(UsageEvent).where(UsageEvent.workspace_id == context.workspace_id)
    ).all()
    assert sum(event.operation.value == "embedding_query" for event in events) == 2
    assert sum(event.operation.value == "chat_completion" for event in events) == 2
