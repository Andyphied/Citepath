# INFRA-004 Implementation Note

## Summary

Added Northstar Cloud demo fixtures under `demo_data/` and an idempotent `scripts/seed_demo.py` that creates a demo user, workspace, uploads all fixtures, and runs ingestion synchronously (no Celery worker required for seeding).

## Files Changed

| File | Change |
|------|--------|
| `demo_data/*.md`, `demo_data/service-dependency-map.json` | PRD §19 fixtures |
| `scripts/seed_demo.py` | Idempotent seed script |
| `scripts/__init__.py` | Package marker for `python -m scripts.seed_demo` |
| `README.md` | Seed usage and demo question |
| `tests/integration/test_seed_demo.py` | Idempotency + billing query retrieval test |

## Behavior Added

- `python -m scripts.seed_demo` creates `demo@northstar.cloud`, workspace slug `northstar-cloud`, indexes 8 demo documents.
- Re-run skips documents already in `indexed` status.
- Ingestion runs via direct `process_ingestion_job()` call for deterministic local/demo setup.

## Demo Credentials

- Email: `demo@northstar.cloud`
- Default password: `northstar-demo` (override with `--password` or `DEMO_SEED_PASSWORD`)

## Tests Added

- `tests/integration/test_seed_demo.py` — full seed, idempotent re-run, retrieval returns chunks for billing 502 question

## Follow-up Items

- Optional CI smoke job invoking seed + query endpoint with mocked LLM providers.
