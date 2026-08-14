# ADR-002: Vector Store Choice

## Status

Accepted

## Context

Citepath must store document chunk embeddings and perform similarity search scoped by workspace. MVP backlog assumption A3 specifies PostgreSQL + pgvector. The corpus size for portfolio demo (Northstar Cloud) is small (tens of documents, thousands of chunks).

## Decision

Use **PostgreSQL 16 with pgvector extension** as the sole vector store. Store embeddings in `document_chunks.embedding` (`vector(1536)`) and query with cosine distance (`<=>`) filtered by `workspace_id`.

Create an **HNSW index** on `embedding` for approximate nearest neighbor search at demo scale.

## Consequences

**Positive:**
- One database for relational + vector data — no sync lag between chunks and metadata
- ACID transactions: delete document and chunks atomically on re-index
- Workspace filter in same SQL query as vector search — strong isolation story
- Lower operational cost and Terraform surface vs dedicated vector DB
- Demonstrates pragmatic backend judgment for MVP scope

**Negative:**
- pgvector performance degrades at very large scale (millions of vectors per table)
- No built-in hybrid BM25 + vector in MVP (would require PostgreSQL full-text add-on or external search)
- Index rebuild required if embedding dimension changes

## Alternatives Considered

| Alternative | Why not selected |
|-------------|------------------|
| **Pinecone** | Additional service, cost, and tenancy model complexity; overkill for demo corpus |
| **Qdrant** | Extra infrastructure; dual-store consistency between Postgres metadata and Qdrant vectors |
| **Weaviate** | Heavier ops footprint; learning curve not justified for MVP |
| **Elasticsearch/OpenSearch hybrid** | Powerful hybrid search but significant ops burden; MVP assumes A11 top-k vector only |

## Implementation Notes

- Enable extension in first migration: `CREATE EXTENSION vector;`
- Every similarity query: `WHERE workspace_id = $1` before `ORDER BY embedding <=> $2`
- Default embedding: `text-embedding-3-small` (1536 dimensions)
- Index: `CREATE INDEX ON document_chunks USING hnsw (embedding vector_cosine_ops);`
- **Migration trigger (post-MVP):** Consider dedicated vector DB when any of:
  - \> 500K chunks per deployment
  - p95 retrieval latency \> 200ms under load
  - Need hybrid search / advanced reranking at scale
- Design `RetrievalService` interface so vector backend could swap later without changing RAG/agent modules
