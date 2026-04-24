"""
Guided ApproveKit demo agent.

Terminal 1:

    python3 demo/agent.py --db /tmp/approvekit_demo.db --reset

Terminal 2:

    approvekit-web --db /tmp/approvekit_demo.db --port 8765

The agent pauses at risky tool calls until the browser reviewer approves,
rejects, or leaves a request to time out.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Callable, Dict

# Allow running from project root without installing the package.
sys.path.insert(0, str(Path(__file__).parent.parent))

from approvekit import ApproveKit, Policy
from approvekit.exceptions import ApprovalRejectedError, ApprovalTimeoutError
from approvekit.storage import Storage


DEFAULT_DB_PATH = "/tmp/approvekit_demo.db"


def build_policy() -> Policy:
    return Policy.from_dict(
        {
            "default_timeout": 45,
            "rules": [
                {
                    "tool": "read_record",
                    "require_approval": False,
                    "auto_approve": True,
                    "risk_level": "low",
                },
                {
                    "tool": "send_email",
                    "require_approval": True,
                    "timeout": 45,
                    "risk_level": "high",
                    "redact_fields": ["body"],
                },
                {
                    "tool": "pii_access",
                    "require_approval": True,
                    "timeout": 45,
                    "risk_level": "medium",
                    "redact_fields": ["email", "ssn"],
                },
                {
                    "tool": "delete_record",
                    "require_approval": True,
                    "timeout": 30,
                    "risk_level": "high",
                },
                {
                    "tool": "prod_write",
                    "require_approval": True,
                    "timeout": 8,
                    "risk_level": "high",
                    "redact_fields": ["value"],
                },
                {
                    "tool": "*",
                    "require_approval": True,
                    "timeout": 30,
                    "risk_level": "medium",
                },
            ],
        }
    )


def build_tools(kit: ApproveKit) -> Dict[str, Callable[..., Dict[str, Any]]]:
    @kit.guard
    def read_record(table: str, record_id: int) -> Dict[str, Any]:
        print(f"  EXECUTED read_record table={table!r} record_id={record_id}")
        return {"table": table, "record_id": record_id, "data": {"name": "Alice"}}

    @kit.guard
    def send_email(to: str, subject: str, body: str) -> Dict[str, Any]:
        print(f"  EXECUTED send_email to={to!r} subject={subject!r}")
        return {"status": "sent", "to": to, "subject": subject}

    @kit.guard
    def pii_access(
        user_id: int,
        fields: list[str],
        profile: Dict[str, Any],
        justification: str,
    ) -> Dict[str, Any]:
        print(f"  EXECUTED pii_access user_id={user_id} fields={fields}")
        return {"user_id": user_id, "fields": fields, "profile_name": profile["name"]}

    @kit.guard
    def delete_record(table: str, record_id: int, reason: str) -> Dict[str, Any]:
        print(f"  EXECUTED delete_record table={table!r} record_id={record_id}")
        return {"status": "deleted", "table": table, "record_id": record_id}

    @kit.guard
    def prod_write(
        key: str,
        value: Dict[str, Any],
        environment: str,
        reason: str,
    ) -> Dict[str, Any]:
        print(f"  EXECUTED prod_write key={key!r} environment={environment!r}")
        return {"status": "written", "key": key, "environment": environment}

    return {
        "read_record": read_record,
        "send_email": send_email,
        "pii_access": pii_access,
        "delete_record": delete_record,
        "prod_write": prod_write,
    }


def run_agent(db_path: str, reset: bool, poll_interval: float) -> None:
    db_file = Path(db_path)
    if reset and db_file.exists():
        db_file.unlink()

    storage = Storage(db_path=db_path)
    kit = ApproveKit(policy=build_policy(), storage=storage, poll_interval=poll_interval)
    tools = build_tools(kit)

    try:
        _print_header(db_path)

        _run_step(
            "1. Low-risk read auto-approves",
            lambda: tools["read_record"](table="users", record_id=42),
        )
        _run_step(
            "2. High-risk email waits for approval",
            lambda: tools["send_email"](
                to="ceo@example.com",
                subject="Quarterly report",
                body="Revenue details and customer notes for Q2.",
            ),
        )
        _run_step(
            "3. PII access shows redacted payloads in the reviewer",
            lambda: tools["pii_access"](
                user_id=42,
                fields=["email", "ssn"],
                profile={
                    "name": "Alice Chen",
                    "email": "alice@example.com",
                    "ssn": "123-45-6789",
                },
                justification="Support case requires identity verification.",
            ),
        )
        _run_step(
            "4. Dangerous delete should be rejected in the reviewer",
            lambda: tools["delete_record"](
                table="payments",
                record_id=7001,
                reason="Agent thinks duplicate payment can be removed.",
            ),
        )
        _run_step(
            "5. Production write defaults to deny if no one reviews it",
            lambda: tools["prod_write"](
                key="billing.retry_limit",
                value={"from": 3, "to": 12, "customer_segment": "enterprise"},
                environment="production",
                reason="Agent wants to reduce failed renewal tickets.",
            ),
        )

        _print_audit(storage)
    finally:
        storage.close()


def _run_step(title: str, call: Callable[[], Dict[str, Any]]) -> None:
    print()
    print(title)
    print("-" * len(title))
    try:
        result = call()
        print(f"  Result: {result}")
    except ApprovalRejectedError as exc:
        print(f"  Blocked by rejection: {exc}")
    except ApprovalTimeoutError as exc:
        print(f"  Blocked by timeout: {exc}")


def _print_header(db_path: str) -> None:
    print("=" * 68)
    print("ApproveKit Demo Agent")
    print("=" * 68)
    print(f"Database: {db_path}")
    print()
    print("Open a second terminal and run:")
    print(f"  approvekit-web --db {db_path} --port 8765")
    print()
    print("Suggested reviewer actions:")
    print("  Step 2: approve")
    print("  Step 3: approve and inspect redaction")
    print("  Step 4: reject")
    print("  Step 5: leave alone for timeout, or approve to see execution")


def _print_audit(storage: Storage) -> None:
    entries = storage.list_audit()
    print()
    print(f"Audit log ({len(entries)} entries)")
    print("-" * 68)
    for entry in entries:
        risk = entry.metadata.get("risk_level", "low")
        print(
            f"  {entry.timestamp.strftime('%H:%M:%S')} "
            f"{entry.tool_name:<14} {entry.decision.value:<9} risk={risk}"
        )


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Run the guided ApproveKit demo agent.")
    parser.add_argument("--db", default=DEFAULT_DB_PATH, help="SQLite database path.")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Delete the demo database before starting.",
    )
    parser.add_argument(
        "--poll-interval",
        type=float,
        default=0.25,
        help="Seconds between approval checks.",
    )
    args = parser.parse_args(argv)
    run_agent(db_path=args.db, reset=args.reset, poll_interval=args.poll_interval)


if __name__ == "__main__":
    main()
