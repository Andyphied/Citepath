"""Auth domain exceptions."""


class DuplicateEmailError(Exception):
    """Raised when registering with an email that already exists."""


class InvalidCredentialsError(Exception):
    """Raised when login credentials do not match any user."""


class UnauthorizedError(Exception):
    """Raised when a protected route is called without credentials."""


class TokenExpiredError(Exception):
    """Raised when a JWT has expired."""


class TokenInvalidError(Exception):
    """Raised when a JWT is malformed or fails signature verification."""
