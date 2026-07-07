"""Unit tests for local filesystem storage adapter."""

from uuid import uuid4

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
    assert not (tmp_path / "etc").exists()
