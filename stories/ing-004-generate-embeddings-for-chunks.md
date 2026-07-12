# ING-004 — Generate Embeddings for Chunks

> **Epic:** Epic 4: Ingestion Pipeline  
> **Story ID:** ING-004
> **Status:** completed
> **Completed:** 2026-07-12
> **Implementation note:** [ING-004](../docs/implementation-notes/ING-004.md)

**User Story**

> As the system, I want to generate vector embeddings for each chunk, so that semantic search works.

**Product Rationale**

Embeddings enable vector retrieval; must log usage (USAGE-002).

**Functional Requirements**

- Call embedding provider for each chunk (batch if supported)
- Store vector in pgvector column
- Record embedding model name on chunk or job
- Track embedding token usage per batch

**Acceptance Criteria**

- Given 10 chunks  
  When embedding generation completes  
  Then each chunk has a non-null embedding vector

- Given embedding API failure  
  When retry exhausts  
  Then job is marked failed with reason

**Priority:** P0  
**Dependencies:** ING-003, USAGE-002  
**Notes for Engineering:** Batch size configurable; abstract `EmbeddingProvider` interface.


---

[← Back to MVP Product Backlog](../MVP_PRODUCT_BACKLOG.md)
