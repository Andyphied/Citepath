"""API tests for agent run endpoints."""

import json
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import sessionmaker

try:
    from testcontainers.postgres import PostgresContainer
except ImportError:  # pragma: no cover - optional dev dependency
    PostgresContainer = None

from app.infrastructure.config import reset_settings_cache
from app.infrastructure.db.enums import AgentRunStatus, ConversationMode, DocumentStatus
from app.infrastructure.db.session import reset_db_engine
from app.infrastructure.llm.types import CompletionResult, EmbeddingResult
from app.main import create_app
from app.modules.agents.service import AGENT_RUN_COMPLETED_EVENT, OBJECTIVE_AUDIT_MAX_CHARS
from app.modules.audit.models import AuditLog
from app.modules.ingestion.chunker import EmbeddedChunk
from app.modules.ingestion.repository import IngestionRepository

EMBEDDING_DIMENSIONS = 1536
REPO_ROOT = Path(__file__).resolve().parents[2]


class FixedEmbeddingProvider:
    @property
    def provider_name(self) -> str:
        return "mock"

    def embed(self, texts: list[str]) -> EmbeddingResult:
        vector = [0.0] * EMBEDDING_DIMENSIONS
        vector[0] = 1.0
        return EmbeddingResult(
            vectors=[vector],
            embedding_tokens=8,
            model="mock-embedding",
            latency_ms=5,
        )


class AgentStubCompletionProvider:
    provider_name = "mock"

    def __init__(self, *, unknown_tool: bool = False) -> None:
        self._call = 0
        self._unknown_tool = unknown_tool

    def complete(self, *, messages, response_format=None):
        self._call += 1
        if self._unknown_tool:
            content = json.dumps(
                {
                    "action": "call_tool",
                    "tool_name": "delete_everything",
                    "arguments": {},
                }
            )
        elif self._call == 1:
            content = json.dumps(
                {
                    "action": "call_tool",
                    "tool_name": "search_knowledge_base",
                    "arguments": {"query": "billing API 502 deployment"},
                }
            )
        elif self._call == 2:
            content = json.dumps({"action": "finish", "reason": "done"})
        else:
            content = json.dumps(
                {
                    "problem_statement": "Billing API returning 502 after deployment",
                    "summary": "Restart billing-api and verify gateway timeouts.",
                    "likely_causes": ["Recent deployment"],
                    "likely_related_systems": ["billing-api"],
                    "recommended_checks": ["Restart billing-api"],
                    "related_documents": [],
                    "action_items": ["Check gateway timeout"],
                    "risks_or_unknowns": [],
                    "next_steps": ["Review deployment notes"],
                }
            )
        return CompletionResult(
            content=content,
            prompt_tokens=80,
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
    reason="Docker is required for agent API tests",
)


@pytest.fixture(scope="module")
def postgres_url():
    with PostgresContainer("pgvector/pgvector:pg16") as postgres:
        yield postgres.get_connection_url()


@pytest.fixture
def agent_api_context(postgres_url, minimal_env, monkeypatch):
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

    completion_provider = AgentStubCompletionProvider()
    monkeypatch.setattr(
        factory_module,
        "create_embedding_provider",
        lambda settings: FixedEmbeddingProvider(),
    )
    monkeypatch.setattr(
        factory_module,
        "create_completion_provider",
        lambda settings: completion_provider,
    )
    monkeypatch.setattr(
        deps_module,
        "create_embedding_provider",
        lambda settings: FixedEmbeddingProvider(),
    )
    monkeypatch.setattr(
        deps_module,
        "create_completion_provider",
        lambda settings: completion_provider,
    )

    with TestClient(create_app()) as client:
        yield client, session, completion_provider

    session.close()
    with engine.begin() as connection:
        connection.execute(text("TRUNCATE users RESTART IDENTITY CASCADE"))
    engine.dispose()
    reset_db_engine()


def _register(client: TestClient, *, email: str = "agent-api@example.com") -> tuple[dict, str]:
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


def _create_workspace(
    client: TestClient,
    token: str,
    *,
    name: str = "Agent Workspace",
    slug: str = "agent-workspace",
) -> dict:
    response = client.post(
        "/workspaces",
        json={"name": name, "slug": slug},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    return response.json()


def _invite_member(
    client: TestClient,
    owner_token: str,
    workspace_id: str,
    *,
    email: str,
    role: str,
) -> None:
    response = client.post(
        f"/workspaces/{workspace_id}/members",
        json={"email": email, "role": role},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert response.status_code == 201


def _seed_document(session, *, workspace_id: UUID, content: str | None = None):
    from app.modules.documents.repository import DocumentRepository

    document = DocumentRepository(session).create(
        workspace_id=workspace_id,
        status=DocumentStatus.INDEXED,
        title="Billing Runbook",
        source_type="runbook",
        file_type="md",
    )
    ingestion_repo = IngestionRepository(session)
    vector = [0.0] * EMBEDDING_DIMENSIONS
    vector[0] = 1.0
    ingestion_repo.replace_chunks_for_document(
        workspace_id=workspace_id,
        document_id=document.id,
        embedded_chunks=[
            EmbeddedChunk(
                content=content or "For billing 502 errors restart billing-api.",
                chunk_index=0,
                metadata={"section": "502"},
                embedding=vector,
                embedding_model="text-embedding-3-small",
            )
        ],
    )
    return document


def test_agent_run_endpoint_completes_with_structured_summary(agent_api_context) -> None:
    client, session, _provider = agent_api_context
    user, token = _register(client)
    workspace = _create_workspace(client, token)
    _seed_document(session, workspace_id=UUID(workspace["id"]))

    response = client.post(
        f"/workspaces/{workspace['id']}/agent-runs",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "objective": "billing API 502 after deployment",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == AgentRunStatus.COMPLETED.value
    assert body["tool_calls_count"] >= 1
    assert body["summary"]["problem_statement"]
    assert body["summary"]["recommended_checks"]
    assert body["citations"]

    get_response = client.get(
        f"/workspaces/{workspace['id']}/agent-runs/{body['agent_run_id']}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert get_response.status_code == 200
    detail = get_response.json()
    assert detail["objective"] == "billing API 502 after deployment"
    assert detail["status"] == AgentRunStatus.COMPLETED.value

    tool_calls_response = client.get(
        f"/workspaces/{workspace['id']}/agent-runs/{body['agent_run_id']}/tool-calls",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert tool_calls_response.status_code == 200
    items = tool_calls_response.json()["items"]
    assert len(items) == body["tool_calls_count"]
    assert items[0]["tool_name"] == "search_knowledge_base"
    assert "query" in items[0]["input"]
    assert items[0]["output"] is not None
    assert items[0]["latency_ms"] is not None
    assert items[0]["created_at"]
    if len(items) > 1:
        assert items[0]["created_at"] <= items[1]["created_at"]

    session.expire_all()
    audit_row = session.scalar(
        select(AuditLog).where(
            AuditLog.workspace_id == workspace["id"],
            AuditLog.event_type == AGENT_RUN_COMPLETED_EVENT,
        )
    )
    assert audit_row is not None
    assert str(audit_row.actor_user_id) == user["id"]
    assert audit_row.metadata_["agent_run_id"] == body["agent_run_id"]
    assert audit_row.metadata_["status"] == AgentRunStatus.COMPLETED.value
    assert audit_row.metadata_["tool_call_count"] == body["tool_calls_count"]
    assert audit_row.metadata_["objective"] == "billing API 502 after deployment"


def test_agent_run_unknown_tool_returns_non_500(agent_api_context) -> None:
    client, session, provider = agent_api_context
    provider._unknown_tool = True
    _user, token = _register(client, email="agent-unknown-tool@example.com")
    workspace = _create_workspace(client, token, slug="agent-unknown-tool")
    _seed_document(session, workspace_id=UUID(workspace["id"]))

    response = client.post(
        f"/workspaces/{workspace['id']}/agent-runs",
        headers={"Authorization": f"Bearer {token}"},
        json={"objective": "try unknown tool path"},
    )

    assert response.status_code == 503
    body = response.json()
    assert body["error"]["code"] == "agent_orchestration_failed"
    assert "delete_everything" not in response.text

    session.expire_all()
    audit_row = session.scalar(
        select(AuditLog).where(
            AuditLog.workspace_id == workspace["id"],
            AuditLog.event_type == AGENT_RUN_COMPLETED_EVENT,
        )
    )
    assert audit_row is not None
    assert audit_row.metadata_["status"] == AgentRunStatus.FAILED.value
    assert audit_row.metadata_["tool_call_count"] >= 1


def test_agent_run_viewer_allowed_on_post_and_get(agent_api_context) -> None:
    client, session, _provider = agent_api_context
    _owner, owner_token = _register(client, email="agent-owner@example.com")
    _viewer, viewer_token = _register(client, email="agent-viewer@example.com")
    workspace = _create_workspace(client, owner_token, slug="agent-viewer-ws")
    _invite_member(
        client,
        owner_token,
        workspace["id"],
        email="agent-viewer@example.com",
        role="viewer",
    )
    _seed_document(session, workspace_id=UUID(workspace["id"]))

    post_response = client.post(
        f"/workspaces/{workspace['id']}/agent-runs",
        headers={"Authorization": f"Bearer {viewer_token}"},
        json={"objective": "billing API 502 after deployment"},
    )
    assert post_response.status_code == 200
    agent_run_id = post_response.json()["agent_run_id"]

    get_response = client.get(
        f"/workspaces/{workspace['id']}/agent-runs/{agent_run_id}",
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    assert get_response.status_code == 200


def test_agent_run_non_member_returns_403(agent_api_context) -> None:
    client, _session, _provider = agent_api_context
    _owner, owner_token = _register(client, email="agent-owner-nm@example.com")
    _outsider, outsider_token = _register(client, email="agent-outsider@example.com")
    workspace = _create_workspace(client, owner_token, slug="agent-non-member")

    post_response = client.post(
        f"/workspaces/{workspace['id']}/agent-runs",
        headers={"Authorization": f"Bearer {outsider_token}"},
        json={"objective": "billing API 502 after deployment"},
    )
    assert post_response.status_code == 403

    get_response = client.get(
        f"/workspaces/{workspace['id']}/agent-runs/{uuid4()}",
        headers={"Authorization": f"Bearer {outsider_token}"},
    )
    assert get_response.status_code == 403


def test_agent_run_unauthenticated_returns_401(agent_api_context) -> None:
    client, _session, _provider = agent_api_context
    workspace_id = uuid4()

    post_response = client.post(
        f"/workspaces/{workspace_id}/agent-runs",
        json={"objective": "billing API 502 after deployment"},
    )
    assert post_response.status_code == 401

    get_response = client.get(f"/workspaces/{workspace_id}/agent-runs/{uuid4()}")
    assert get_response.status_code == 401


def test_agent_run_cross_workspace_access_returns_404(agent_api_context) -> None:
    client, session, _provider = agent_api_context
    _user_a, token_a = _register(client, email="agent-iso-a@example.com")
    _user_b, token_b = _register(client, email="agent-iso-b@example.com")
    workspace_a = _create_workspace(client, token_a, slug="agent-iso-a")
    workspace_b = _create_workspace(client, token_b, slug="agent-iso-b")
    _seed_document(session, workspace_id=UUID(workspace_a["id"]))

    create_response = client.post(
        f"/workspaces/{workspace_a['id']}/agent-runs",
        headers={"Authorization": f"Bearer {token_a}"},
        json={"objective": "billing API 502 after deployment"},
    )
    assert create_response.status_code == 200
    agent_run_id = create_response.json()["agent_run_id"]

    cross_get = client.get(
        f"/workspaces/{workspace_b['id']}/agent-runs/{agent_run_id}",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert cross_get.status_code == 404

    cross_tool_calls = client.get(
        f"/workspaces/{workspace_b['id']}/agent-runs/{agent_run_id}/tool-calls",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert cross_tool_calls.status_code == 404


def test_agent_tool_calls_member_cannot_view_other_users_run(agent_api_context) -> None:
    client, session, _provider = agent_api_context
    _owner, owner_token = _register(client, email="agent-tool-owner@example.com")
    _member, member_token = _register(client, email="agent-tool-member@example.com")
    workspace = _create_workspace(client, owner_token, slug="agent-tool-member-ws")
    _invite_member(
        client,
        owner_token,
        workspace["id"],
        email="agent-tool-member@example.com",
        role="member",
    )
    _seed_document(session, workspace_id=UUID(workspace["id"]))

    create_response = client.post(
        f"/workspaces/{workspace['id']}/agent-runs",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={"objective": "billing API 502 after deployment"},
    )
    assert create_response.status_code == 200
    agent_run_id = create_response.json()["agent_run_id"]

    member_list = client.get(
        f"/workspaces/{workspace['id']}/agent-runs/{agent_run_id}/tool-calls",
        headers={"Authorization": f"Bearer {member_token}"},
    )
    assert member_list.status_code == 404

    owner_list = client.get(
        f"/workspaces/{workspace['id']}/agent-runs/{agent_run_id}/tool-calls",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert owner_list.status_code == 200
    assert len(owner_list.json()["items"]) >= 1


def test_agent_tool_calls_admin_can_view_member_run(agent_api_context) -> None:
    client, session, _provider = agent_api_context
    _owner, owner_token = _register(client, email="agent-tool-admin-owner@example.com")
    _admin, admin_token = _register(client, email="agent-tool-admin@example.com")
    _member, member_token = _register(client, email="agent-tool-admin-member@example.com")
    workspace = _create_workspace(client, owner_token, slug="agent-tool-admin-ws")
    _invite_member(
        client,
        owner_token,
        workspace["id"],
        email="agent-tool-admin@example.com",
        role="admin",
    )
    _invite_member(
        client,
        owner_token,
        workspace["id"],
        email="agent-tool-admin-member@example.com",
        role="member",
    )
    _seed_document(session, workspace_id=UUID(workspace["id"]))

    create_response = client.post(
        f"/workspaces/{workspace['id']}/agent-runs",
        headers={"Authorization": f"Bearer {member_token}"},
        json={"objective": "billing API 502 after deployment"},
    )
    assert create_response.status_code == 200
    agent_run_id = create_response.json()["agent_run_id"]

    admin_list = client.get(
        f"/workspaces/{workspace['id']}/agent-runs/{agent_run_id}/tool-calls",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert admin_list.status_code == 200
    assert len(admin_list.json()["items"]) >= 1


def test_agent_run_audit_truncates_long_objective(agent_api_context) -> None:
    client, session, _provider = agent_api_context
    _user, token = _register(client, email="agent-audit-truncate@example.com")
    workspace = _create_workspace(client, token, slug="agent-audit-truncate")
    _seed_document(session, workspace_id=UUID(workspace["id"]))
    long_objective = "billing 502 " + ("x" * OBJECTIVE_AUDIT_MAX_CHARS)

    response = client.post(
        f"/workspaces/{workspace['id']}/agent-runs",
        headers={"Authorization": f"Bearer {token}"},
        json={"objective": long_objective},
    )
    assert response.status_code == 200

    session.expire_all()
    audit_row = session.scalar(
        select(AuditLog).where(
            AuditLog.workspace_id == workspace["id"],
            AuditLog.event_type == AGENT_RUN_COMPLETED_EVENT,
        )
    )
    assert audit_row is not None
    assert len(audit_row.metadata_["objective"]) == OBJECTIVE_AUDIT_MAX_CHARS + 1
    assert audit_row.metadata_["objective"].endswith("…")


def test_agent_run_rejects_foreign_conversation_id(agent_api_context) -> None:
    client, session, _provider = agent_api_context
    from app.modules.rag.repository import RAGRepository

    _user_a, token_a = _register(client, email="agent-conv-a@example.com")
    _user_b, token_b = _register(client, email="agent-conv-b@example.com")
    workspace_a = _create_workspace(client, token_a, slug="agent-conv-a")
    workspace_b = _create_workspace(client, token_b, slug="agent-conv-b")

    foreign_conversation = RAGRepository(session).create_conversation(
        workspace_id=UUID(workspace_b["id"]),
        user_id=UUID(_user_b["id"]),
        mode=ConversationMode.RAG,
        title="Foreign conversation",
    )

    response = client.post(
        f"/workspaces/{workspace_a['id']}/agent-runs",
        headers={"Authorization": f"Bearer {token_a}"},
        json={
            "objective": "billing API 502 after deployment",
            "conversation_id": str(foreign_conversation.id),
        },
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"
