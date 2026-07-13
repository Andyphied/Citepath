"""Document domain exceptions."""


class UnsupportedFileTypeError(Exception):
    """Raised when an uploaded file extension is not allowed."""

    def __init__(self, *, extension: str | None = None) -> None:
        self.extension = extension
        super().__init__()


class FileTooLargeError(Exception):
    """Raised when an uploaded file exceeds the configured size limit."""

    def __init__(self, *, max_bytes: int, actual_bytes: int) -> None:
        self.max_bytes = max_bytes
        self.actual_bytes = actual_bytes
        super().__init__()


class DocumentNotFoundError(Exception):
    """Raised when a document is missing or not in the requested workspace."""
