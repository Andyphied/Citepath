"""Document storage adapters."""

from app.infrastructure.config import Settings, StorageBackend as StorageBackendKind
from app.infrastructure.storage.interface import StorageBackend
from app.infrastructure.storage.local import LocalStorageBackend


def create_storage_backend(settings: Settings) -> StorageBackend:
    """Return the configured storage backend implementation."""
    if settings.STORAGE_BACKEND == StorageBackendKind.LOCAL:
        return LocalStorageBackend(settings.STORAGE_PATH)

    raise NotImplementedError(
        f"Storage backend {settings.STORAGE_BACKEND.value!r} is not implemented"
    )
