"""Custom exceptions raised by ApproveKit middleware."""


class ApproveKitError(Exception):
    """Base class for all ApproveKit errors."""


class ApprovalRejectedError(ApproveKitError):
    """Raised when a reviewer explicitly rejects a tool call."""


class ApprovalTimeoutError(ApproveKitError):
    """Raised when no reviewer decision arrives within the configured timeout."""
