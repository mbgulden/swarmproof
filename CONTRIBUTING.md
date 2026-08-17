# Contributing to SwarmProof

Thank you for your interest in contributing to **SwarmProof**! We welcome contributions from developers, researchers, and AI practitioners aiming to eliminate hallucinated agent completions and establish verifiable multi-agent truth oracles.

---

## 🛠️ Development Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/mbgulden/swarmproof.git
   cd swarmproof
   ```

2. **Create and activate a virtual environment**:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install editable package with dev dependencies**:
   ```bash
   pip install -e ".[dev]"
   ```

4. **Run the test suite**:
   ```bash
   pytest tests/ -v
   ```

---

## 📐 Invariant Contribution Guidelines

SwarmProof enforces **10 Anti-Deception Invariants**. When adding features or proposing new invariants:
- **Zero Hallucinated Victories**: Any new invariant must fail closed (i.e. reject execution if data is ambiguous or unverified).
- **Zero External Dependencies**: Core `swarmproof` runtime must remain pure Python standard library to ensure 100% portability across environments and Docker images.
- **TDD Requirement**: Every new invariant or fix must include both a RED failure reproduction test and a GREEN verification test.

---

## 🚀 Submitting a Pull Request

1. Fork the repo and create a feature branch (`git checkout -b feature/my-new-invariant`).
2. Commit your changes with conventional commit messages (`feat: ...`, `fix: ...`, `docs: ...`).
3. Ensure all tests pass (`pytest tests/`).
4. Ensure code formatting is clean (`git diff --check`).
5. Open a Pull Request on GitHub against `main`.
