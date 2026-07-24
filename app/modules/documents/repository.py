"""Document persistence with workspace scoping."""

from typing import Any
from uuid import UUID

from sqlalchemy import func, select
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

    def count_by_status_for_workspace(
        self,
        *,
        workspace_id: UUID,
    ) -> dict[DocumentStatus, int]:
        """Return document counts grouped by status for a workspace."""
        stmt = (
            select(Document.status, func.count())
            .where(Document.workspace_id == workspace_id)
            .group_by(Document.status)
        )
        rows = self._session.execute(stmt).all()
        counts: dict[DocumentStatus, int] = {status: 0 for status in DocumentStatus}
        for status, count in rows:
            resolved = (
                status if isinstance(status, DocumentStatus) else DocumentStatus(status)
            )
            counts[resolved] = int(count)
        return counts

    def list_for_workspace_paginated(
        self,
        *,
        workspace_id: UUID,
        page: int,
        page_size: int,
        status: DocumentStatus | None = None,
    ) -> tuple[list[Document], int]:
        """Return a paginated document list and total count for a workspace."""
        conditions = [Document.workspace_id == workspace_id]
        if status is not None:
            conditions.append(Document.status == status)

        total = self._session.scalar(
            select(func.count()).select_from(Document).where(*conditions)
        )
        total = int(total or 0)

        offset = (page - 1) * page_size
        stmt = (
            select(Document)
            .where(*conditions)
            .order_by(Document.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        items = list(self._session.scalars(stmt).all())
        return items, total

    def delete(self, *, document: Document) -> None:
        """Delete a document row and commit."""
        self._session.delete(document)
        self._session.commit()

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
