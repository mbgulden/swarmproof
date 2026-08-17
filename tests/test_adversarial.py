"""
Comprehensive Multi-Angle Adversarial Test Suite for SwarmProof.

Penetration and evasion tests covering credential leakage, command injection,
stale replay attacks, path traversal, synthetic RED cheating, and buffer boundaries.
"""

import tempfile
import time
from pathlib import Path
import pytest

from swarmproof.core.security import PathSanitizer, SecretScrubber
from swarmproof.core.runner import TestRunner
from swarmproof.core.synchronizer import ManifestSynchronizer
from swarmproof.core.verifier import GatekeeperVerifier
from swarmproof.schemas.contracts import AntiDeceptionContracts
from swarmproof.schemas.evidence import EvidenceLedger
from swarmproof.schemas.manifest import DualManifest
from swarmproof.schemas.receipt import ReceiptStage, VerificationReceipt


# ── 1. CREDENTIAL & SECRET SANITIZATION TESTS ──────────────────────────

def test_secret_scrubber_redacts_tokens():
    fake_gh = "ghp_" + "1234567890abcdef1234567890abcdef1234"
    fake_lin = "lin_api_" + "abcdef1234567890abcdef1234567890abcdef12"
    fake_oa = "sk-proj-" + "1234567890abcdef1234567890abcdef1234567890"

    raw_text = (
        f"Auth: {fake_gh}\n"
        f"Linear: {fake_lin}\n"
        f"OpenAI: {fake_oa}\n"
        "Bearer: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.e30.t-ID\n"
        "Param: token='secret_token_value_123'"
    )
    scrubbed = SecretScrubber.scrub(raw_text)
    assert "ghp_" not in scrubbed
    assert "lin_api_" not in scrubbed
    assert "sk-proj-" not in scrubbed
    assert "[REDACTED_SECRET]" in scrubbed
    assert SecretScrubber.has_secrets(raw_text) is True
    assert SecretScrubber.has_secrets(scrubbed) is False


def test_receipt_scrubs_secrets_from_command_and_output():
    fake_gh = "ghp_" + "1234567890abcdef1234567890abcdef1234"
    receipt = VerificationReceipt.from_execution(
        stage=ReceiptStage.POST_REPAIR_GREEN,
        command="curl -H 'Authorization: Bearer my_secret_token_1234567890abcdef' https://api.example.com",
        exit_code=0,
        stdout=f"User authenticated with {fake_gh}",
        stderr="",
        duration_seconds=0.1,
    )
    assert "my_secret_token" not in receipt.command
    assert "ghp_" not in receipt.stdout_preview
    assert "[REDACTED_SECRET]" in receipt.command
    assert "[REDACTED_SECRET]" in receipt.stdout_preview



# ── 2. PATH TRAVERSAL TESTS ───────────────────────────────────────────

def test_path_traversal_write_blocked():
    with tempfile.TemporaryDirectory() as tmp_dir:
        ledger = EvidenceLedger(
            task_id="GRO-TRAVERSAL",
            agent_id="attacker",
            model="claude",
            commit_sha="a" * 40,
            tree_sha="b" * 40,
            clean_diff_check=True,
        )
        manifest = DualManifest(
            task_id="GRO-TRAVERSAL",
            summary="Attack attempt",
            status="VERIFIED_SUCCESS",
            ledger=ledger,
        )

        with pytest.raises(ValueError, match="Path traversal detected"):
            ManifestSynchronizer.write_dual_manifest(
                manifest=manifest,
                output_dir=tmp_dir,
                md_filename="../../evil.md",
            )


# ── 3. ANTI-REPLAY & STALENESS TESTS ───────────────────────────────────

def test_anti_replay_rejects_stale_receipt():
    ledger = EvidenceLedger(
        task_id="GRO-REPLAY",
        agent_id="attacker",
        model="claude",
        commit_sha="a" * 40,
        tree_sha="b" * 40,
        clean_diff_check=True,
    )
    # Stale receipt timestamp (3 hours ago)
    old_timestamp = time.time() - 10800
    stale_receipt = VerificationReceipt(
        stage=ReceiptStage.POST_REPAIR_GREEN,
        command="pytest",
        exit_code=0,
        passed=True,
        duration_seconds=1.0,
        stdout_sha256="c" * 64,
        stderr_sha256="d" * 64,
        timestamp=old_timestamp,
    )
    ledger.add_receipt(stale_receipt)
    manifest = DualManifest(
        task_id="GRO-REPLAY",
        summary="Replay attack attempt",
        status="VERIFIED_SUCCESS",
        ledger=ledger,
    )
    report = AntiDeceptionContracts.evaluate(manifest)
    assert report.passed is False
    assert any("Anti-Replay Freshness" in v.name for v in report.violations)


def test_anti_replay_rejects_mismatched_commit_nonce():
    ledger = EvidenceLedger(
        task_id="GRO-NONCE",
        agent_id="attacker",
        model="claude",
        commit_sha="1111111111111111111111111111111111111111",
        tree_sha="b" * 40,
        clean_diff_check=True,
    )
    # Receipt bound to a different commit SHA
    cross_commit_receipt = VerificationReceipt(
        stage=ReceiptStage.POST_REPAIR_GREEN,
        command="pytest",
        exit_code=0,
        passed=True,
        duration_seconds=1.0,
        stdout_sha256="c" * 64,
        stderr_sha256="d" * 64,
        commit_sha="2222222222222222222222222222222222222222",
    )
    ledger.add_receipt(cross_commit_receipt)
    manifest = DualManifest(
        task_id="GRO-NONCE",
        summary="Cross commit replay attack",
        status="VERIFIED_SUCCESS",
        ledger=ledger,
    )
    report = AntiDeceptionContracts.evaluate(manifest)
    assert report.passed is False
    assert any("Commit Nonce Binding" in v.name for v in report.violations)


# ── 4. SYNTHETIC RED CHEATING & COMMAND EQUIVALENCE ────────────────────

def test_red_green_command_mismatch_rejected():
    ledger = EvidenceLedger(
        task_id="GRO-SYNTHETIC-RED",
        agent_id="attacker",
        model="claude",
        commit_sha="a" * 40,
        tree_sha="b" * 40,
        clean_diff_check=True,
    )
    # Agent tries to fake RED with a dummy syntax error
    fake_red = VerificationReceipt.from_execution(
        stage=ReceiptStage.PRE_REPAIR_RED,
        command='python -c "syntax error here"',
        exit_code=1,
        stdout="",
        stderr="SyntaxError",
        duration_seconds=0.05,
    )
    # But real GREEN is the auth test
    real_green = VerificationReceipt.from_execution(
        stage=ReceiptStage.POST_REPAIR_GREEN,
        command="pytest tests/test_auth.py",
        exit_code=0,
        stdout="1 passed",
        stderr="",
        duration_seconds=0.1,
    )
    ledger.add_receipt(fake_red)
    ledger.add_receipt(real_green)

    manifest = DualManifest(
        task_id="GRO-SYNTHETIC-RED",
        summary="Synthetic RED attack",
        status="VERIFIED_SUCCESS",
        ledger=ledger,
    )
    report = AntiDeceptionContracts.evaluate(manifest, require_red_green=True)
    assert report.passed is False
    assert any("RED-GREEN Command Target Equivalence" in v.name for v in report.violations)


# ── 5. SAFE TOKENIZED EXECUTION TESTS ──────────────────────────────────

def test_safe_tokenized_execution_without_shell():
    import sys
    runner = TestRunner()
    # Execute as tokenized list (shell=False)
    receipt = runner.run_command([sys.executable, "-c", "print('TOKENIZED_SAFE')"])
    assert receipt.exit_code == 0
    assert receipt.passed is True
    assert "TOKENIZED_SAFE" in receipt.stdout_preview


def test_bounded_stdout_preview_limit():
    huge_stdout = "A" * 100000  # 100 KB
    receipt = VerificationReceipt.from_execution(
        stage=ReceiptStage.POST_REPAIR_GREEN,
        command="big_log_cmd",
        exit_code=0,
        stdout=huge_stdout,
        stderr="",
        duration_seconds=0.5,
        max_preview_len=5000,
    )
    assert len(receipt.stdout_preview) == 5000
    # But the hash covers the entire 100KB string
    assert len(receipt.stdout_sha256) == 64
