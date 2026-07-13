"""Ingestion domain exceptions."""


class IngestionJobNotFoundError(Exception):
    """Raised when an ingestion job is missing or not in the requested workspace."""
