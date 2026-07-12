# ING-005 — Store Chunks in Vector Database

> **Epic:** Epic 4: Ingestion Pipeline  
> **Story ID:** ING-005
> **Status:** completed
> **Completed:** 2026-07-12
> **Implementation note:** [ING-005](../docs/implementation-notes/ING-005.md)

**User Story**

> As the system, I want to persist chunks with embeddings in PostgreSQL/pgvector, so that retrieval can query them.

**Product Rationale**

Durable chunk storage is required for all downstream RAG and agent tools.

**Functional Requirements**

- Insert into `document_chunks` with workspace_id, document_id, content, embedding, metadata, token_count
- Index on workspace_id and document_id
- pgvector index for similarity search (IVFFlat or HNSW per pgvector version)

**Acceptance Criteria**

- Given successful embedding  
  When storage completes  
  Then chunks are queryable via vector search in the same workspace

**Priority:** P0  
**Dependencies:** ING-004  
**Notes for Engineering:** Migration creates vector extension and index; document re-index deletes old chunks first.


---

[← Back to MVP Product Backlog](../MVP_PRODUCT_BACKLOG.md)
