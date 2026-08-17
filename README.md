# 🛡️ SwarmProof: Universal Multi-Agent Verification & Truth Oracle Engine

**SwarmProof** is a standalone, portable Python package and CLI tool that cryptographically binds and enforces empirical verification of AI agent task completions, eliminating hallucinated victories and false PR claims across multi-agent workflows.

---

## ⚡ Key Features

1. **Deterministic RED → GREEN Test Oracle**: Captures immutable pre-repair failure signatures (RED) and verifies post-repair passes (GREEN) in isolated environments.
2. **Cryptographic Head & Tree Binding**: Computes exact candidate commit SHA (`git rev-parse HEAD`), tree SHA (`git write-tree`), and validates zero formatting errors (`git diff --check`).
3. **Dual Synchronized Manifests**: Enforces 100% synchronization between human-readable `RESULT.md` and machine-parseable `result-packet.json`.
4. **10 Anti-Deception Invariants**: Hard mathematical and runtime fences preventing false success claims, mocked tests, or modified test assertions.
5. **Fail-Closed Gatekeeper CLI**: Portable `swarmproof verify --strict` and `swarmproof verify` commands for CI pipelines, pre-commit hooks, and multi-agent orchestration hubs.

---

## 📦 Installation

```bash
pip install swarmproof
```

Or for local development:
```bash
git clone https://github.com/mbgulden/swarmproof.git
cd swarmproof
pip install -e ".[dev]"
```

---

## 🚀 Quick Start

### 1. Execute a Verified Test Run
```bash
swarmproof run --test "pytest tests/test_auth.py"
```

### 2. Seal a Verification Evidence Manifest
```bash
swarmproof seal --task "GRO-4768" --agent "agy" --summary "Fixed token expiry race condition"
```

### 3. Verify a Closeout Packet (Fail-Closed)
```bash
swarmproof verify result-packet.json --strict
```

---

## 🔒 v0.2.0 Hardening Features

- **AST Guard**: Prevents weakening of test assertions.
- **Shadow Quarantine**: Safely isolates generated code execution.
- **Secret Scrubbing**: Automatically redacts sensitive tokens from output.
- **Git Hooks**: Pre-commit hook integration for invariant enforcement.

---

## 📄 License
MIT © GrowthWebDev
