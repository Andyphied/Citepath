"""Storage key validation helpers."""


def reject_unsafe_storage_key(storage_key: str) -> None:
    """Reject storage keys that could escape the storage root or bypass prefix checks."""
    if not storage_key or "\x00" in storage_key:
        raise ValueError(f"Invalid storage key: {storage_key!r}")

    if storage_key.startswith(("/", "\\")):
        raise ValueError(f"Invalid storage key: {storage_key!r}")

    for part in storage_key.split("/"):
        if part in ("", ".", ".."):
            raise ValueError(f"Invalid storage key: {storage_key!r}")
