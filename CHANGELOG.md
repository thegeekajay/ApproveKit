# Changelog

All notable changes to ApproveKit are documented here.

The format follows Keep a Changelog, and ApproveKit uses Semantic Versioning.

## [Unreleased]

## [0.1.2] - 2026-04-24

### Added

- Web reviewer and terminal reviewer screenshots embedded in README.
- Architecture and infographic design assets added to `assets/`.

## [0.1.1] - 2026-04-24

### Added

- `__version__` constant exported from `approvekit` package.
- One-command release helper (`release.py`) for patch/minor/major releases with automated version bumping, CHANGELOG scaffolding, build, tag, push, and GitHub release creation.
- GitHub Actions publish workflow (`.github/workflows/publish-pypi.yml`) that automatically publishes to TestPyPI then PyPI on each GitHub Release.
- Maintainer Release Flow section in README documenting the one-command release process.

### Changed

- Project URLs in `pyproject.toml` updated to custom domain (`http://approvekit.theajaykumar.com`).
- README logo image switched to HTTPS GitHub raw URL for correct rendering on PyPI and GitHub.

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

[Unreleased]: https://github.com/thegeekajay/ApproveKit/compare/v0.1.2...HEAD
[0.1.1]: https://github.com/thegeekajay/ApproveKit/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/thegeekajay/ApproveKit/releases/tag/v0.1.0
[0.1.2]: https://github.com/thegeekajay/ApproveKit/compare/v0.1.1...v0.1.2
