"""
Shared test fixtures for ApproveKit test suite.
"""

import pytest

from approvekit import ApproveKit, Policy
from approvekit.storage import Storage


@pytest.fixture()
def storage():
    """In-memory SQLite storage; closed automatically after each test."""
    with Storage(db_path=":memory:") as s:
        yield s


@pytest.fixture()
def simple_policy():
    """Policy that requires approval for 'risky_tool' (2-second timeout)."""
    return Policy.from_dict(
        {
            "default_timeout": 2,
            "rules": [
                {"tool": "risky_tool", "require_approval": True, "timeout": 2},
                {"tool": "safe_tool", "require_approval": False, "auto_approve": True},
            ],
        }
    )


@pytest.fixture()
def kit(storage, simple_policy):
    """ApproveKit instance wired to in-memory storage and simple_policy."""
    return ApproveKit(policy=simple_policy, storage=storage, poll_interval=0.05)
