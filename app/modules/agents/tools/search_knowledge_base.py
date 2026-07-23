"""search_knowledge_base agent tool."""

from __future__ import annotations

from app.modules.agents.schemas import SearchKnowledgeBaseArgs
from app.modules.retrieval.schemas import RetrievalFilters
from app.modules.retrieval.service import RetrievalService
from app.modules.workspaces.context import WorkspaceContext


def execute_search_knowledge_base(
    *,
    args: SearchKnowledgeBaseArgs,
    context: WorkspaceContext,
    retrieval_service: RetrievalService,
) -> dict:
    """Search workspace knowledge base and return grounded citations."""
    filters = None
    if args.file_type or args.source_type or args.document_id:
        filters = RetrievalFilters(
            file_type=args.file_type,
            source_type=args.source_type,
            document_id=args.document_id,
        )

    result = retrieval_service.search(
        query=args.query,
        workspace_id=context.workspace_id,
        user_id=context.user_id,
        top_k=args.top_k,
        metadata={"agent_tool": "search_knowledge_base"},
        filters=filters,
    )

    citations = []
    content_lines: list[str] = []
    related_documents: list[str] = []

    for chunk in result.chunks:
        doc_id = str(chunk.document_metadata.document_id)
        if doc_id not in related_documents:
            related_documents.append(doc_id)
        citations.append(
            {
                "chunk_id": str(chunk.chunk_id),
                "document_id": doc_id,
                "document_title": chunk.document_metadata.title,
                "chunk_preview": chunk.content_preview,
                "score": chunk.score,
                "metadata": chunk.document_metadata.chunk_metadata,
            }
        )
        title = chunk.document_metadata.title or "untitled"
        content_lines.append(
            f"[{title}] (score={chunk.score:.2f}): {chunk.content_preview}"
        )

    return {
        "content": "\n".join(content_lines) if content_lines else "No matching chunks found.",
        "citations": citations,
        "related_documents": related_documents,
        "insufficient_context": result.insufficient_context,
        "query": result.query,
    }
