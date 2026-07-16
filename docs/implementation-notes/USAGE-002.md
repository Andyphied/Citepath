# USAGE-002 Implementation Note

## Summary

Completed embedding usage logging for both ingestion and query paths. Verified and extended ING-004 ingestion batch logging to use `embedding_document`, added `embedding_query` / `embedding_document` enum values with migration, introduced a RET-001-ready `embed_query_text()` helper, and added job-level embedding token aggregation.

## Files Changed

| File | Purpose |
|------|---------|
| `app/infrastructure/db/enums.py` | Added `EMBEDDING_DOCUMENT`, `EMBEDDING_QUERY`; kept legacy `EMBEDDING` |
| `app/migrations/versions/003_add_embedding_usage_operations.py` | Enum migration and backfill of legacy rows |
| `app/modules/ingestion/embeddings.py` | Switched ingestion usage logging to `embedding_document` |
| `app/modules/retrieval/__init__.py` | Retrieval module package |
| `app/modules/retrieval/embeddings.py` | Query embed-and-log helper for RET-001 |
| `app/modules/usage/repository.py` | `sum_embedding_tokens_for_job()` |
| `app/modules/usage/service.py` | Delegates job token aggregation |
| `tests/unit/test_ingestion_embeddings.py` | Updated operation assertions |
| `tests/unit/test_retrieval_embeddings.py` | Query-side usage logging unit tests |
| `tests/unit/test_usage_repository.py` | Repository/service aggregation unit tests |
| `tests/integration/test_ingestion_usage_events.py` | 20-chunk ingestion aggregate acceptance test |

## Behavior Added

- Ingestion batches log one `usage_events` row per provider call with `operation=embedding_document`, `embedding_tokens` from provider, and metadata `{document_id, job_id, batch_size}`.
- Failed ingestion batches log `status=failed` before returning `EmbeddingError`.
- `embed_query_text()` embeds a single question, logs `operation=embedding_query` with caller metadata (e.g. `conversation_id`) plus `query_length`, and returns `QueryEmbeddingResult` or `QueryEmbeddingError`.
- `UsageService.sum_embedding_tokens_for_job(workspace_id, job_id)` sums `embedding_tokens` across document-ingestion events for a job (includes legacy `embedding` rows).

## Tests Added

**Unit:**

- `tests/unit/test_ingestion_embeddings.py` — updated for `embedding_document`
- `tests/unit/test_retrieval_embeddings.py` — success, provider failure, vector-count mismatch
- `tests/unit/test_usage_repository.py` — aggregation delegation

**Integration:**

- `tests/integration/test_ingestion_usage_events.py` — 20 chunks in 3 batches → 60 aggregate tokens queryable per job

## Decisions Made

- Reconciled story enum (`embedding_document`, `embedding_query`) with ADR-007 by extending the PostgreSQL enum rather than overloading generic `embedding`. Legacy `embedding` retained for downgrade safety; migration backfills existing rows to `embedding_document`.
- Ingestion logging remains in `modules/ingestion/embeddings.py` (ING-004); query logging lives in `modules/retrieval/embeddings.py` as the RET-001 contract without implementing vector search.
- One usage event per batch call when provider returns usage once (per story note).
- Usage logging failures remain non-blocking per ADR-007.

## Known Limitations

- No USAGE-004 admin summary or workspace-day aggregation in this story.
- Query helper does not cache embeddings across requests (RET-001 may add request-scoped cache).
- Job aggregation filters on `metadata.job_id` JSON; no dedicated column index.

## Follow-up Items

- **RET-001:** Wire `embed_query_text()` into `RetrievalService` and RAG entry points.
- **USAGE-004:** Expose workspace usage summaries using `usage_events` aggregates.
- **ADR-007:** Consider documenting granular embedding operations in the ADR text.

## Verification

```bash
pip install -e ".[dev]"
pytest tests/unit/test_ingestion_embeddings.py \
  tests/unit/test_retrieval_embeddings.py \
  tests/unit/test_usage_repository.py \
  tests/unit/test_usage_service.py -v
```

Docker integration (optional):

```bash
pytest tests/integration/test_ingestion_usage_events.py -v
```

## Fix Cycle 1 (Gate 4)

**Review finding:** Unrelated `stories/doc-007-document-status-display.md` completion marker was mixed into the USAGE-002 working tree.

**Resolution:** Committed DOC-007 completion separately as `5673b89` (`docs(doc): mark DOC-007 story complete`). USAGE-002 changeset no longer includes DOC-007 files.
