"""Audit module domain exceptions."""


class InvalidAuditRangeError(Exception):
    """Raised when an audit log date range is empty or inverted."""
