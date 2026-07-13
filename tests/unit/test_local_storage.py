"""Unit tests for local filesystem storage adapter."""

from uuid import uuid4

import pytest

from app.infrastructure.storage.local import LocalStorageBackend


def test_local_storage_save_writes_file(tmp_path) -> None:
    workspace_id = uuid4()
    document_id = uuid4()
    backend = LocalStorageBackend(str(tmp_path))

    storage_key = backend.save(
        workspace_id=workspace_id,
        document_id=document_id,
        filename="billing-api-runbook.md",
        content=b"# Runbook content",
    )

    expected_path = tmp_path / str(workspace_id) / str(document_id) / "billing-api-runbook.md"
    assert storage_key == f"{workspace_id}/{document_id}/billing-api-runbook.md"
    assert expected_path.read_bytes() == b"# Runbook content"


def test_local_storage_sanitizes_path_traversal_filename(tmp_path) -> None:
    workspace_id = uuid4()
    document_id = uuid4()
    backend = LocalStorageBackend(str(tmp_path))

    storage_key = backend.save(
        workspace_id=workspace_id,
        document_id=document_id,
        filename="../../etc/passwd",
        content=b"safe",
    )

    assert storage_key.endswith("/passwd")
    assert (tmp_path / storage_key).read_bytes() == b"safe"
    assert (tmp_path / "etc").exists() is False


def test_local_storage_get_reads_saved_file(tmp_path) -> None:
    workspace_id = uuid4()
    document_id = uuid4()
    backend = LocalStorageBackend(str(tmp_path))

    storage_key = backend.save(
        workspace_id=workspace_id,
        document_id=document_id,
        filename="notes.txt",
        content=b"stored bytes",
    )

    assert backend.get(storage_key) == b"stored bytes"


def test_local_storage_get_rejects_missing_key(tmp_path) -> None:
    backend = LocalStorageBackend(str(tmp_path))

    with pytest.raises(FileNotFoundError):
        backend.get("missing/key.txt")


def test_local_storage_get_rejects_path_traversal(tmp_path) -> None:
    backend = LocalStorageBackend(str(tmp_path))

    with pytest.raises(ValueError, match="Invalid storage key"):
        backend.get("../../etc/passwd")


def test_local_storage_get_rejects_embedded_parent_segments(tmp_path) -> None:
    workspace_a = uuid4()
    document_a = uuid4()
    workspace_b = uuid4()
    document_b = uuid4()
    backend = LocalStorageBackend(str(tmp_path))

    backend.save(
        workspace_id=workspace_b,
        document_id=document_b,
        filename="secret.txt",
        content=b"foreign",
    )
    traversal_key = f"{workspace_a}/{document_a}/../{workspace_b}/{document_b}/secret.txt"

    with pytest.raises(ValueError, match="Invalid storage key"):
        backend.get(traversal_key)
