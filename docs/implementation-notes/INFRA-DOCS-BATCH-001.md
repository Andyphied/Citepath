# INFRA-DOCS-BATCH-001 Implementation Note

Batch: **INFRA-007** (README & architecture docs) + **INFRA-008** (OpenAPI polish)

**Status:** Review fix cycle applied — stories remain
`in_progress` until accepted. Do **not** mark completed.

## Summary

Expanded the root README into a reviewer-friendly under-30-minute local demo
path (real LLM key → Compose → sync seed → JWT → query/agent), with env vars,
testing, security / workspace isolation, and design tradeoffs linked to the
architecture package (ADRs + Mermaid). Polished FastAPI OpenAPI metadata so
`/docs` and `/redoc` document Bearer JWT, MVP routes/schemas, and examples on
query + agent-run.

## Review fix cycle

| Prior must-fix | How fixed | File evidence |
|-----------------|-----------|---------------|
| README treated LLM key as optional for under-30-min live answers | Step **0** requires a **real** `OPENAI_API_KEY` (or Anthropic) before seed + query; placeholder called out as boot-only | `README.md` Quick start §0–§3; `.env.example` LLM comments |
| Unclear how to set key in Compose / recreate | Compose interpolates `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` / `LLM_PROVIDER` from `.env`/shell; README documents `docker compose up -d --force-recreate api` | `docker-compose.yml` `x-app-environment`; `README.md` §0 |
| Seed vs Celery worker unclear | Documented sync in-process ingestion (`process_ingestion_job`); Celery worker **not** required for seed | `README.md` §2; Known Limitations below |
| Architecture package linked but untracked on clean checkout | Included linked package in this batch’s deliverable set (docs index, 01–03, 07, 13, linked ADRs, diagrams) | Files Changed table; untracked paths now in batch scope for commit |
| Python version said 3.12 vs image/pyproject 3.11 | Aligned to **3.11+** / `python:3.11-slim` | `README.md` Architecture table; `docs/README.md`; `docs/adr/ADR-001-*.md` |
| Flower no-auth / local-only warning missing | Restored next to Flower URL | `README.md` service table |
| Demo user/password not labeled local-only | Labeled **local demo credentials only**; change before shared/internet-facing deploy | `README.md` §2 |
| `/docs` `/redoc` `/openapi.json` + `persistAuthorization` risk not noted | Local-demo / edge-restriction notes; JWT browser persistence called out | `README.md` API documentation; `app/main.py` `OPENAPI_DESCRIPTION`; `docs/06-api-design.md` |
| OpenAPI isolation blurb omitted non-member 403 | Added non-members → **403**; cross-workspace resource → **404** | `app/main.py` `OPENAPI_DESCRIPTION`; `docs/06-api-design.md` |

## INFRA-007 — README and architecture documentation

### Behavior Added

- Root `README.md` now covers overview, quick start (key → Compose → seed → JWT),
  architecture mermaid, env var tables, security/isolation, design tradeoffs
  (pgvector, JWT, chunking), API/docs links, testing, and doc map.
- Architecture package index + overview/diagram/RAG/testing docs and linked ADRs
  are part of this batch so README links resolve on a clean checkout.
- `.env.example` documents chunk/embedding knobs and real-key requirement for demo.
- Clarified in `docs/06-api-design.md` that the live app mounts routes at `/`
  (no `/api/v1` prefix) while keeping the narrative contract otherwise.

### Decisions Made

- Did **not** invent greenfield architecture; tradeoffs cite ADR-001/002/004/005/006/008
  and existing `docs/07` / `docs/09`.
- Documented actual Compose seed path via `docker compose exec api python -m scripts.seed_demo`.
- Seed uses sync in-process ingestion; async upload path still uses Celery worker.
- Compose placeholder key remains the default for boot; demo path requires a real key.

## INFRA-008 — OpenAPI API documentation

### Behavior Added

- App factory OpenAPI: title, version `0.1.0`, rich description (auth +
  isolation + local-demo docs note), tagged groups, `persistAuthorization` in
  Swagger UI.
- Explicit `BearerJWT` HTTP bearer scheme (`bearerFormat: JWT`) via
  `HTTPBearer(scheme_name="BearerJWT")` and custom OpenAPI merge.
- Request `openapi_examples` on `POST .../query` and `POST .../agent-runs`;
  schema-level examples on request/response models.
- Route summaries/docstrings for key RAG/agent endpoints.

### Tests Added

- `tests/unit/test_openapi.py`
  - `/docs`, `/redoc`, `/openapi.json` return 200
  - `BearerJWT` security scheme present
  - All MVP paths listed
  - Query/agent-run examples + `security: BearerJWT` on those operations

## Files Changed

| File | Purpose |
|------|---------|
| `README.md` | Reviewer quick start + security/tradeoffs (review fixes) |
| `.env.example` | Chunk/embedding vars + real LLM key for demo |
| `docker-compose.yml` | Interpolate LLM key/provider from `.env`/shell |
| `docs/README.md` | Architecture index; Python 3.11+ |
| `docs/01-system-overview.md` | Architecture package (linked from README) |
| `docs/02-architecture-diagram.md` | System context narrative |
| `docs/03-container-diagram.md` | Container view |
| `docs/07-rag-architecture.md` | Retrieval & grounding (tradeoff link) |
| `docs/13-testing-strategy.md` | Testing strategy (README Testing link) |
| `docs/adr/ADR-001-backend-architecture-style.md` | Linked ADR; Python 3.11+ |
| `docs/adr/ADR-002-vector-store-choice.md` | Linked ADR |
| `docs/adr/ADR-003-llm-provider-abstraction.md` | Linked ADR |
| `docs/adr/ADR-004-background-job-processing.md` | Linked ADR |
| `docs/adr/ADR-006-agent-tool-execution-model.md` | Linked ADR |
| `docs/adr/ADR-008-deployment-target.md` | Linked ADR |
| `docs/diagrams/*.mmd` | Mermaid sources linked from docs/README |
| `docs/06-api-design.md` | OpenAPI URLs, root mount, local-demo notes |
| `app/main.py` | OpenAPI metadata + BearerJWT + isolation/docs notes |
| `app/api/deps.py` | Named BearerJWT HTTPBearer |
| `app/api/routes/queries.py` | Examples + summary |
| `app/api/routes/agent_runs.py` | Examples + summary |
| `app/modules/rag/schemas.py` | Schema examples |
| `app/modules/agents/schemas.py` | Schema examples |
| `tests/unit/test_openapi.py` | INFRA-008 verification |
| `docs/implementation-notes/INFRA-DOCS-BATCH-001.md` | This note |
| `stories/infra-007-*.md`, `stories/infra-008-*.md` | remain `in_progress` |

## Known Limitations

- README demo curl path assumes `jq` on the host for the token/workspace steps.
- **Real** provider API key is a hard prerequisite for seed (sync embed/index) and
  live grounded answers; Compose default placeholder only boots the stack.
- Seed runs ingestion synchronously in the `api` process — worker not needed for
  seed; document upload → Celery still needs `worker`.
- OpenAPI examples use placeholder UUIDs; not live Northstar IDs.
- Flower has no auth — local-only; do not expose beyond localhost.
- Terraform / INFRA-006 intentionally out of scope for this batch.
- Stories not marked `completed`.

## Follow-up Items

- Re-review after this fix cycle.
- Commit should include architecture package files listed above.
- INFRA-006 Terraform scaffold (separate story).
- Optional: add README smoke script wrapping login → query.

## Verification

```bash
docker compose config -q
.venv/bin/pytest tests/unit/test_openapi.py -v
```
