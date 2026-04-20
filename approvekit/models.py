"""Data models for ApproveKit."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ApprovalStatus(str, Enum):
    """Lifecycle states of an approval request."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    TIMEOUT = "timeout"


@dataclass
class ApprovalRequest:
    """Represents a single approval request for a tool call."""

    tool_name: str
    tool_args: Dict[str, Any]
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    status: ApprovalStatus = ApprovalStatus.PENDING
    created_at: datetime = field(default_factory=_utcnow)
    reviewed_at: Optional[datetime] = None
    reviewer_notes: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_terminal(self) -> bool:
        """Return True when the request has reached a final state."""
        return self.status != ApprovalStatus.PENDING

    def approve(self, notes: Optional[str] = None) -> None:
        self.status = ApprovalStatus.APPROVED
        self.reviewed_at = _utcnow()
        self.reviewer_notes = notes

    def reject(self, notes: Optional[str] = None) -> None:
        self.status = ApprovalStatus.REJECTED
        self.reviewed_at = _utcnow()
        self.reviewer_notes = notes

    def mark_timeout(self) -> None:
        self.status = ApprovalStatus.TIMEOUT
        self.reviewed_at = _utcnow()


@dataclass
class AuditEntry:
    """Immutable record written after every approval decision."""

    request_id: str
    tool_name: str
    tool_args: Dict[str, Any]
    decision: ApprovalStatus
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=_utcnow)
    reviewer_notes: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
