"""
Interactive CLI reviewer for pending ApproveKit approval requests.

Run with::

    approvekit-review --db path/to/approvekit.db

or as a Python module::

    python -m approvekit.reviewer --db path/to/approvekit.db
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from typing import Optional

from approvekit.models import ApprovalRequest, ApprovalStatus
from approvekit.storage import Storage


def _format_request(req: ApprovalRequest) -> str:
    lines = [
        f"  ID         : {req.id}",
        f"  Tool       : {req.tool_name}",
        f"  Args       : {req.tool_args}",
        f"  Created At : {req.created_at.strftime('%Y-%m-%d %H:%M:%S UTC')}",
        f"  Status     : {req.status.value}",
    ]
    return "\n".join(lines)


def review_loop(storage: Storage) -> None:
    """Interactive terminal loop for reviewing pending requests."""
    print("\n=== ApproveKit Reviewer ===")
    print("Type 'help' for available commands.\n")

    while True:
        pending = storage.list_pending()
        if not pending:
            print("No pending approval requests. Press Enter to refresh or 'q' to quit.")
        else:
            print(f"\n--- {len(pending)} pending request(s) ---")
            for i, req in enumerate(pending, start=1):
                print(f"\n[{i}] {req.tool_name}")
                print(_format_request(req))

        try:
            raw = input("\napprovekit> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting reviewer.")
            break

        if not raw:
            continue

        parts = raw.split(None, 2)
        cmd = parts[0].lower()

        if cmd in ("q", "quit", "exit"):
            print("Goodbye.")
            break

        elif cmd == "help":
            _print_help()

        elif cmd == "list":
            _cmd_list(storage)

        elif cmd == "audit":
            _cmd_audit(storage)

        elif cmd == "approve":
            if len(parts) < 2:
                print("Usage: approve <request-id> [notes]")
                continue
            req_id = parts[1]
            notes: Optional[str] = parts[2] if len(parts) > 2 else None
            _cmd_decide(storage, req_id, approve=True, notes=notes)

        elif cmd == "reject":
            if len(parts) < 2:
                print("Usage: reject <request-id> [notes]")
                continue
            req_id = parts[1]
            notes = parts[2] if len(parts) > 2 else None
            _cmd_decide(storage, req_id, approve=False, notes=notes)

        else:
            print(f"Unknown command: {cmd!r}. Type 'help' for usage.")


def _print_help() -> None:
    print(
        "\nCommands:\n"
        "  list              – List all pending requests\n"
        "  approve <id> [notes] – Approve a request\n"
        "  reject  <id> [notes] – Reject a request\n"
        "  audit             – Show audit log\n"
        "  quit / q          – Exit the reviewer\n"
        "  help              – Show this message\n"
    )


def _cmd_list(storage: Storage) -> None:
    pending = storage.list_pending()
    if not pending:
        print("No pending requests.")
        return
    for req in pending:
        print(f"\n{_format_request(req)}")


def _cmd_audit(storage: Storage) -> None:
    entries = storage.list_audit()
    if not entries:
        print("Audit log is empty.")
        return
    print(f"\n{'─' * 60}")
    print(f"{'ID':<36}  {'Tool':<20}  {'Decision':<10}  {'Timestamp'}")
    print(f"{'─' * 60}")
    for e in entries:
        ts = e.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        print(f"{e.id:<36}  {e.tool_name:<20}  {e.decision.value:<10}  {ts}")
    print(f"{'─' * 60}")


def _cmd_decide(
    storage: Storage, req_id: str, approve: bool, notes: Optional[str]
) -> None:
    req = storage.get_request(req_id)
    if req is None:
        # Try prefix match.
        all_reqs = storage.list_requests()
        matches = [r for r in all_reqs if r.id.startswith(req_id)]
        if len(matches) == 1:
            req = matches[0]
        elif len(matches) > 1:
            print(f"Ambiguous prefix '{req_id}' matches {len(matches)} requests.")
            return
        else:
            print(f"Request '{req_id}' not found.")
            return

    if req.is_terminal():
        print(f"Request {req.id} is already in state '{req.status.value}'.")
        return

    if approve:
        req.approve(notes)
        verb = "Approved"
    else:
        req.reject(notes)
        verb = "Rejected"

    storage.save_request(req)
    print(f"✓ {verb} request {req.id} for tool '{req.tool_name}'.")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main(argv: Optional[list] = None) -> None:
    parser = argparse.ArgumentParser(
        description="Interactive reviewer for ApproveKit pending requests."
    )
    parser.add_argument(
        "--db",
        default=":memory:",
        help="Path to the ApproveKit SQLite database (default: :memory:).",
    )
    args = parser.parse_args(argv)

    with Storage(db_path=args.db) as storage:
        review_loop(storage)


if __name__ == "__main__":
    main()
