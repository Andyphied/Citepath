# ADR-001: Backend Architecture Style

## Status

Accepted

## Context

Citepath MVP requires a backend that supports REST APIs, multi-tenant RBAC, async document ingestion, RAG queries, agent orchestration, and production concerns (migrations, tests, observability). The team is small and the MVP must ship a credible demo without operational overhead from distributed systems.

We must choose an architecture style and primary backend framework.

## Decision

Use a **modular monolith** implemented in **Python 3.11+ with FastAPI** (runtime image `python:3.11-slim`; `requires-python >=3.11`), organized by domain modules (`auth`, `workspaces`, `documents`, `ingestion`, `retrieval`, `rag`, `agents`, etc.) within a single deployable artifact. Run two processes from the same codebase: **API (Uvicorn)** and **Celery worker**.

## Consequences

**Positive:**
- Single repo, single deployment unit, simple local dev with Docker Compose
- FastAPI provides automatic OpenAPI, Pydantic validation, async-capable routes
- Clear module boundaries allow future extraction without upfront microservice cost
- Python ecosystem strength for AI/RAG libraries and PDF processing
- Shared domain models and transactions across ingestion and retrieval

**Negative:**
- API and worker scale together only by deploying more of each process type independently (acceptable for MVP)
- Monolith codebase requires discipline to enforce module dependency rules
- Python GIL less relevant here since LLM I/O is network-bound

## Alternatives Considered

| Alternative | Why not selected |
|-------------|------------------|
| **Microservices** | Premature for MVP: splits ingestion/RAG/agents across network boundaries, adds deployment complexity, distributed tracing needs, and cross-service tenancy enforcement — without MVP traffic justification |
| **Serverless-only backend** | Ingestion and agent runs exceed typical Lambda timeouts; cold starts hurt demo UX; local dev parity is weaker |
| **Django monolith** | Viable but heavier ORM conventions and slower OpenAPI-first workflow; FastAPI aligns better with typed API + AI service integration |
| **Node.js backend** | Weaker alignment with team Python AI tooling and PDF/chunking libraries; no compelling MVP advantage |

## Implementation Notes

- Enforce module boundaries documented in [04-module-boundaries.md](../04-module-boundaries.md)
- `infrastructure/` must not import domain modules
- Use Alembic for migrations; SQLAlchemy 2.0 style
- API routes are thin; business logic lives in `modules/*/service.py`
- Same Docker image for API and worker with different `CMD`
