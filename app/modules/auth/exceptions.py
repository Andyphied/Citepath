"""Auth domain exceptions."""


class DuplicateEmailError(Exception):
    """Raised when registering with an email that already exists."""


class InvalidCredentialsError(Exception):
    """Raised when login credentials do not match any user."""
