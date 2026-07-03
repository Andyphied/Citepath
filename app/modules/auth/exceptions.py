"""Auth domain exceptions."""


class DuplicateEmailError(Exception):
    """Raised when registering with an email that already exists."""
