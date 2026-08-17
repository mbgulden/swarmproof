# Changelog

## [0.3.0] - 2026-08-17

### 🔒 Security Hardening
- **C1**: Fixed quarantine engine file leak — pristine baseline files are now deleted in `finally` block when the original file didn't exist
- **C2**: Fixed encoding mismatch (cp1252→UTF-8 mojibake on Windows) — quarantine engine now uses binary I/O for exact byte-for-byte roundtrip
- **C3**: Fixed non-atomic dual manifest writes — now uses `tempfile` + `os.replace()` for crash-safe writes
- **H2**: Documented shell injection risk for string commands in TestRunner
- **H3**: Added 10MB file size guard to `GatekeeperVerifier.verify_file()` preventing OOM attacks
- **H4**: Expanded secret detection patterns: Slack, Stripe, Discord, URL credentials, generic JWTs
- **H8**: AST Guard now detects `exec()`/`eval()`/`compile()` calls and import aliasing of pytest/unittest in test functions

### 🐛 Bug Fixes
- **C4**: `VerificationReceipt.from_dict()` now properly coerces `stage` strings to `ReceiptStage` enum
- **C5**: Removed dead `isinstance(Enum)` check in `VerificationReceipt.to_dict()`
- **H1**: Fixed `GitOracle._run_git()` to use `encoding="utf-8"` preventing garbled output on Windows
- **H5**: Narrowed `hooks.py` chmod exception handling from `Exception` to `OSError`
- **H6**: Strengthened `EvidenceLedger.compute_ledger_hash()` to include `exit_code`, `stage`, `command`, and `passed` — preventing receipt swap attacks
- **H7**: Removed hard-coded Windows paths from CLI tests, using `Path(__file__).parent.parent`

### ✨ Improvements
- **M1**: Added PEP 561 `py.typed` marker for type checker support
- **M2**: Added MIT LICENSE file
- **M3**: Fixed README Quick Start examples to match actual CLI flags, updated invariant count to 10
- **M6**: Added negative test coverage for Invariant 2 (missing RED receipt) and Invariant 5 (negative duration)
- **M7/M8**: Added `to_dict()` serialization to `InvariantViolation` and `ValidationReport`
- **L1**: Exported all core modules from `swarmproof.core.__init__`
- **L3**: Added `[project.urls]` and Python 3.13 classifier to `pyproject.toml`

### 📊 Test Coverage
- 29 → 31 tests (added Invariant 2 and 5 negative tests)
- All 31 tests passing on Python 3.12

## [0.2.0] - 2026-08-17

### Added
- AST Assertion Guard (`ast_guard.py`) — detects test weakening, tautological asserts, skip injection
- Shadow Quarantine Engine (`quarantine.py`) — runs tests against immutable git baseline
- Secret Scrubber (`security.py`) — regex-based credential detection and redaction
- Path Sanitizer (`security.py`) — prevents directory traversal attacks
- Universal Git Hook Installer (`hooks.py`) — fail-closed pre-commit/pre-push hooks
- Invariants 7–10: Anti-Replay Freshness, RED-GREEN Command Equivalence, Credential Sanitization, Test Suite Non-Weakening
- 8 adversarial test cases

## [0.1.0] - 2026-08-17

### Added
- Core schemas: `VerificationReceipt`, `EvidenceLedger`, `DualManifest`
- 6 Anti-Deception Invariants (Observable Execution, RED-GREEN Trace, Exact-Head Binding, Clean Diff, Receipt Truth, Sync Integrity)
- `TestRunner` — black-box command execution with receipt generation
- `GitOracle` — deterministic git evidence collection
- `ManifestSynchronizer` — dual RESULT.md + result-packet.json writer
- `GatekeeperVerifier` — fail-closed verification engine
- CLI with `run`, `seal`, `verify`, `guard`, `shadow`, `hook` subcommands
