"""
Integration tests for SwarmProof v2 Multi-Oracle Pipeline and SwarmLock 2PL Barrier Bridge.
"""

import tempfile
from pathlib import Path
import pytest

from swarmproof.bridge import SwarmproofBridge
from swarmproof.oracles.ast_oracle import ASTOracle
from swarmproof.oracles.type_oracle import TypeOracle
from swarmproof.proof import ProofCertificateGenerator
from swarmproof.rules import InvariantEngine


def test_ast_oracle_detects_syntax_and_suppression():
    with tempfile.TemporaryDirectory() as tmpdir:
        f_bad_syntax = Path(tmpdir) / "bad_syntax.py"
        f_bad_syntax.write_text("def broken_fn(:\n    return 42\n", encoding="utf-8")

        diags_syntax = ASTOracle.verify_file(f_bad_syntax)
        assert len(diags_syntax) == 1
        assert diags_syntax[0].error_type == "SyntaxError"

        f_suppression = Path(tmpdir) / "suppression.py"
        f_suppression.write_text("def risky():\n    try:\n        do_something()\n    except Exception:\n        pass\n", encoding="utf-8")

        diags_suppression = ASTOracle.verify_file(f_suppression)
        assert len(diags_suppression) == 1
        assert diags_suppression[0].error_type == "SuppressedExceptionError"


def test_invariant_engine_blocks_prohibited_imports():
    with tempfile.TemporaryDirectory() as tmpdir:
        f_insecure = Path(tmpdir) / "insecure.py"
        f_insecure.write_text("import telnetlib\n\ndef run():\n    pass\n", encoding="utf-8")

        diags = InvariantEngine.verify_invariants(f_insecure, f_insecure.read_text())
        assert len(diags) == 1
        assert diags[0].error_type == "DisallowedImportError"
        assert "telnetlib" in diags[0].message


def test_proof_certificate_generation_and_integrity():
    clean_code = "def add(a: int, b: int) -> int:\n    return a + b\n"
    cert = ProofCertificateGenerator.generate("src/math.py", clean_code, ["ast", "types", "invariants"])
    
    assert cert.status == "VERIFIED"
    assert cert.verify_integrity(clean_code) is True
    assert cert.verify_integrity(clean_code + "\n# altered") is False


def test_bridge_verification_clean_vs_broken():
    with tempfile.TemporaryDirectory() as tmpdir:
        # 1. Clean File
        f_clean = Path(tmpdir) / "clean.py"
        f_clean.write_text("def authenticate(token: str) -> bool:\n    return len(token) > 0\n", encoding="utf-8")

        ok, cert, diags = SwarmproofBridge.verify_and_settle(f_clean, run_tests=False)
        assert ok is True
        assert cert is not None
        assert len(diags) == 0

        # 2. Broken File (Tautological assert + banned import)
        f_broken = Path(tmpdir) / "broken.py"
        f_broken.write_text("import pickle\n\ndef test_fake():\n    assert True\n", encoding="utf-8")

        ok_bad, cert_bad, diags_bad = SwarmproofBridge.verify_and_settle(f_broken, run_tests=False)
        assert ok_bad is False
        assert cert_bad is None
        assert len(diags_bad) >= 2  # Disallowed import + Tautological assert
