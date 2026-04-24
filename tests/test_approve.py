"""Tests for the happy-path approval flow."""

from __future__ import annotations

import threading
import time

import pytest

from approvekit import ApproveKit, Policy
from approvekit.models import ApprovalStatus


def test_safe_tool_runs_without_approval(kit, storage):
    """A tool with require_approval=False should execute immediately."""
    results = []

    @kit.guard
    def safe_tool(x: int) -> int:
        results.append(x)
        return x * 2

    value = safe_tool(x=7)

    assert value == 14
    assert results == [7]

    # An audit entry must have been written.
    entries = storage.list_audit()
    assert len(entries) == 1
    assert entries[0].decision == ApprovalStatus.APPROVED
    assert entries[0].tool_name == "safe_tool"


def test_approval_allows_execution(kit, storage):
    """A guarded tool should execute after a reviewer approves it."""
    executed = []

    @kit.guard
    def risky_tool(action: str) -> str:
        executed.append(action)
        return f"done:{action}"

    def _approve_after_delay():
        time.sleep(0.15)
        pending = storage.list_pending()
        assert len(pending) == 1
        kit.approve(pending[0].id, notes="Looks good")

    t = threading.Thread(target=_approve_after_delay, daemon=True)
    t.start()

    result = risky_tool(action="deploy")

    t.join(timeout=2)

    assert result == "done:deploy"
    assert executed == ["deploy"]

    # Audit log should record the approval.
    entries = storage.list_audit()
    assert len(entries) == 1
    entry = entries[0]
    assert entry.decision == ApprovalStatus.APPROVED
    assert entry.tool_name == "risky_tool"
    assert entry.reviewer_notes == "Looks good"


def test_approve_stores_reviewed_at(kit, storage):
    """reviewed_at should be set when a request is approved."""

    @kit.guard
    def risky_tool() -> str:
        return "ok"

    def _approve():
        time.sleep(0.1)
        pending = storage.list_pending()
        kit.approve(pending[0].id)

    t = threading.Thread(target=_approve, daemon=True)
    t.start()
    risky_tool()
    t.join(timeout=2)

    reqs = storage.list_requests(status=ApprovalStatus.APPROVED)
    assert len(reqs) == 1
    assert reqs[0].reviewed_at is not None


def test_args_captured_in_audit(kit, storage):
    """Tool arguments should appear in both the request and audit entry."""

    @kit.guard
    def risky_tool(a: int, b: str = "default") -> None:
        pass

    def _approve():
        time.sleep(0.1)
        pending = storage.list_pending()
        kit.approve(pending[0].id)

    t = threading.Thread(target=_approve, daemon=True)
    t.start()
    risky_tool(1, b="hello")
    t.join(timeout=2)

    entries = storage.list_audit()
    assert entries[0].tool_args == {"a": 1, "b": "hello"}


def test_redacted_fields_are_stored_but_original_args_execute(storage):
    """Sensitive fields should be masked in storage without changing execution."""
    policy = Policy.from_dict(
        {
            "default_timeout": 2,
            "rules": [
                {
                    "tool": "send_email",
                    "require_approval": True,
                    "timeout": 2,
                    "risk_level": "high",
                    "redact_fields": ["body", "ssn"],
                },
            ],
        }
    )
    kit = ApproveKit(policy=policy, storage=storage, poll_interval=0.05)
    executed = []

    @kit.guard
    def send_email(to: str, body: str, profile: dict) -> str:
        executed.append({"to": to, "body": body, "profile": profile})
        return body

    def _approve():
        time.sleep(0.1)
        pending = storage.list_pending()
        assert len(pending) == 1
        assert pending[0].tool_args == {
            "to": "ceo@example.com",
            "body": "[REDACTED]",
            "profile": {"name": "Alice", "ssn": "[REDACTED]"},
        }
        assert pending[0].metadata["risk_level"] == "high"
        assert pending[0].metadata["timeout"] == 2
        assert pending[0].metadata["redact_fields"] == ["body", "ssn"]
        kit.approve(pending[0].id, notes="safe after review")

    t = threading.Thread(target=_approve, daemon=True)
    t.start()

    result = send_email(
        to="ceo@example.com",
        body="confidential report",
        profile={"name": "Alice", "ssn": "123-45-6789"},
    )

    t.join(timeout=2)

    assert result == "confidential report"
    assert executed == [
        {
            "to": "ceo@example.com",
            "body": "confidential report",
            "profile": {"name": "Alice", "ssn": "123-45-6789"},
        }
    ]

    entries = storage.list_audit()
    assert entries[0].tool_args["body"] == "[REDACTED]"
    assert entries[0].tool_args["profile"]["ssn"] == "[REDACTED]"
    assert entries[0].metadata["risk_level"] == "high"
