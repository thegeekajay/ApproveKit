"""Tests for the rejection flow."""

from __future__ import annotations

import threading
import time

import pytest

from approvekit.exceptions import ApprovalRejectedError
from approvekit.models import ApprovalStatus


def test_rejection_raises_error(kit, storage):
    """When a reviewer rejects a request, ApprovalRejectedError is raised."""
    executed = []

    @kit.guard
    def risky_tool(action: str) -> str:
        executed.append(action)
        return f"done:{action}"

    def _reject_after_delay():
        time.sleep(0.15)
        pending = storage.list_pending()
        assert len(pending) == 1
        kit.reject(pending[0].id, notes="Too risky")

    t = threading.Thread(target=_reject_after_delay, daemon=True)
    t.start()

    with pytest.raises(ApprovalRejectedError) as exc_info:
        risky_tool(action="nuke")

    t.join(timeout=2)

    # Tool body must NOT have run.
    assert executed == []
    # Error message should include notes.
    assert "Too risky" in str(exc_info.value)


def test_rejected_request_persisted(kit, storage):
    """The database must record a rejected request."""

    @kit.guard
    def risky_tool() -> None:
        pass

    def _reject():
        time.sleep(0.1)
        pending = storage.list_pending()
        kit.reject(pending[0].id, notes="nope")

    t = threading.Thread(target=_reject, daemon=True)
    t.start()

    with pytest.raises(ApprovalRejectedError):
        risky_tool()

    t.join(timeout=2)

    reqs = storage.list_requests(status=ApprovalStatus.REJECTED)
    assert len(reqs) == 1
    assert reqs[0].reviewer_notes == "nope"


def test_rejected_audit_entry(kit, storage):
    """An audit entry with decision=REJECTED must be written on rejection."""

    @kit.guard
    def risky_tool() -> None:
        pass

    def _reject():
        time.sleep(0.1)
        pending = storage.list_pending()
        kit.reject(pending[0].id)

    t = threading.Thread(target=_reject, daemon=True)
    t.start()

    with pytest.raises(ApprovalRejectedError):
        risky_tool()

    t.join(timeout=2)

    entries = storage.list_audit()
    assert len(entries) == 1
    assert entries[0].decision == ApprovalStatus.REJECTED
    assert entries[0].tool_name == "risky_tool"


def test_double_reject_raises_value_error(kit, storage):
    """Attempting to reject an already-terminal request should fail cleanly."""

    @kit.guard
    def risky_tool() -> None:
        pass

    def _reject():
        time.sleep(0.1)
        pending = storage.list_pending()
        kit.reject(pending[0].id)

    t = threading.Thread(target=_reject, daemon=True)
    t.start()

    with pytest.raises(ApprovalRejectedError):
        risky_tool()

    t.join(timeout=2)

    reqs = storage.list_requests(status=ApprovalStatus.REJECTED)
    assert reqs

    with pytest.raises(ValueError, match="terminal state"):
        kit.reject(reqs[0].id)
