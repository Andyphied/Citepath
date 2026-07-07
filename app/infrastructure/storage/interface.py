"""Storage backend protocol for document files."""

from typing import Protocol
from uuid import UUID


class StorageBackend(Protocol):
    """Persist and address uploaded document bytes."""

    def save(
        self,
        *,
        workspace_id: UUID,
        document_id: UUID,
        filename: str,
        content: bytes,
    ) -> str:
        """Write content and return the storage key for the document."""
        ...

    def get(self, storage_key: str) -> bytes:
        """Read stored content by storage key."""
        ...
