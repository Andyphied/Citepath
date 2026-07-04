"""Workspace domain exceptions."""


class DuplicateSlugError(Exception):
    """Raised when creating a workspace with a slug that already exists."""


class InvalidSlugError(Exception):
    """Raised when a workspace slug fails format validation."""


class WorkspaceForbiddenError(Exception):
    """Raised when a user lacks membership for a workspace."""
