"""Extraction errors for the ingestion pipeline."""


class ExtractionError(Exception):
    """Raised when text cannot be extracted from a document."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message
