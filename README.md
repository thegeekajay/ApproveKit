# ApproveKit

**ApproveKit** is a lightweight, framework-agnostic Python middleware for human-in-the-loop (HITL) approval of risky AI agent actions.

It intercepts tool calls such as `send_email`, `delete_record`, `prod_write`, and `pii_access`, evaluates them against simple policy rules, pauses execution when approval is required, and logs every decision in a persistent audit trail.

---

## Features

- 🛡 **Decorator-based middleware** – wrap any callable with `@kit.guard`
- 📋 **Simple policy config** – dict, JSON, or YAML; supports per-tool rules, timeouts, and auto-approve
- 💾 **SQLite-backed persistence** – approval requests and full audit history
- 🔄 **Blocking approval flow** – agent pauses until a reviewer acts or the timeout expires
- 🖥 **CLI reviewer interface** – approve or reject pending requests from the terminal
- 🧪 **Tested flows** – approve, reject, and timeout covered by the test suite

---

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│                        AI Agent                          │
│  result = send_email(to=..., subject=..., body=...)      │
└────────────────────────┬─────────────────────────────────┘
                         │  @kit.guard wraps the function
                         ▼
┌──────────────────────────────────────────────────────────┐
│                    ApproveKit Middleware                  │
│  1. Capture tool name + args                             │
│  2. Evaluate policy  ──► auto-approve? → call fn()       │
│  3. Require approval? → save ApprovalRequest to SQLite   │
│  4. Poll DB every 0.5 s ◄── Reviewer CLI writes decision │
│  5. APPROVED → call fn()  |  REJECTED → raise error      │
│                              TIMEOUT  → raise error      │
└────────────────────────┬─────────────────────────────────┘
                         │  AuditEntry written on every exit
                         ▼
              ┌──────────────────────┐
              │   SQLite Database    │
              │  approval_requests   │
              │  audit_log           │
              └──────────────────────┘
```

### Key modules

| Module | Responsibility |
|---|---|
| `approvekit/core.py` | `ApproveKit` class, `guard` decorator, polling loop |
| `approvekit/policy.py` | `Policy` / `PolicyRule` – rule evaluation |
| `approvekit/storage.py` | Thread-safe SQLite persistence |
| `approvekit/models.py` | `ApprovalRequest`, `AuditEntry`, `ApprovalStatus` |
| `approvekit/reviewer.py` | Interactive CLI for reviewing pending requests |
| `approvekit/exceptions.py` | `ApprovalRejectedError`, `ApprovalTimeoutError` |
| `demo/` | Sample tools and agent |

---

## Setup

**Requirements:** Python 3.9+

```bash
# Clone and install (editable, with dev dependencies)
git clone https://github.com/thegeekajay/ApproveKit.git
cd ApproveKit
pip install -e ".[dev]"
```

---

## Quick Start

### 1. Define a policy

```python
from approvekit import ApproveKit, Policy

policy = Policy.from_dict({
    "default_timeout": 300,          # seconds
    "rules": [
        {"tool": "send_email",    "require_approval": True,  "risk_level": "high"},
        {"tool": "delete_record", "require_approval": True,  "timeout": 60},
        {"tool": "read_record",   "require_approval": False, "auto_approve": True},
    ]
})
```

You can also load policy from a file:

```python
policy = Policy.from_yaml("policy.yaml")
policy = Policy.from_json("policy.json")
```

### 2. Create a kit and guard your tools

```python
from approvekit.storage import Storage

storage = Storage(db_path="/tmp/approvekit.db")   # persistent
kit = ApproveKit(policy=policy, storage=storage)

@kit.guard
def send_email(to: str, subject: str, body: str) -> dict:
    # real implementation here
    ...

@kit.guard
def delete_record(table: str, record_id: int) -> dict:
    ...
```

### 3. Call tools from your agent

```python
from approvekit.exceptions import ApprovalRejectedError, ApprovalTimeoutError

try:
    send_email(to="ceo@example.com", subject="Quarterly Report", body="…")
except ApprovalRejectedError as e:
    print(f"Rejected: {e}")
except ApprovalTimeoutError as e:
    print(f"Timed out: {e}")
```

The agent **blocks** at the guarded call until a reviewer approves, rejects, or the timeout fires.

### 4. Review pending requests

In a second terminal:

```bash
approvekit-review --db /tmp/approvekit.db
```

```
=== ApproveKit Reviewer ===

--- 1 pending request(s) ---

[1] send_email
  ID         : 3f7a…
  Tool       : send_email
  Args       : {'to': 'ceo@example.com', 'subject': 'Quarterly Report', …}
  Created At : 2024-01-15 10:30:00 UTC
  Status     : pending

approvekit> approve 3f7a Looks good
✓ Approved request 3f7a… for tool 'send_email'.
```

Available commands: `list`, `approve <id> [notes]`, `reject <id> [notes]`, `audit`, `quit`.

---

## Running the Demo

```bash
# Terminal 1 – start the agent
python demo/agent.py

# Terminal 2 – review pending requests
approvekit-review --db /tmp/approvekit_demo.db
```

---

## Running Tests

```bash
pytest tests/ -v
```

Tests cover:
- `test_approve.py` – happy path: auto-approve and human approval
- `test_reject.py` – reviewer rejects; tool body does not execute
- `test_timeout.py` – no reviewer acts; `ApprovalTimeoutError` is raised
- `test_policy.py` – policy rule matching, defaults, YAML/JSON loading
- `test_storage.py` – SQLite CRUD for requests and audit entries

---

## Policy Reference

| Field | Type | Default | Description |
|---|---|---|---|
| `tool` | str | required | Tool name, or `"*"` for wildcard |
| `require_approval` | bool | `false` | Block and wait for human approval |
| `timeout` | int (s) | `300` | Seconds before `ApprovalTimeoutError` |
| `auto_approve` | bool | `false` | Log and execute immediately, no human needed |
| `risk_level` | str | `"low"` | Informational: `"low"`, `"medium"`, `"high"` |

---

## License

MIT

