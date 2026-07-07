"""Local filesystem storage adapter."""

from pathlib import Path
from uuid import UUID

from app.infrastructure.storage.interface import StorageBackend
from app.infrastructure.storage.validation import reject_unsafe_storage_key


class LocalStorageBackend:
    """Store document files on the local filesystem."""

    def __init__(self, base_path: str) -> None:
        self._base_path = Path(base_path)

    def save(
        self,
        *,
        workspace_id: UUID,
        document_id: UUID,
        filename: str,
        content: bytes,
    ) -> str:
        """Write content under workspace/document hierarchy."""
        safe_filename = Path(filename).name.replace("\x00", "")
        if not safe_filename:
            safe_filename = "upload"

        relative_key = f"{workspace_id}/{document_id}/{safe_filename}"
        full_path = self._base_path / relative_key
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_bytes(content)
        return relative_key

    def get(self, storage_key: str) -> bytes:
        """Read content from a previously saved storage key."""
        reject_unsafe_storage_key(storage_key)
        full_path = (self._base_path / storage_key).resolve()
        base_path = self._base_path.resolve()
        if not full_path.is_relative_to(base_path):
            raise ValueError(f"Invalid storage key: {storage_key}")
        if not full_path.is_file():
            raise FileNotFoundError(f"Storage object not found: {storage_key}")
        return full_path.read_bytes()
