"""Document-related HTTP exception handlers."""

from fastapi import Request, status

from app.modules.documents.exceptions import (
    DocumentNotFoundError,
    DocumentReindexInProgressError,
    FileTooLargeError,
    UnsupportedFileTypeError,
)
from app.modules.observability.errors import error_response


async def unsupported_file_type_handler(
    request: Request,
    exc: UnsupportedFileTypeError,
):
    """Return 422 when the uploaded file type is not supported."""
    details = {}
    if exc.extension is not None:
        details["extension"] = exc.extension
    return error_response(
        request=request,
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        code="unsupported_file_type",
        message="Unsupported file type",
        details=details,
    )


async def file_too_large_handler(
    request: Request,
    exc: FileTooLargeError,
):
    """Return 422 when the uploaded file exceeds the size limit."""
    return error_response(
        request=request,
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        code="file_too_large",
        message="Uploaded file exceeds the maximum allowed size",
        details={
            "max_bytes": exc.max_bytes,
            "actual_bytes": exc.actual_bytes,
        },
    )


async def document_not_found_handler(
    request: Request,
    _exc: DocumentNotFoundError,
):
    """Return 404 when a document is missing or not in the workspace."""
    return error_response(
        request=request,
        status_code=status.HTTP_404_NOT_FOUND,
        code="not_found",
        message="Document not found",
    )


async def document_reindex_in_progress_handler(
    request: Request,
    _exc: DocumentReindexInProgressError,
):
    """Return 409 when a document re-index is already in progress."""
    return error_response(
        request=request,
        status_code=status.HTTP_409_CONFLICT,
        code="reindex_in_progress",
        message="Document re-index is already in progress",
    )
