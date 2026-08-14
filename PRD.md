# PRD: Citepath — Engineering Knowledge & Incident Response Assistant

## 1. Product Summary

**Citepath** is an AI-powered knowledge assistant for engineering teams. It connects to internal engineering documents, runbooks, incident reports, architecture notes, pull request summaries, deployment logs, and service documentation. It helps engineers quickly answer operational questions, investigate incidents, summarize technical context, and recommend next actions.

The product combines **RAG**, **AI agents**, **vector search**, **tool calling**, **multi-tenant backend architecture**, and **cloud infrastructure**.

The goal is not to build a simple chatbot. The goal is to build a production-style AI platform that can ingest technical knowledge, retrieve relevant context, reason across documents, and use tools to assist engineers during real operational workflows.

## 2. Product Positioning

**One-liner:**

> Citepath helps engineering teams search, understand, and act on their internal technical knowledge using AI agents and retrieval-augmented generation.

**Target users:**

* Backend engineers
* DevOps engineers
* Platform engineers
* Engineering managers
* SRE teams
* Startup CTOs
* Technical support engineers

**Primary use case:**

An engineer asks:

> “The billing API is returning intermittent 502s after the latest deployment. What changed recently, what runbook applies, and what should I check first?”

Citepath should retrieve relevant deployment notes, incident history, service docs, runbooks, and architecture context, then produce a grounded answer with citations and recommended next steps.

## 3. Why This Is a Strong Portfolio Project

This project shows principal-level engineering because it demonstrates:

* AI/LLM product architecture, not just prompt usage.
* RAG pipeline design with embeddings, chunking, metadata, and retrieval ranking.
* Agentic workflows with tools and controlled execution.
* Multi-tenant backend design.
* Production concerns: auth, observability, background jobs, rate limits, token cost tracking, retries, async processing, audit logs.
* Infrastructure ownership with Docker, Terraform, and cloud deployment.
* Strong API design and domain modeling.
* Clear system boundaries and tradeoffs.

## 4. Problem Statement

Engineering teams accumulate knowledge across many disconnected places:

* Notion or Confluence docs
* Markdown files
* GitHub repositories
* PR descriptions
* Incident postmortems
* Slack discussions
* Runbooks
* Deployment notes
* Architecture decision records

When something breaks or a new engineer joins, finding the right context is slow. Traditional search often fails because users do not know the exact keywords. Generic AI chatbots are risky because they hallucinate or answer without knowing the company’s actual system.

Citepath solves this by giving teams an AI assistant that answers using retrieved internal context, cites its sources, and can run controlled investigation tools.

## 5. Goals

### Business goals

* Help engineering teams reduce time spent searching for internal technical knowledge.
* Improve incident response speed.
* Make onboarding easier for new engineers.
* Provide a strong portfolio example of production-grade backend, AI, and cloud engineering.

### Product goals

* Allow users to upload or sync technical documents.
* Convert documents into searchable vector embeddings.
* Let users ask technical questions and receive grounded answers with citations.
* Provide AI agent tools for incident investigation workflows.
* Track token usage, retrieval quality, and response confidence.
* Support multi-tenant workspaces.

### Engineering goals

* Build a clean, scalable backend architecture.
* Separate ingestion, retrieval, agent orchestration, and user-facing APIs.
* Implement production-ready authentication and authorization.
* Use background workers for long-running ingestion tasks.
* Deploy with Docker and Terraform.
* Include tests, API docs, structured logs, metrics, and CI/CD.

## 6. Non-Goals

The first version will not support:

* Full Slack integration.
* Full GitHub OAuth sync.
* Real production incident automation.
* Automatic remediation actions.
* Fine-tuning models.
* Enterprise SSO.
* Complex billing.
* Real-time streaming logs from cloud providers.

These can be documented as future improvements.

## 7. User Personas

### Persona 1: Platform Engineer

Needs fast answers during incidents.

Wants to ask:

> “What services depend on the billing database?”

Needs:

* Service dependency context
* Relevant runbooks
* Past incident summaries
* Suggested next checks

### Persona 2: Backend Engineer

Needs technical context before making changes.

Wants to ask:

> “How does authentication work in the API gateway?”

Needs:

* Architecture docs
* Code-related notes
* ADRs
* API documentation

### Persona 3: Engineering Manager

Needs summarized engineering context.

Wants to ask:

> “Summarize the last three payment-related incidents and recurring causes.”

Needs:

* Incident summaries
* Pattern detection
* Action items
* Risk areas

### Persona 4: New Engineer

Needs onboarding help.

Wants to ask:

> “What should I read first to understand the notification service?”

Needs:

* Recommended docs
* Dependency map
* Key concepts
* Service owners

## 8. Core User Stories

### Document ingestion

As a workspace admin, I want to upload engineering documents so that Citepath can index my team’s knowledge.

Acceptance criteria:

* User can upload PDF, Markdown, TXT, or JSON files.
* System extracts text and metadata.
* System chunks the content.
* System generates embeddings.
* System stores chunks in a vector database.
* User can see ingestion status: pending, processing, completed, failed.

### Ask a question

As an engineer, I want to ask a question and receive an answer grounded in internal documents.

Acceptance criteria:

* User can enter a natural-language question.
* System retrieves relevant chunks.
* System generates an answer using retrieved context.
* Answer includes source citations.
* Answer includes confidence level.
* Answer does not claim unsupported facts.
* User can view which documents were used.

### Incident assistant

As an engineer, I want the assistant to guide me through incident investigation.

Acceptance criteria:

* User can start an “incident investigation” session.
* User can describe the issue.
* Agent retrieves relevant runbooks and past incidents.
* Agent suggests first checks.
* Agent can call safe tools such as:

  * search knowledge base
  * summarize deployment notes
  * list related services
  * extract action items
* Agent produces a structured investigation summary.

### Source citation

As a user, I want answers to include citations so I can verify them.

Acceptance criteria:

* Each answer includes references to source documents.
* Citations show document title, section, and chunk preview.
* User can click or inspect retrieved source chunks.
* If no strong context is found, assistant says it does not know.

### Workspace separation

As an admin, I want documents and conversations isolated by workspace.

Acceptance criteria:

* Users belong to one or more workspaces.
* Documents are scoped to a workspace.
* Vector search only retrieves chunks from the active workspace.
* Conversations are scoped to the workspace.
* Users cannot access documents from other workspaces.

### Usage and cost tracking

As an admin, I want to see token usage and AI cost estimates.

Acceptance criteria:

* System records prompt tokens, completion tokens, embedding tokens, and estimated cost.
* Usage is tracked per workspace and per user.
* Admin can view daily usage summary.
* Errors and retries are recorded.

## 9. MVP Features

### Authentication and workspace management

* Email/password or magic link authentication.
* Workspace creation.
* User roles:

  * Owner
  * Admin
  * Member
  * Viewer

### Document ingestion

* Upload documents.
* Extract text.
* Chunk documents.
* Generate embeddings.
* Store chunk metadata.
* Track ingestion jobs.

### RAG question answering

* Ask a question.
* Retrieve top-k chunks.
* Optional reranking.
* Generate answer.
* Return citations.
* Store conversation history.

### AI agent mode

* Agent can use controlled tools:

  * `search_knowledge_base`
  * `summarize_document`
  * `extract_action_items`
  * `compare_incidents`
  * `suggest_debugging_steps`
* Agent must cite sources.
* Agent cannot execute destructive actions.

### Admin dashboard

* Document status.
* User count.
* Recent questions.
* Token usage.
* Failed ingestion jobs.

### Observability

* Structured logs.
* Request IDs.
* Health check endpoint.
* Basic metrics endpoint.
* Background job monitoring.

## 10. Version 2 Features

* GitHub repository ingestion.
* Slack thread ingestion.
* Notion/Confluence sync.
* Service dependency graph.
* Incident timeline generator.
* Evaluation dashboard for RAG quality.
* Model comparison: OpenAI vs Claude.
* Prompt versioning UI.
* Advanced access controls.
* Team-level analytics.
* Streaming responses.
* SSO.

## 11. Functional Requirements

## 11.1 Authentication

Users must be able to register, log in, and access only their workspace data.

Minimum requirements:

* JWT-based authentication.
* Password hashing.
* Role-based access control.
* Workspace membership checks.
* API-level authorization middleware.

## 11.2 Document upload

Users must be able to upload files.

Supported MVP formats:

* `.md`
* `.txt`
* `.pdf`
* `.json`

Document fields:

* `id`
* `workspace_id`
* `uploaded_by`
* `title`
* `source_type`
* `file_type`
* `status`
* `created_at`
* `updated_at`

Statuses:

* `uploaded`
* `processing`
* `indexed`
* `failed`

## 11.3 Chunking

The ingestion pipeline must split documents into chunks.

Chunking strategy:

* Default chunk size: 800–1,200 tokens.
* Overlap: 100–200 tokens.
* Preserve metadata:

  * document title
  * section heading
  * page number, if PDF
  * source type
  * created date
  * workspace ID

## 11.4 Embeddings

System must generate embeddings for each chunk.

Requirements:

* Store embedding vector.
* Store original text.
* Store metadata.
* Support re-embedding if model changes.
* Track embedding model used.

Potential choices:

* OpenAI embeddings
* pgvector
* Qdrant
* Weaviate

For portfolio simplicity, I recommend:

> PostgreSQL + pgvector

This shows strong backend judgment because it keeps the MVP infrastructure lean while still demonstrating vector search.

## 11.5 Retrieval

System must retrieve relevant chunks for a user question.

Requirements:

* Query embedding generation.
* Vector similarity search.
* Workspace filtering.
* Metadata filtering by document type.
* Top-k retrieval.
* Optional hybrid search using keyword + vector search.
* Return chunk text, score, document metadata, and citation ID.

Recommended MVP:

* Top 8 vector results.
* Rerank or compress to top 4–5 context chunks.
* Use metadata filters when available.

## 11.6 Answer generation

The system must generate grounded answers.

Requirements:

* Use retrieved context.
* Include citations.
* Avoid unsupported claims.
* Include “I could not find enough context” when retrieval is weak.
* Return structured response:

  * answer
  * citations
  * confidence
  * suggested follow-up questions

## 11.7 Agent orchestration

The AI agent should reason through multi-step tasks using safe tools.

Agent tools:

```text
search_knowledge_base(query, filters)
summarize_document(document_id)
extract_action_items(document_id)
compare_incidents(incident_ids)
suggest_debugging_steps(service_name, symptom)
```

Agent rules:

* Must use retrieved sources for factual claims.
* Must cite sources.
* Must not invent internal system details.
* Must not perform real external side effects.
* Must return final structured output.

## 11.8 Conversations

System must store conversation history.

Conversation fields:

* `id`
* `workspace_id`
* `user_id`
* `title`
* `mode`
* `created_at`

Message fields:

* `id`
* `conversation_id`
* `role`
* `content`
* `metadata`
* `created_at`

## 11.9 Token and cost tracking

Every AI call should be logged.

Fields:

* `workspace_id`
* `user_id`
* `provider`
* `model`
* `operation`
* `prompt_tokens`
* `completion_tokens`
* `embedding_tokens`
* `estimated_cost`
* `latency_ms`
* `status`
* `created_at`

This is a very senior feature because it shows cost and production awareness.

## 12. Non-Functional Requirements

### Security

* Workspace isolation.
* Role-based access control.
* Secure file handling.
* No cross-tenant retrieval.
* Environment-based secrets.
* API rate limiting.
* Audit logs for sensitive actions.

### Reliability

* Ingestion jobs must be retryable.
* Failed jobs should store error reason.
* API should return clear error responses.
* Health checks for API, database, worker, and vector store.

### Scalability

* Async background workers for ingestion.
* Batch embedding generation.
* Database indexes on workspace and document fields.
* Pagination for documents and conversations.
* Ability to move from pgvector to dedicated vector DB later.

### Observability

* Request-scoped structured logs.
* Metrics for latency, error rate, token usage, ingestion duration.
* Tracing-ready architecture.
* Admin visibility into failed jobs.

### Maintainability

* Modular codebase.
* Clear domain boundaries.
* Typed schemas.
* Database migrations.
* Automated tests.
* Clear README and architecture docs.

## 13. Recommended Architecture

## 13.1 High-level components

```text
Frontend / Admin UI
        |
        v
FastAPI Backend
        |
        |---- Auth & RBAC Service
        |---- Workspace Service
        |---- Document Service
        |---- Ingestion Orchestrator
        |---- Retrieval Service
        |---- Agent Service
        |---- Usage Tracking Service
        |
        v
PostgreSQL + pgvector
        |
        v
Redis Queue / Celery Worker
        |
        v
OpenAI / Claude / Embedding Provider
```

## 13.2 Backend modules

Suggested folder structure:

```text
app/
  api/
    routes/
      auth.py
      workspaces.py
      documents.py
      conversations.py
      queries.py
      agents.py
      admin.py
  core/
    config.py
    security.py
    logging.py
    errors.py
  domain/
    users/
    workspaces/
    documents/
    ingestion/
    retrieval/
    agents/
    usage/
  infrastructure/
    database/
    vector_store/
    llm/
    queue/
    storage/
  workers/
    ingestion_worker.py
  tests/
```

This structure shows senior-level organization.

## 14. Suggested Tech Stack

### Backend

* Python
* FastAPI
* Pydantic
* SQLAlchemy
* Alembic
* PostgreSQL
* pgvector
* Redis
* Celery or RQ

### AI

* OpenAI API
* Claude/Anthropic API
* LangChain or lightweight custom orchestration
* Embeddings
* RAG pipeline
* Prompt templates
* Token tracking

### Infrastructure

* Docker
* Docker Compose
* Terraform
* AWS ECS Fargate or GCP Cloud Run
* Managed PostgreSQL
* S3/GCS file storage
* GitHub Actions

### Frontend

For portfolio purposes, keep this simple:

* Next.js
* React
* Tailwind

Or skip complex frontend and build:

* Swagger/OpenAPI docs
* Minimal admin UI
* Clean demo screenshots

Because your portfolio is backend/platform focused, the frontend does not need to be fancy.

## 15. Data Model

Core tables:

```text
users
workspaces
workspace_members
documents
document_chunks
conversations
messages
agent_runs
agent_tool_calls
usage_events
audit_logs
ingestion_jobs
```

### Example entities

```text
users
- id
- email
- password_hash
- created_at

workspaces
- id
- name
- slug
- created_at

workspace_members
- workspace_id
- user_id
- role

documents
- id
- workspace_id
- uploaded_by
- title
- source_type
- file_type
- storage_path
- status
- error_message
- created_at

document_chunks
- id
- workspace_id
- document_id
- chunk_index
- content
- embedding
- metadata
- token_count
- created_at

conversations
- id
- workspace_id
- user_id
- mode
- title
- created_at

messages
- id
- conversation_id
- role
- content
- citations
- metadata
- created_at

agent_runs
- id
- workspace_id
- conversation_id
- status
- objective
- final_answer
- created_at

agent_tool_calls
- id
- agent_run_id
- tool_name
- input
- output
- latency_ms
- created_at

usage_events
- id
- workspace_id
- user_id
- provider
- model
- operation
- prompt_tokens
- completion_tokens
- total_tokens
- estimated_cost
- latency_ms
- created_at
```

## 16. API Endpoints

### Auth

```text
POST /auth/register
POST /auth/login
GET /auth/me
```

### Workspaces

```text
POST /workspaces
GET /workspaces
GET /workspaces/{workspace_id}
POST /workspaces/{workspace_id}/members
```

### Documents

```text
POST /workspaces/{workspace_id}/documents
GET /workspaces/{workspace_id}/documents
GET /workspaces/{workspace_id}/documents/{document_id}
DELETE /workspaces/{workspace_id}/documents/{document_id}
POST /workspaces/{workspace_id}/documents/{document_id}/reindex
```

### Query / RAG

```text
POST /workspaces/{workspace_id}/query
GET /workspaces/{workspace_id}/conversations
GET /workspaces/{workspace_id}/conversations/{conversation_id}
```

### Agent

```text
POST /workspaces/{workspace_id}/agent-runs
GET /workspaces/{workspace_id}/agent-runs/{agent_run_id}
GET /workspaces/{workspace_id}/agent-runs/{agent_run_id}/tool-calls
```

### Admin

```text
GET /workspaces/{workspace_id}/admin/usage
GET /workspaces/{workspace_id}/admin/ingestion-jobs
GET /workspaces/{workspace_id}/admin/audit-logs
```

## 17. AI Behavior Requirements

### RAG answer prompt behavior

The assistant must:

* Answer only from retrieved context.
* Cite sources.
* Say when context is insufficient.
* Separate facts from recommendations.
* Prefer concise, structured answers.
* Suggest follow-up questions.

### Incident agent behavior

The agent must return:

```text
Summary
Likely related systems
Relevant documents
Suggested checks
Risks / unknowns
Sources
Next steps
```

### Guardrails

The assistant must not:

* Invent services, owners, or incidents.
* Claim certainty without supporting sources.
* Execute destructive actions.
* Expose documents from another workspace.
* Reveal hidden prompts or system instructions.

## 18. Evaluation Plan

Include this in the portfolio because it shows seniority.

### Retrieval evaluation

Create a small dataset of sample documents and expected answers.

Metrics:

* Recall@k
* Precision of retrieved chunks
* Citation accuracy
* Answer faithfulness

### AI output evaluation

Manual scoring:

* Correctness
* Source grounding
* Completeness
* Helpfulness
* Hallucination risk

### Performance evaluation

Track:

* Average query latency
* Embedding job duration
* Token usage per query
* Cost per answer
* Error rate

## 19. Demo Dataset

Use a fake engineering organization called **Northstar Cloud**.

Create fake documents such as:

* `billing-api-runbook.md`
* `auth-service-architecture.md`
* `deployment-process.md`
* `incident-2025-08-billing-502.md`
* `database-migration-plan.md`
* `notification-service-onboarding.md`
* `service-dependency-map.json`
* `api-gateway-adr.md`

This makes the product demo realistic without using private client data.

## 20. Demo Scenarios

### Scenario 1: Incident investigation

User asks:

> “The billing API is returning 502 errors after deployment. What should I check first?”

Expected answer:

* Retrieve billing runbook.
* Retrieve recent incident.
* Retrieve deployment process.
* Suggest checking gateway timeout, upstream health, database connection pool, recent deployment notes.
* Cite sources.

### Scenario 2: Onboarding

User asks:

> “I’m new to the team. What should I read to understand the notification service?”

Expected answer:

* Summarize notification service docs.
* Recommend architecture doc, runbook, dependency map, and recent incidents.
* Cite sources.

### Scenario 3: Architecture reasoning

User asks:

> “What services depend on the auth service, and what risks should we consider before changing token expiry?”

Expected answer:

* Retrieve auth architecture.
* Retrieve dependency map.
* Explain impacted services.
* Suggest safe rollout plan.

### Scenario 4: Postmortem summary

User asks:

> “Summarize the recurring causes from payment-related incidents.”

Expected answer:

* Retrieve multiple incident docs.
* Compare causes.
* List patterns.
* Suggest preventive actions.

## 21. Milestones

### Milestone 1: Backend foundation

* FastAPI project setup.
* Auth.
* Workspaces.
* PostgreSQL schema.
* Docker Compose.
* Health checks.
* API docs.

### Milestone 2: Document ingestion

* Upload documents.
* Text extraction.
* Chunking.
* Embeddings.
* pgvector storage.
* Background worker.

### Milestone 3: RAG Q&A

* Query endpoint.
* Vector retrieval.
* Answer generation.
* Citations.
* Conversation storage.
* Usage tracking.

### Milestone 4: Agent workflows

* Agent run endpoint.
* Tool registry.
* Search tool.
* Summarize tool.
* Incident investigation flow.
* Tool call logging.

### Milestone 5: Admin and observability

* Usage dashboard.
* Ingestion job status.
* Audit logs.
* Structured logging.
* Tests.

### Milestone 6: Cloud deployment

* Docker production config.
* Terraform infrastructure.
* GitHub Actions CI/CD.
* Deployment docs.
* Architecture diagram.

## 22. Acceptance Criteria for Portfolio Readiness

The project is portfolio-ready when:

* A user can upload documents.
* Documents are chunked, embedded, and indexed.
* A user can ask questions and receive grounded answers with citations.
* Agent mode can perform at least three tool-based steps.
* Workspace isolation works.
* Token usage is tracked.
* Docker Compose runs locally.
* README explains architecture and tradeoffs.
* Tests cover core services.
* Terraform files demonstrate deployable infrastructure.
* Screenshots and diagrams are available for Upwork portfolio.

## 23. Principal-Level Implementation Details to Highlight

These are the details that will make the project look senior/principal-level:

### 1. Clean architecture

Do not put everything in route handlers. Separate:

* API layer
* domain services
* repository layer
* infrastructure adapters
* LLM providers
* vector store abstraction
* agent tools

### 2. Provider abstraction

Create interfaces like:

```text
EmbeddingProvider
LLMProvider
VectorStore
DocumentStorage
ToolRegistry
```

This shows you can design systems that can switch from OpenAI to Claude, pgvector to Qdrant, local storage to S3, etc.

### 3. Workspace isolation

Every query, document, chunk, and agent run must be scoped by `workspace_id`.

This is very important. It shows security awareness.

### 4. Token and cost tracking

Log every LLM and embedding call.

This shows production AI awareness.

### 5. Citation grounding

Do not return generic AI answers. Always show sources.

This shows responsible AI engineering.

### 6. Async ingestion pipeline

Use background jobs for document processing.

This shows scalability.

### 7. Observability

Use structured logs, request IDs, error tracking, and health checks.

This shows platform maturity.

### 8. Evaluation harness

Create a simple test dataset with expected questions and expected sources.

This shows AI product judgment beyond basic implementation.

## 24. Suggested GitHub README Sections

Use this structure:

```text
# Citepath

## Overview
## Problem
## Demo
## Architecture
## Core Features
## AI/RAG Pipeline
## Agent Workflow
## Data Model
## API Documentation
## Infrastructure
## Local Setup
## Testing
## Evaluation
## Security Considerations
## Design Decisions
## Tradeoffs
## Future Improvements
```

## 25. Upwork Portfolio Entry

When the project is finished, add this to Upwork.

**Title**

> AI Agent & RAG Knowledge Platform

**Role**

> Principal Backend & AI Engineer

**Description**

> Built a production-style AI knowledge platform for engineering teams using RAG, vector search, AI agents, OpenAI/Claude APIs, and FastAPI. The system ingests technical documents, generates embeddings, retrieves relevant context, and produces grounded answers with citations. Includes token optimization, tool-based agent workflows, workspace isolation, Docker deployment, and Terraform-based cloud infrastructure.

**Skills**

> Python, FastAPI, OpenAI API, LangChain, RAG, Vector Database, Terraform, Docker, AWS

## 26. Final Recommendation

Build this as a **backend-first product** with a clean minimal UI.

Do not spend too much time making the frontend beautiful. Spend your effort on:

* architecture
* ingestion pipeline
* retrieval quality
* agent tools
* citations
* token tracking
* multi-tenancy
* Terraform
* README
* diagrams

That is what will communicate principal-level skill.
