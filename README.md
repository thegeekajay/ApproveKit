# ApproveKit

Human approval gates for risky AI agent actions.

ApproveKit is a lightweight, framework-agnostic Python package that wraps tool calls, evaluates simple policy rules, pauses risky actions for human review, and records every outcome in SQLite audit history.

It is built for agent builders, platform engineers, and teams who need a practical local-first approval layer before giving agents access to tools like email, production writes, record deletion, or PII access.

## What It Does

- Wrap any Python callable with `@kit.guard`.
- Auto-approve low-risk tools while still writing audit entries.
- Hold risky tool calls until a reviewer approves or rejects them.
- Default-deny on timeout.
- Redact configured payload fields before persistence.
- Review pending requests in a browser with `approvekit-web`.
- Keep a durable SQLite audit trail.

## Install

```bash
pip install approvekit
```

For local development:

```bash
python3 -m pip install -e ".[dev]"
```

## Quick Start

```python
from approvekit import ApproveKit, Policy, Storage

policy = Policy.from_dict({
    "default_timeout": 60,
    "rules": [
        {
            "tool": "send_email",
            "require_approval": True,
            "risk_level": "high",
            "redact_fields": ["body"],
        },
        {
            "tool": "read_record",
            "require_approval": False,
            "auto_approve": True,
            "risk_level": "low",
        },
    ],
})

storage = Storage(db_path="/tmp/approvekit.db")
kit = ApproveKit(policy=policy, storage=storage)

@kit.guard
def send_email(to: str, subject: str, body: str) -> dict:
    return {"status": "sent", "to": to, "subject": subject}

send_email(
    to="ceo@example.com",
    subject="Quarterly report",
    body="Sensitive content that will be redacted in storage.",
)
```

In a second terminal:

```bash
approvekit-web --db /tmp/approvekit.db --port 8765
```

Open `http://127.0.0.1:8765` to approve or reject the pending request.

## Guided Demo

Terminal 1:

```bash
python3 demo/agent.py --db /tmp/approvekit_demo.db --reset
```

Terminal 2:

```bash
approvekit-web --db /tmp/approvekit_demo.db --port 8765
```

The demo walks through:

- auto-approved read
- approval-required email
- PII access with redacted fields
- rejected delete
- production write that times out unless reviewed

The terminal reviewer is still available:

```bash
approvekit-review --db /tmp/approvekit_demo.db
```

## Policy Reference

```yaml
default_timeout: 60

rules:
  - tool: send_email
    require_approval: true
    timeout: 45
    risk_level: high
    redact_fields: [body]

  - tool: read_record
    require_approval: false
    auto_approve: true
    risk_level: low

  - tool: "*"
    require_approval: true
    risk_level: medium
```

| Field | Type | Description |
| --- | --- | --- |
| `tool` | string | Exact tool name, or `*` for fallback. |
| `require_approval` | bool | Whether a human decision is required before execution. |
| `timeout` | int | Seconds to wait before default-deny timeout. |
| `auto_approve` | bool | Execute immediately and write an approved audit entry. |
| `risk_level` | string | Informational label shown in reviewer UI and audit metadata. |
| `redact_fields` | list | Dict field names to mask before request/audit persistence. |

## Architecture

```text
Agent tool call
  -> ApproveKit guard
  -> Policy evaluation
  -> Auto-approved path OR pending request in SQLite
  -> Web/CLI reviewer decision
  -> Approved tool execution OR rejected/timeout block
  -> Audit entry
```

Only approved risky requests execute the wrapped tool body. Rejected and timed-out requests are persisted and audited without executing the action.

## Project Structure

```text
approvekit/
  core.py       # guard decorator and approval wait loop
  policy.py     # policy rules, YAML/JSON loading, redaction settings
  storage.py    # SQLite request and audit persistence
  reviewer.py   # terminal reviewer
  web.py        # local browser reviewer
demo/
  agent.py      # guided two-terminal demo
tests/
  test_*.py     # approve, reject, timeout, storage, policy, web tests
docs/
  MVP_IMPLEMENTATION_PLAN.md
```

## Development

```bash
python3 -m pip install -e ".[dev]"
python3 -m pytest -q
```

## Documentation

- Landing page: `index.html`
- Developer docs: `docs.html`
- MVP tracker: `docs/MVP_IMPLEMENTATION_PLAN.md`
- Changelog: `CHANGELOG.md`

## License

MIT
