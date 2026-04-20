"""Tests for the timeout flow."""

from __future__ import annotations

import pytest

from approvekit.exceptions import ApprovalTimeoutError
from approvekit.models import ApprovalStatus
from approvekit import ApproveKit, Policy
from approvekit.storage import Storage


@pytest.fixture()
def fast_timeout_kit():
    """Kit configured with a 1-second timeout for risky_tool."""
    policy = Policy.from_dict(
        {
            "default_timeout": 1,
            "rules": [
                {"tool": "risky_tool", "require_approval": True, "timeout": 1},
            ],
        }
    )
    storage = Storage(db_path=":memory:")
    kit = ApproveKit(policy=policy, storage=storage, poll_interval=0.05)
    yield kit, storage
    storage.close()


def test_timeout_raises_error(fast_timeout_kit):
    """When no reviewer acts within the timeout, ApprovalTimeoutError is raised."""
    kit, storage = fast_timeout_kit
    executed = []

    @kit.guard
    def risky_tool() -> None:
        executed.append(True)

    with pytest.raises(ApprovalTimeoutError) as exc_info:
        risky_tool()

    assert executed == [], "Tool body must not execute on timeout"
    assert "risky_tool" in str(exc_info.value)


def test_timeout_persisted_as_timeout_status(fast_timeout_kit):
    """The request should end up in TIMEOUT state in the database."""
    kit, storage = fast_timeout_kit

    @kit.guard
    def risky_tool() -> None:
        pass

    with pytest.raises(ApprovalTimeoutError):
        risky_tool()

    reqs = storage.list_requests()
    assert len(reqs) == 1
    assert reqs[0].status == ApprovalStatus.TIMEOUT


def test_timeout_audit_entry(fast_timeout_kit):
    """An audit entry with decision=TIMEOUT must be written."""
    kit, storage = fast_timeout_kit

    @kit.guard
    def risky_tool() -> None:
        pass

    with pytest.raises(ApprovalTimeoutError):
        risky_tool()

    entries = storage.list_audit()
    assert len(entries) == 1
    assert entries[0].decision == ApprovalStatus.TIMEOUT


def test_no_pending_after_timeout(fast_timeout_kit):
    """After a timeout, there should be no remaining pending requests."""
    kit, storage = fast_timeout_kit

    @kit.guard
    def risky_tool() -> None:
        pass

    with pytest.raises(ApprovalTimeoutError):
        risky_tool()

    assert storage.list_pending() == []
