"""Unit tests for storage key validation."""

import pytest

from app.infrastructure.storage.validation import reject_unsafe_storage_key


@pytest.mark.parametrize(
    "storage_key",
    [
        "",
        "../../etc/passwd",
        "ws/doc/../../other/doc/file.txt",
        "/absolute/key.txt",
        "ws//doc/file.txt",
        "ws/./doc/file.txt",
    ],
)
def test_reject_unsafe_storage_key_rejects_invalid_keys(storage_key: str) -> None:
    with pytest.raises(ValueError, match="Invalid storage key"):
        reject_unsafe_storage_key(storage_key)


def test_reject_unsafe_storage_key_allows_canonical_key() -> None:
    reject_unsafe_storage_key("workspace-id/document-id/sample.txt")
