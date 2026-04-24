# Changelog

All notable changes to ApproveKit are documented here.

The format follows Keep a Changelog, and ApproveKit uses Semantic Versioning.

## [Unreleased]

### Added

- Local browser reviewer via `approvekit-web`.
- JSON reviewer endpoints for pending requests, approval decisions, rejection decisions, and audit history.
- Policy `redact_fields` for masking sensitive payload values before persistence.
- Policy context metadata on approval requests and audit entries.
- Guided demo agent with approve, reject, timeout/default-deny, and redaction paths.
- Static landing page and developer documentation page.
- MVP implementation tracker in `docs/MVP_IMPLEMENTATION_PLAN.md`.
- Project metadata, MIT license, and GitHub Actions test workflow.

### Changed

- Demo policy now includes redaction settings for email bodies, production values, and PII fields.
- README now focuses on the web reviewer demo and integration path.

## [0.1.0] - 2026-04-20

### Added

- Initial `ApproveKit.guard` decorator for approval-gated tool calls.
- Policy loading from Python dictionaries, JSON, and YAML.
- SQLite-backed approval request and audit storage.
- CLI reviewer via `approvekit-review`.
- Tests for approve, reject, timeout, policy, and storage behavior.

[Unreleased]: https://github.com/thegeekajay/ApproveKit/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/thegeekajay/ApproveKit/releases/tag/v0.1.0
