"""Document routes."""

from typing import Annotated

from uuid import UUID

from fastapi import APIRouter, File, Form, Query, UploadFile, status

from app.api.deps import (
    DocumentServiceDep,
    RequireDocumentMutateDep,
    RequireViewDocumentsDep,
)
from app.infrastructure.db.enums import DocumentStatus
from app.modules.documents.schemas import (
    DocumentDetailResponse,
    DocumentListResponse,
    DocumentUploadResponse,
)

router = APIRouter(prefix="/workspaces", tags=["documents"])


@router.get(
    "/{workspace_id}/documents",
    response_model=DocumentListResponse,
)
async def list_documents(
    workspace_context: RequireViewDocumentsDep,
    document_service: DocumentServiceDep,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    status: Annotated[DocumentStatus | None, Query()] = None,
) -> DocumentListResponse:
    """List documents in the workspace with optional status filter."""
    return document_service.list_documents(
        context=workspace_context,
        page=page,
        page_size=page_size,
        status=status,
    )


@router.get(
    "/{workspace_id}/documents/{document_id}",
    response_model=DocumentDetailResponse,
)
async def get_document(
    document_id: UUID,
    workspace_context: RequireViewDocumentsDep,
    document_service: DocumentServiceDep,
) -> DocumentDetailResponse:
    """Return document details including ingestion status and chunk count."""
    return document_service.get_document_detail(
        context=workspace_context,
        document_id=document_id,
    )


@router.post(
    "/{workspace_id}/documents",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def upload_document(
    workspace_context: RequireDocumentMutateDep,
    document_service: DocumentServiceDep,
    file: Annotated[UploadFile, File()],
    title: Annotated[str | None, Form()] = None,
    source_type: Annotated[str | None, Form()] = None,
) -> DocumentUploadResponse:
    """Upload a supported document to the workspace."""
    content = await file.read()
    return document_service.upload(
        context=workspace_context,
        file_content=content,
        filename=file.filename or "untitled",
        title=title,
        source_type=source_type,
    )
