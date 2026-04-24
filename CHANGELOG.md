# Changelog

All notable changes to ApproveKit are documented here.

The format follows Keep a Changelog, and ApproveKit uses Semantic Versioning.

## [Unreleased]

## [0.1.0] - 2026-04-24

### Added

- `ApproveKit.guard` decorator for approval-gated tool calls.
- Policy loading from Python dictionaries, JSON, and YAML files.
- SQLite-backed approval request and audit storage.
- CLI reviewer via `approvekit-review`.
- Local browser reviewer via `approvekit-web`.
- JSON reviewer endpoints for pending requests, approval decisions, rejection decisions, and audit history.
- Policy `redact_fields` for masking sensitive payload values before persistence.
- Policy context metadata on approval requests and audit entries.
- Guided demo agent with approve, reject, timeout/default-deny, and redaction paths (`demo/agent.py`).
- Static landing page (`index.html`) and developer documentation page (`docs.html`).
- MIT license and project metadata.
- Tests for approve, reject, timeout, policy, storage, and web reviewer.

[Unreleased]: https://github.com/thegeekajay/ApproveKit/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/thegeekajay/ApproveKit/releases/tag/v0.1.0
