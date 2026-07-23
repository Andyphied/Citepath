"""API tests for RAG conversation list and detail endpoints."""

from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

try:
    from testcontainers.postgres import PostgresContainer
except ImportError:  # pragma: no cover - optional dev dependency
    PostgresContainer = None

from app.infrastructure.config import reset_settings_cache
from app.infrastructure.db.enums import DocumentStatus
from app.infrastructure.db.session import reset_db_engine
from app.infrastructure.llm.types import CompletionResult, EmbeddingResult
from app.main import create_app
from app.modules.ingestion.chunker import EmbeddedChunk
from app.modules.ingestion.repository import IngestionRepository

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

    def complete(self, *, messages, response_format=None):
        return CompletionResult(
            content=(
                '{"answer":"Restart billing-api for billing 502 errors.",'
                '"facts":["502 requires restart"],'
                '"recommendations":["Check upstream health"],'
                '"cited_chunk_ids":[],'
                '"suggested_followups":["What logs?","Who owns billing?"]}'
            ),
            prompt_tokens=100,
            completion_tokens=40,
            model="mock-chat",
            latency_ms=8,
        )


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
    reason="Docker is required for conversation API tests",
)


def _embedding(*, primary: float) -> list[float]:
    vector = [0.0] * EMBEDDING_DIMENSIONS
    vector[0] = primary
    return vector


@pytest.fixture(scope="module")
def postgres_url():
    with PostgresContainer("pgvector/pgvector:pg16") as postgres:
        yield postgres.get_connection_url()


@pytest.fixture
def conversation_api_context(postgres_url, minimal_env, monkeypatch):
    monkeypatch.chdir(REPO_ROOT)
    monkeypatch.setenv("DATABASE_URL", postgres_url)
    reset_settings_cache()
    reset_db_engine()

    alembic_cfg = Config(str(REPO_ROOT / "alembic.ini"))
    command.upgrade(alembic_cfg, "head")

    engine = create_engine(postgres_url)
    session_factory = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    session = session_factory()

    import app.api.deps as deps_module
    import app.infrastructure.llm.factory as factory_module

    monkeypatch.setattr(
        factory_module,
        "create_embedding_provider",
        lambda settings: FixedEmbeddingProvider(_embedding(primary=1.0)),
    )
    monkeypatch.setattr(
        factory_module,
        "create_completion_provider",
        lambda settings: StubCompletionProvider(),
    )
    monkeypatch.setattr(
        deps_module,
        "create_embedding_provider",
        lambda settings: FixedEmbeddingProvider(_embedding(primary=1.0)),
    )
    monkeypatch.setattr(
        deps_module,
        "create_completion_provider",
        lambda settings: StubCompletionProvider(),
    )

    with TestClient(create_app()) as client:
        yield client, session

    session.close()
    with engine.begin() as connection:
        connection.execute(text("TRUNCATE users RESTART IDENTITY CASCADE"))
    engine.dispose()
    reset_db_engine()


def _register(client: TestClient, *, email: str) -> tuple[dict, str]:
    response = client.post(
        "/auth/register",
        json={
            "email": email,
            "password": "securepass123",
            "name": email.split("@")[0],
        },
    )
    assert response.status_code == 201
    body = response.json()
    return body["user"], body["access_token"]


def _create_workspace(client: TestClient, token: str, *, slug: str) -> dict:
    response = client.post(
        "/workspaces",
        json={"name": slug, "slug": slug},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    return response.json()


def _seed_document(session, *, workspace_id):
    from app.modules.documents.repository import DocumentRepository

    return DocumentRepository(session).create(
        workspace_id=workspace_id,
        status=DocumentStatus.INDEXED,
        title="Billing Runbook",
        source_type="runbook",
        file_type="md",
    )


def _seed_chunk(session, *, workspace_id, document_id) -> None:
    ingestion_repo = IngestionRepository(session)
    ingestion_repo.replace_chunks_for_document(
        workspace_id=workspace_id,
        document_id=document_id,
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


def _ask_question(client, *, workspace_id, token, question, conversation_id=None):
    payload = {"question": question}
    if conversation_id is not None:
        payload["conversation_id"] = str(conversation_id)
    return client.post(
        f"/workspaces/{workspace_id}/query",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )


def test_list_conversations_returns_callers_conversations_only(
    conversation_api_context,
) -> None:
    client, session = conversation_api_context
    _user_a, token_a = _register(client, email="conv-list-a@example.com")
    _user_b, token_b = _register(client, email="conv-list-b@example.com")
    workspace = _create_workspace(client, token_a, slug="conv-list-workspace")
    document = _seed_document(session, workspace_id=workspace["id"])
    _seed_chunk(session, workspace_id=workspace["id"], document_id=document.id)

    response_a = _ask_question(
        client,
        workspace_id=workspace["id"],
        token=token_a,
        question="What should I check for billing 502 errors?",
    )
    assert response_a.status_code == 200
    conversation_id = response_a.json()["conversation_id"]

    _create_workspace(client, token_b, slug="conv-list-other")
    invite_response = client.post(
        f"/workspaces/{workspace['id']}/members",
        json={"email": "conv-list-b@example.com", "role": "member"},
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert invite_response.status_code == 201

    list_a = client.get(
        f"/workspaces/{workspace['id']}/conversations",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert list_a.status_code == 200
    body_a = list_a.json()
    assert body_a["total"] == 1
    assert len(body_a["items"]) == 1
    assert body_a["items"][0]["id"] == conversation_id
    assert body_a["items"][0]["mode"] == "rag"
    assert "502" in body_a["items"][0]["title"]

    list_b = client.get(
        f"/workspaces/{workspace['id']}/conversations",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert list_b.status_code == 200
    assert list_b.json()["total"] == 0
    assert list_b.json()["items"] == []


def test_get_conversation_returns_messages_with_citations(
    conversation_api_context,
) -> None:
    client, session = conversation_api_context
    _user, token = _register(client, email="conv-detail@example.com")
    workspace = _create_workspace(client, token, slug="conv-detail-workspace")
    document = _seed_document(session, workspace_id=workspace["id"])
    _seed_chunk(session, workspace_id=workspace["id"], document_id=document.id)

    query_response = _ask_question(
        client,
        workspace_id=workspace["id"],
        token=token,
        question="What should I check for billing 502 errors?",
    )
    assert query_response.status_code == 200
    conversation_id = query_response.json()["conversation_id"]

    detail = client.get(
        f"/workspaces/{workspace['id']}/conversations/{conversation_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert detail.status_code == 200
    body = detail.json()
    assert body["conversation"]["id"] == conversation_id
    assert len(body["messages"]) == 2
    assert body["messages"][0]["role"] == "user"
    assert body["messages"][1]["role"] == "assistant"
    assert body["messages"][1]["citations"]
    assert body["messages"][1]["citations"][0]["document_title"] == "Billing Runbook"
    assert body["messages"][1]["citations"][0]["chunk_preview"].startswith(
        "For billing 502"
    )


def test_get_conversation_returns_404_for_foreign_conversation(
    conversation_api_context,
) -> None:
    client, session = conversation_api_context
    owner, owner_token = _register(client, email="conv-owner@example.com")
    other, other_token = _register(client, email="conv-other@example.com")
    workspace = _create_workspace(client, owner_token, slug="conv-foreign-workspace")
    document = _seed_document(session, workspace_id=workspace["id"])
    _seed_chunk(session, workspace_id=workspace["id"], document_id=document.id)

    query_response = _ask_question(
        client,
        workspace_id=workspace["id"],
        token=owner_token,
        question="billing 502 guidance",
    )
    conversation_id = query_response.json()["conversation_id"]

    invite_response = client.post(
        f"/workspaces/{workspace['id']}/members",
        json={"email": "conv-other@example.com", "role": "member"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert invite_response.status_code == 201
    _ = other

    detail = client.get(
        f"/workspaces/{workspace['id']}/conversations/{conversation_id}",
        headers={"Authorization": f"Bearer {other_token}"},
    )
    assert detail.status_code == 404
    assert detail.json()["error"]["code"] == "not_found"


def test_conversation_endpoints_require_auth(conversation_api_context) -> None:
    client, _session = conversation_api_context
    workspace_id = uuid4()
    conversation_id = uuid4()

    list_response = client.get(f"/workspaces/{workspace_id}/conversations")
    assert list_response.status_code == 401

    detail_response = client.get(
        f"/workspaces/{workspace_id}/conversations/{conversation_id}"
    )
    assert detail_response.status_code == 401
