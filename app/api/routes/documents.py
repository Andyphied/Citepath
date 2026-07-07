"""Document routes."""

from typing import Annotated

from fastapi import APIRouter, File, Form, UploadFile, status

from app.api.deps import DocumentServiceDep, RequireDocumentMutateDep
from app.modules.documents.schemas import DocumentResponse

router = APIRouter(prefix="/workspaces", tags=["documents"])


@router.post(
    "/{workspace_id}/documents",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_document(
    workspace_context: RequireDocumentMutateDep,
    document_service: DocumentServiceDep,
    file: Annotated[UploadFile, File()],
    title: Annotated[str | None, Form()] = None,
    source_type: Annotated[str | None, Form()] = None,
) -> DocumentResponse:
    """Upload a supported document to the workspace."""
    content = await file.read()
    return document_service.upload(
        context=workspace_context,
        file_content=content,
        filename=file.filename or "untitled",
        title=title,
        source_type=source_type,
    )
