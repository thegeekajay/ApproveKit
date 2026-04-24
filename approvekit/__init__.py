"""
ApproveKit – Human-in-the-loop approval middleware for AI agent tool calls.

Quick start::

    from approvekit import ApproveKit, Policy

    policy = Policy.from_dict({
        "rules": [
            {"tool": "send_email", "require_approval": True},
            {"tool": "delete_record", "require_approval": True, "timeout": 60},
        ]
    })
    kit = ApproveKit(policy=policy)

    @kit.guard
    def send_email(to, subject, body):
        ...  # real implementation
"""

from approvekit.core import ApproveKit
from approvekit.models import ApprovalRequest, ApprovalStatus, AuditEntry
from approvekit.policy import Policy, PolicyRule
from approvekit.storage import Storage

__version__ = "0.1.2"
__all__ = [
    "ApproveKit",
    "ApprovalRequest",
    "ApprovalStatus",
    "AuditEntry",
    "Policy",
    "PolicyRule",
    "Storage",
    "__version__",
]
