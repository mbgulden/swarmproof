# 🛡️ SwarmProof

[![CI](https://github.com/mbgulden/swarmproof/actions/workflows/ci.yml/badge.svg)](https://github.com/mbgulden/swarmproof/actions)
[![PyPI version](https://img.shields.io/badge/pypi-v0.3.0-blue.svg)](https://pypi.org/project/swarmproof/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Zero Hallucinations](https://img.shields.io/badge/Anti--Deception-10%20Invariants-emerald.svg)](https://github.com/mbgulden/swarmproof)

> **Universal Multi-Agent Verification & Truth Oracle Engine**  
> *Cryptographically binding empirical execution proof to AI agent task completions. Eliminating hallucinated victories, modified test suites, and unverified PR claims.*

---

## 💡 Why SwarmProof?

AI coding agents (Antigravity, Claude Code, Codex, Cursor, AutoGen, CrewAI) frequently suffer from **premature victory claims**:
- Declaring tests "passed" without executing the test harness.
- Weakening assertions (e.g. replacing complex assertions with `assert True`).
- Injecting `try/except: pass` or `@pytest.mark.skip` to suppress failing cases.
- Claiming bug fixes without demonstrating a reproducible pre-repair failure (RED trace).
- Submitting pull requests with dirty whitespace, conflict markers, or mismatched commit SHAs.

**SwarmProof** solves this by acting as an unyielding, fail-closed **Truth Oracle** that operates directly against system runtimes, Git state, and Python AST trees.

---

## 🏛️ System Architecture

```
                    ┌──────────────────────────────────────────────┐
                    │               AI Coding Agent                │
                    │   (Antigravity / Claude Code / CrewAI / ...)  │
                    └──────────────────────┬───────────────────────┘
                                           │
                                     1. Code Edit
                                           ▼
                    ┌──────────────────────────────────────────────┐
                    │           SwarmProof Runner & AST            │
                    │   - AST Anti-Weakening Guard                 │
                    │   - Tokenized Subprocess Isolation           │
                    │   - Secret Sanitization & Scrubber           │
                    └──────────────────────┬───────────────────────┘
                                           │
                               2. Cryptographic Receipts
                                           ▼
                    ┌──────────────────────────────────────────────┐
                    │            Evidence Ledger Sealer            │
                    │   - Commit SHA (git rev-parse HEAD)          │
                    │   - Tree SHA (git write-tree)                │
                    │   - Stdout/Stderr SHA-256 Hashes             │
                    │   - RED (Pre) → GREEN (Post) Traces          │
                    └──────────────────────┬───────────────────────┘
                                           │
                               3. Fail-Closed Verification
                                           ▼
    ┌─────────────────────────────────────────────────────────────────────────────┐
    │                       10 Anti-Deception Invariants Gate                     │
    │  [✓] INV-01  [✓] INV-02  [✓] INV-03  [✓] INV-04  [✓] INV-05  [✓] INV-06 ... │
    └──────────────────────────────────────┬──────────────────────────────────────┘
                                           │
                        ┌──────────────────┴──────────────────┐
                        ▼                                     ▼
             [PASS] Sealed Closeout                 [FAIL] Rejection & Auto-Repair
            (Dual Manifest Synchronized)           (Zero Hallucinated Victories)
```

---

## ⚖️ The 10 Anti-Deception Invariants

| # | Invariant | Description | Failure Mode Prevented |
|---|---|---|---|
| **INV-01** | **Observable Execution Proof** | Validates real process execution, zero exit code, and non-empty stdout/stderr signatures. | Mocked or imagined test runs. |
| **INV-02** | **RED → GREEN Decision Trace** | Requires a pre-repair failing receipt (`exit_code != 0`) followed by a post-repair pass. | "Fixed" bugs that were never broken. |
| **INV-03** | **Exact Head & Tree Binding** | Cryptographically matches `git rev-parse HEAD` and `git write-tree` to candidate worktree. | Out-of-band commit spoofing. |
| **INV-04** | **Clean Diff Verification** | Asserts zero formatting warnings, trailing whitespaces, or merge conflicts (`git diff --check`). | Corrupted or dirty PR patches. |
| **INV-05** | **Receipt Identity Truth** | Validates non-negative execution duration and non-empty SHA-256 digests. | Tampered or synthetic receipts. |
| **INV-06** | **Dual Manifest Synchronization** | Enforces 100% byte & claim equivalence between `RESULT.md` and `result-packet.json`. | Discrepancies between docs & code. |
| **INV-07** | **Anti-Replay Freshness** | Validates receipt timestamps within task lifetime and prevents reusing stale receipts. | Replaying old test passes on new bugs. |
| **INV-08** | **Command Equivalence** | Guarantees that the RED test and GREEN test executed the identical command string. | Swapping hard tests for trivial tests. |
| **INV-09** | **Secret Sanitization** | Scrubs Slack/Discord webhooks, JWTs, Stripe tokens, and API keys before ledger sealing. | Leaking secrets into evidence logs. |
| **INV-10** | **AST Anti-Weakening Guard** | Disallows assertion count reductions, tautologies (`assert True`), and skip decorators. | Cheating tests by deleting assertions. |

---

## 📦 Installation

```bash
pip install swarmproof
```

*Pure Python standard library. Zero heavy runtime dependencies.*

---

## 🚀 Quick Start & CLI Usage

### 1. Run an Isolated Test Oracle
Execute any test command through SwarmProof to capture an authenticated receipt:
```bash
# Capture post-repair passing test
swarmproof run --test "pytest tests/test_auth.py" --stage POST_REPAIR_GREEN --task GRO-4768

# Capture pre-repair failure test (for TDD compliance)
swarmproof run --test "pytest tests/test_auth.py" --stage PRE_REPAIR_RED --task GRO-4768
```

### 2. Check AST Assertion Degradation
Inspect candidate test code against baseline to verify no assertions were weakened:
```bash
swarmproof ast-guard --baseline tests/test_auth.py --candidate tests/test_auth.py
```

### 3. Seal Evidence Manifests
Generate synchronized `RESULT.md` and `result-packet.json` manifests:
```bash
swarmproof seal \
  --task "GRO-4768" \
  --agent "agy" \
  --status "VERIFIED_SUCCESS" \
  --summary "Resolved token expiration race condition with atomic refresh fence."
```

### 4. Verify Closeout Packet (Fail-Closed)
Evaluate all 10 Invariants against the generated closeout packet:
```bash
# Standard verification
swarmproof verify result-packet.json

# Strict mode (enforces Invariant 2 RED-GREEN Decision Trace)
swarmproof verify result-packet.json --strict
```

### 5. Install Universal Git Hooks
Prevent developers or agents from committing unverified code:
```bash
swarmproof hooks install
```

---

## 🐍 Python SDK Integration

Integrate SwarmProof directly into your custom agent loops or testing frameworks:

```python
from swarmproof.core.runner import TestRunner
from swarmproof.core.ast_guard import ASTAssertionGuard
from swarmproof.core.verifier import ManifestVerifier
from swarmproof.schemas.manifest import CloseoutManifest

# 1. Execute an Oracle Run
runner = TestRunner()
receipt = runner.execute("pytest tests/test_core.py", stage="POST_REPAIR_GREEN")
print(f"Captured Exit Code: {receipt.exit_code}, SHA: {receipt.stdout_sha256[:12]}")

# 2. Guard Against Assertion Weakening
ast_guard = ASTAssertionGuard()
report = ast_guard.diff_metrics(baseline_code, candidate_code)
if not report.is_clean:
    raise ValueError(f"AST Weakening detected: {report.violations}")

# 3. Verify Closeout Manifest against 10 Invariants
verifier = ManifestVerifier()
result = verifier.verify_packet(manifest_dict, strict=True)
if not result.passed:
    print("Verification Failed:", result.violations)
else:
    print("Verified Clean! Passed Invariants:", result.passed_invariants)
```

---

## 🤖 CI / CD Integration (GitHub Actions)

Add SwarmProof verification to your PR gatekeeper workflow:

```yaml
name: Agent PR Gatekeeper

on:
  pull_request:
    branches: [ main ]

jobs:
  verify-agent-claims:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout Code
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install SwarmProof
        run: pip install swarmproof

      - name: Fail-Closed Manifest Verification
        run: |
          swarmproof verify result-packet.json --strict
```

---

## 🗺️ Swarm Ecosystem

SwarmProof is part of the **Swarm Primitives Ecosystem** for autonomous agent swarms:

- 🔒 **SwarmLock**: Tokenized, non-blocking distributed advisory locks.
- ⏱️ **SwarmCron**: Native high-precision background cron scheduling.
- 🛡️ **SwarmProof**: Truth Oracle, evidence ledgers, and anti-hallucination gates.
- 🔀 **SwarmRouter**: Intelligent query routing and model cascading *(coming soon)*.
- 🧠 **SwarmCurator**: Long-term memory distillation and context compaction *(coming soon)*.

---

## 📄 License
MIT © GrowthWebDev
