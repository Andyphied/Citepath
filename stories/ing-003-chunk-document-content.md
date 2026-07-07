# ING-003 — Chunk Document Content

> **Epic:** Epic 4: Ingestion Pipeline  
> **Story ID:** ING-003
> **Status:** completed
> **Completed:** 2026-07-07
> **Implementation note:** [ING-003](../docs/implementation-notes/ING-003.md)

**User Story**

> As the system, I want to split extracted text into overlapping chunks, so that retrieval can find relevant passages.

**Product Rationale**

Chunk quality directly affects RAG answer quality; core pipeline step.

**Functional Requirements**

- Chunk size: 800–1,200 tokens (configurable)
- Overlap: 100–200 tokens
- Preserve metadata: document title, section heading (if detectable), page number (PDF), source type, workspace_id, document_id, chunk_index
- Token counting via same tokenizer as embedding model approximation

**Acceptance Criteria**

- Given a 5,000-token document  
  When chunking runs  
  Then multiple chunks are created with sequential `chunk_index` and overlap

- Given metadata from PDF page 2  
  When chunk is stored  
  Then metadata includes `page_number: 2`

**Priority:** P0  
**Dependencies:** ING-002  
**Notes for Engineering:** Split on paragraph boundaries where possible before hard token cut.


---

[← Back to MVP Product Backlog](../MVP_PRODUCT_BACKLOG.md)
