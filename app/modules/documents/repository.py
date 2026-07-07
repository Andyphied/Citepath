"""Document persistence with workspace scoping."""

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.infrastructure.db.enums import DocumentStatus
from app.infrastructure.db.scoped_repository import WorkspaceScopedRepository
from app.modules.documents.models import Document


class DocumentRepository(WorkspaceScopedRepository[Document]):
    """Workspace-scoped document CRUD."""

    _model = Document

    def __init__(self, session: Session) -> None:
        super().__init__(session)

    def create(
        self,
        *,
        workspace_id: UUID,
        status: DocumentStatus,
        id: UUID | None = None,
        uploaded_by: UUID | None = None,
        title: str | None = None,
        source_type: str | None = None,
        file_type: str | None = None,
        storage_key: str | None = None,
        metadata_: dict[str, Any] | None = None,
    ) -> Document:
        """Persist a document in the given workspace."""
        document_kwargs: dict[str, Any] = {
            "workspace_id": workspace_id,
            "uploaded_by": uploaded_by,
            "title": title,
            "source_type": source_type,
            "file_type": file_type,
            "storage_key": storage_key,
            "status": status,
            "metadata_": metadata_,
        }
        if id is not None:
            document_kwargs["id"] = id
        document = Document(**document_kwargs)
        self._session.add(document)
        self._session.commit()
        self._session.refresh(document)
        return document

    def list_for_workspace(self, *, workspace_id: UUID) -> list[Document]:
        """Return all documents in a workspace."""
        stmt = select(Document).order_by(Document.created_at.desc())
        stmt = self._scoped_filter(stmt, workspace_id)
        return list(self._session.scalars(stmt).all())

    def update_status(
        self,
        *,
        document: Document,
        status: DocumentStatus,
    ) -> Document:
        """Update document status and commit."""
        document.status = status
        self._session.commit()
        self._session.refresh(document)
        return document
