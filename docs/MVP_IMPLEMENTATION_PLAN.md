# ApproveKit MVP Implementation Tracker

ApproveKit is moving from a working Python library into a demo-ready open source MVP. This tracker is intentionally kept in the repo so the implementation can be followed through small, reviewable commits.

## Current Baseline

- Core package exists with `ApproveKit.guard`, policy evaluation, SQLite storage, approval/rejection/timeout behavior, and CLI review.
- Demo agent exists, but it does not yet show the full reviewer/web/audit story.
- Test baseline before this tracker: `python3 -m pytest -q` passes with 28 tests.
- Existing commit history already shows initial project work from April 20-21, 2026.

## MVP Goals

- [x] Add policy-level payload redaction for sensitive fields.
- [x] Store policy metadata such as `risk_level`, timeout, and approval mode with each request/audit entry.
- [x] Add a local browser reviewer for pending approvals and audit history.
- [x] Upgrade the demo so it clearly shows auto-approve, approve, reject, timeout/default-deny, and redaction.
- [x] Publish a static website and docs page explaining the product and integration path.
- [x] Add OSS polish: changelog, license, package metadata, and CI.
- [ ] Keep implementation in small commits with clear commit messages.

## Day-by-Day Build Plan

### Day 1: Core Safety and Local Reviewer

- [x] Implement redaction fields in policy rules.
- [x] Apply redaction before requests and audit entries are persisted.
- [x] Attach policy context metadata to requests/audit entries.
- [x] Add a standard-library web reviewer with JSON API endpoints.
- [x] Add tests for redaction, metadata, and web approve/reject flows.

### Day 2: Demo and Public Surface

- [x] Rewrite the demo as a guided script using one shared SQLite database.
- [x] Add README quickstart and demo instructions.
- [x] Add a static landing page with integration snippet and reviewer screenshot-style UI.
- [x] Add developer docs covering policy, reviewer UI, API shape, audit behavior, and demo commands.
- [x] Add changelog and CI workflow.

### Day 3 Buffer: Polish and Release Readiness

- [ ] Run full tests.
- [ ] Review website copy and mobile layout.
- [ ] Finalize tracker checkboxes.
- [ ] Prepare for a `v0.1.0` tag when ready.

## Demo Acceptance Criteria

- Running `python3 demo/agent.py --db /tmp/approvekit_demo.db --reset` starts a guided agent flow.
- Running `approvekit-web --db /tmp/approvekit_demo.db --port 8765` starts a browser reviewer at `http://127.0.0.1:8765`.
- The agent blocks before risky actions and resumes only when the reviewer approves.
- Rejected and timed-out actions do not execute.
- Sensitive fields configured in policy are redacted in pending requests and audit history.
- The audit view shows every terminal outcome.

## Future Roadmap

- Framework adapters for common agent/tool-calling systems.
- Slack, email, and webhook reviewer notifications.
- Postgres storage backend.
- Multi-reviewer workflows, RBAC, and SSO.
- Conditional policy rules based on arguments, tags, environment, or risk score.
- Audit export to JSON/CSV and signed audit records.
- Hosted or Docker Compose demo.
- WorkflowBench integration for approval-gated benchmark scenarios.
