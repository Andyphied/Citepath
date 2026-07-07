# ING-002 — Extract Text from Documents

> **Epic:** Epic 4: Ingestion Pipeline  
> **Story ID:** ING-002
> **Status:** completed
> **Completed:** 2026-07-07
> **Implementation note:** [ING-002](../docs/implementation-notes/ING-002.md)

**User Story**

> As the system, I want to extract plain text from uploaded files, so that content can be chunked and embedded.

**Product Rationale**

Text extraction is the bridge between raw files and the RAG pipeline.

**Functional Requirements**

- Markdown/TXT: read as UTF-8 text
- JSON: extract text fields or stringify structured content
- PDF: extract text per page with page numbers in metadata
- Extraction failures mark job `failed` with reason

**Acceptance Criteria**

- Given a valid PDF with 3 pages  
  When extraction runs  
  Then text is extracted with page metadata

- Given a corrupted PDF  
  When extraction runs  
  Then job status is `failed` with error reason stored

**Priority:** P0  
**Dependencies:** ING-001  
**Notes for Engineering:** Use `pypdf` or `pdfplumber`; handle empty extraction as failure.


---

[← Back to MVP Product Backlog](../MVP_PRODUCT_BACKLOG.md)
