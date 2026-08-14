"""INFRA-008: OpenAPI /docs, /redoc, Bearer JWT, and key route examples."""

from fastapi.testclient import TestClient

from app.main import create_app

# Core MVP paths that must appear in the generated schema.
REQUIRED_PATHS = {
    "/health",
    "/health/ready",
    "/metrics",
    "/auth/register",
    "/auth/login",
    "/auth/logout",
    "/auth/me",
    "/workspaces",
    "/workspaces/{workspace_id}",
    "/workspaces/{workspace_id}/members",
    "/workspaces/{workspace_id}/members/{user_id}",
    "/workspaces/{workspace_id}/documents",
    "/workspaces/{workspace_id}/documents/{document_id}",
    "/workspaces/{workspace_id}/documents/{document_id}/reindex",
    "/workspaces/{workspace_id}/ingestion-jobs/{job_id}",
    "/workspaces/{workspace_id}/query",
    "/workspaces/{workspace_id}/conversations",
    "/workspaces/{workspace_id}/conversations/{conversation_id}",
    "/workspaces/{workspace_id}/agent-runs",
    "/workspaces/{workspace_id}/agent-runs/{agent_run_id}",
    "/workspaces/{workspace_id}/agent-runs/{agent_run_id}/tool-calls",
    "/workspaces/{workspace_id}/admin/usage",
    "/workspaces/{workspace_id}/admin/documents-overview",
    "/workspaces/{workspace_id}/admin/ingestion-jobs",
    "/workspaces/{workspace_id}/admin/recent-questions",
    "/workspaces/{workspace_id}/admin/failed-jobs",
    "/workspaces/{workspace_id}/admin/audit-logs",
}

REQUIRED_TAGS = {
    "health",
    "metrics",
    "auth",
    "workspaces",
    "documents",
    "ingestion",
    "queries",
    "conversations",
    "agent-runs",
    "admin",
}


def test_docs_and_redoc_are_available(minimal_env) -> None:
    client = TestClient(create_app())

    docs = client.get("/docs")
    redoc = client.get("/redoc")
    openapi = client.get("/openapi.json")

    assert docs.status_code == 200
    assert "text/html" in docs.headers["content-type"]
    assert redoc.status_code == 200
    assert "text/html" in redoc.headers["content-type"]
    assert openapi.status_code == 200
    assert openapi.headers["content-type"].startswith("application/json")


def test_openapi_metadata_and_bearer_jwt_scheme(minimal_env) -> None:
    client = TestClient(create_app())
    schema = client.get("/openapi.json").json()

    assert schema["info"]["title"] == "Citepath"
    assert schema["info"]["version"] == "0.1.0"
    description = schema["info"]["description"]
    assert "Bearer" in description
    assert "workspace" in description.lower()

    security_schemes = schema["components"]["securitySchemes"]
    assert "BearerJWT" in security_schemes
    bearer = security_schemes["BearerJWT"]
    assert bearer["type"] == "http"
    assert bearer["scheme"] == "bearer"
    assert bearer.get("bearerFormat") == "JWT"

    tag_names = {tag["name"] for tag in schema.get("tags", [])}
    assert REQUIRED_TAGS.issubset(tag_names)


def test_openapi_lists_mvp_endpoints(minimal_env) -> None:
    client = TestClient(create_app())
    paths = set(client.get("/openapi.json").json()["paths"])

    missing = REQUIRED_PATHS - paths
    assert not missing, f"Missing OpenAPI paths: {sorted(missing)}"


def test_query_and_agent_run_include_examples(minimal_env) -> None:
    client = TestClient(create_app())
    schema = client.get("/openapi.json").json()

    query_path = "/workspaces/{workspace_id}/query"
    agent_path = "/workspaces/{workspace_id}/agent-runs"
    query_post = schema["paths"][query_path]["post"]
    agent_post = schema["paths"][agent_path]["post"]

    query_body = query_post["requestBody"]["content"]["application/json"]
    agent_body = agent_post["requestBody"]["content"]["application/json"]

    assert "examples" in query_body
    assert "examples" in agent_body
    assert "demo_billing_502" in query_body["examples"]
    assert "demo_billing_investigation" in agent_body["examples"]

    example_question = query_body["examples"]["demo_billing_502"]["value"][
        "question"
    ]
    assert "billing 502" in example_question.lower()

    objective = agent_body["examples"]["demo_billing_investigation"]["value"][
        "objective"
    ]
    assert "billing" in objective.lower()

    assert query_post.get("security") == [{"BearerJWT": []}]
    assert agent_post.get("security") == [{"BearerJWT": []}]
