"""
Demo tools that illustrate how ApproveKit intercepts risky operations.

Each function simulates a real-world AI agent action:

* ``send_email``    – send an e-mail (high risk: external communication)
* ``delete_record`` – permanently delete a database row (high risk)
* ``prod_write``    – write to a production data store (high risk)
* ``pii_access``    – access personally identifiable information (medium risk)
* ``read_record``   – read a database row (low risk – auto-approved)
"""

from __future__ import annotations

from typing import Any, Dict

from approvekit import ApproveKit, Policy

# ---------------------------------------------------------------------------
# Policy – defines which tools require human approval
# ---------------------------------------------------------------------------

POLICY = Policy.from_dict(
    {
        "default_timeout": 300,
        "rules": [
            {
                "tool": "send_email",
                "require_approval": True,
                "timeout": 120,
                "risk_level": "high",
            },
            {
                "tool": "delete_record",
                "require_approval": True,
                "timeout": 60,
                "risk_level": "high",
            },
            {
                "tool": "prod_write",
                "require_approval": True,
                "timeout": 120,
                "risk_level": "high",
            },
            {
                "tool": "pii_access",
                "require_approval": True,
                "timeout": 120,
                "risk_level": "medium",
            },
            {
                "tool": "read_record",
                "require_approval": False,
                "auto_approve": True,
                "risk_level": "low",
            },
        ],
    }
)

# Shared kit instance (the demo agent imports this).
kit = ApproveKit(policy=POLICY)


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------


@kit.guard
def send_email(to: str, subject: str, body: str) -> Dict[str, Any]:
    """Simulate sending an e-mail."""
    print(f"[send_email] → to={to!r} subject={subject!r}")
    return {"status": "sent", "to": to, "subject": subject}


@kit.guard
def delete_record(table: str, record_id: int) -> Dict[str, Any]:
    """Simulate permanently deleting a database record."""
    print(f"[delete_record] → table={table!r} record_id={record_id}")
    return {"status": "deleted", "table": table, "record_id": record_id}


@kit.guard
def prod_write(key: str, value: Any) -> Dict[str, Any]:
    """Simulate writing a value to a production data store."""
    print(f"[prod_write] → key={key!r} value={value!r}")
    return {"status": "written", "key": key}


@kit.guard
def pii_access(user_id: int, fields: list) -> Dict[str, Any]:
    """Simulate accessing personally identifiable information."""
    print(f"[pii_access] → user_id={user_id} fields={fields}")
    return {
        "user_id": user_id,
        "data": {f: f"<redacted_{f}>" for f in fields},
    }


@kit.guard
def read_record(table: str, record_id: int) -> Dict[str, Any]:
    """Simulate reading a database record (low risk – auto-approved)."""
    print(f"[read_record] → table={table!r} record_id={record_id}")
    return {"table": table, "record_id": record_id, "data": {"name": "Alice"}}
