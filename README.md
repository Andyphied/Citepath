# AtlasOps AI

Workspace-scoped RAG and incident investigation backend.

## Local stack

```bash
docker compose up --build
```

API: http://localhost:8000  
Health: http://localhost:8000/health/ready  
Web UI: http://localhost:3000 (Next.js app shell — see `web/README.md`)

### Worker visibility (OBS-007)

Compose wires these into `api` and `worker` (override via shell or `.env`):

| Variable | Default | Purpose |
|----------|---------|---------|
| `WORKER_HEARTBEAT_INTERVAL_SECONDS` | `300` | Structured `worker_heartbeat` log interval |
| `CELERY_DEFAULT_QUEUE` | `celery` | Celery queue name and Redis `LLEN` key for `/health/ready.queue_depth` |

```bash
# Faster local heartbeats while debugging
WORKER_HEARTBEAT_INTERVAL_SECONDS=60 docker compose up --build
```

Confirm the worker is alive: `docker compose logs -f worker | grep worker_heartbeat`  
Queue depth: `curl -s http://localhost:8000/health/ready | jq .queue_depth`  
Optional Flower (local only, no auth on host :5555): `docker compose --profile flower up` → http://localhost:5555

Local web dev (without rebuilding the `web` image):

```bash
cd web
cp .env.example .env.local
npm install
npm run dev
```

## Demo dataset (Northstar Cloud)

Seed the portfolio demo workspace, user, and documents:

```bash
# Requires DATABASE_URL, REDIS_URL, JWT_SECRET_KEY, STORAGE_BACKEND, LLM_PROVIDER, OPENAI_API_KEY
python -m scripts.seed_demo
```

Optional:

```bash
python -m scripts.seed_demo --password "your-demo-password"
# or set DEMO_SEED_PASSWORD
```

Creates:

- User: `demo@northstar.cloud` (default password `northstar-demo`)
- Workspace: **Northstar Cloud** (`northstar-cloud` slug)
- Documents from `demo_data/` (runbooks, incidents, architecture notes)

Re-running the script is idempotent — already indexed documents are skipped.

### Demo question

After seeding and ingestion completes, ask:

> What should I check for billing 502 errors after deployment?

Expected: grounded answer with citations from billing runbook / incident docs.

## Usage cost estimates

AtlasOps records token usage on every LLM and embedding call and attaches an
`estimated_cost_usd` using a static price table in
`app/modules/usage/cost_calculator.py` (USD per 1K tokens, blended per model).

These figures are **approximate portfolio/demo estimates, not invoices**. They
may diverge from provider billing because rates are updated manually, input and
output tokens share one rate, and unknown models leave cost unset. Prefer
provider invoices for real spend.

Admin summary (Owner/Admin): `GET /workspaces/{workspace_id}/admin/usage`  
Also: `documents-overview`, `ingestion-jobs`, `recent-questions`, `failed-jobs`, `audit-logs` under `/workspaces/{workspace_id}/admin/`.
(default last 7 days).

## Tests

```bash
pytest tests/unit -q
pytest tests/integration tests/api tests/security -q  # requires Docker (testcontainers)
```

CI (`.github/workflows/ci.yml`) uses the same directory globs: unit job covers `tests/unit` (including `test_agent_*.py`); integration job covers `tests/api`, `tests/integration`, and `tests/security` (including agent API/isolation suites). API/security tests skip when Docker is unavailable.
