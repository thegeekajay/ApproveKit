"""
Sample agent that uses ApproveKit-guarded tools.

Run interactively::

    python demo/agent.py

The agent attempts several tool calls.  High-risk calls pause and wait for
reviewer approval.  While the agent waits you can open a second terminal and
run::

    approvekit-review --db /tmp/approvekit_demo.db

to approve or reject the pending requests.
"""

from __future__ import annotations

import sys
import time
import threading
from pathlib import Path

# Allow running from project root without installing the package.
sys.path.insert(0, str(Path(__file__).parent.parent))

from approvekit import ApproveKit, Policy
from approvekit.storage import Storage
from approvekit.exceptions import ApprovalRejectedError, ApprovalTimeoutError

# ---------------------------------------------------------------------------
# Setup – use a persistent DB so the reviewer CLI can connect to it.
# ---------------------------------------------------------------------------

DB_PATH = "/tmp/approvekit_demo.db"

storage = Storage(db_path=DB_PATH)

policy = Policy.from_dict(
    {
        "default_timeout": 60,
        "rules": [
            {"tool": "send_email", "require_approval": True, "timeout": 60, "risk_level": "high"},
            {"tool": "delete_record", "require_approval": True, "timeout": 30, "risk_level": "high"},
            {"tool": "prod_write", "require_approval": True, "timeout": 60, "risk_level": "high"},
            {"tool": "pii_access", "require_approval": True, "timeout": 60, "risk_level": "medium"},
            {"tool": "read_record", "require_approval": False, "auto_approve": True},
        ],
    }
)

kit = ApproveKit(policy=policy, storage=storage)


# ---------------------------------------------------------------------------
# Agent tools
# ---------------------------------------------------------------------------


@kit.guard
def send_email(to: str, subject: str, body: str) -> dict:
    print(f"  ✉  Email sent to {to}: {subject!r}")
    return {"status": "sent"}


@kit.guard
def delete_record(table: str, record_id: int) -> dict:
    print(f"  🗑  Deleted {table}[{record_id}]")
    return {"status": "deleted"}


@kit.guard
def read_record(table: str, record_id: int) -> dict:
    print(f"  📖 Read {table}[{record_id}]")
    return {"data": {"id": record_id, "name": "Alice"}}


# ---------------------------------------------------------------------------
# Agent logic
# ---------------------------------------------------------------------------


def run_agent() -> None:
    print("=" * 60)
    print("ApproveKit Demo Agent")
    print(f"Database: {DB_PATH}")
    print("=" * 60)
    print()
    print("Open a second terminal and run:")
    print(f"  approvekit-review --db {DB_PATH}")
    print("to review pending approvals.\n")

    # Step 1 – low-risk read (auto-approved, no human needed).
    print("Step 1: Reading a record (low-risk, auto-approved)…")
    result = read_record(table="users", record_id=42)
    print(f"  Result: {result}\n")

    # Step 2 – high-risk send_email (needs approval).
    print("Step 2: Sending an email (high-risk – waiting for approval)…")
    try:
        result = send_email(
            to="ceo@example.com",
            subject="Quarterly Report",
            body="Please find the report attached.",
        )
        print(f"  Result: {result}\n")
    except ApprovalRejectedError as exc:
        print(f"  ✗ Rejected: {exc}\n")
    except ApprovalTimeoutError as exc:
        print(f"  ⏱ Timed out: {exc}\n")

    # Step 3 – high-risk delete (needs approval).
    print("Step 3: Deleting a record (high-risk – waiting for approval)…")
    try:
        result = delete_record(table="orders", record_id=7)
        print(f"  Result: {result}\n")
    except ApprovalRejectedError as exc:
        print(f"  ✗ Rejected: {exc}\n")
    except ApprovalTimeoutError as exc:
        print(f"  ⏱ Timed out: {exc}\n")

    print("Agent finished.")
    print(f"\nAudit log ({len(storage.list_audit())} entries):")
    for entry in storage.list_audit():
        print(
            f"  [{entry.timestamp.strftime('%H:%M:%S')}] "
            f"{entry.tool_name:20s} → {entry.decision.value}"
        )


if __name__ == "__main__":
    run_agent()
