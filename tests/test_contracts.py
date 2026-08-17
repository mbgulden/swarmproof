"""Tests for the 6 Anti-Deception Invariants in SwarmProof."""

from swarmproof.schemas.contracts import AntiDeceptionContracts
from swarmproof.schemas.evidence import EvidenceLedger
from swarmproof.schemas.manifest import DualManifest
from swarmproof.schemas.receipt import ReceiptStage, VerificationReceipt


def test_invariant_1_fails_on_empty_receipts():
    ledger = EvidenceLedger(
        task_id="GRO-TEST",
        agent_id="fake_agent",
        model="fake_model",
        commit_sha="a" * 40,
        tree_sha="b" * 40,
        clean_diff_check=True,
        receipts=[],
    )
    manifest = DualManifest(
        task_id="GRO-TEST",
        summary="Empty receipts attempt",
        status="VERIFIED_SUCCESS",
        ledger=ledger,
    )
    report = AntiDeceptionContracts.evaluate(manifest)
    assert report.passed is False
    assert any("Observable Execution Proof" in v.name for v in report.violations)


def test_invariant_3_fails_on_corrupted_git_shas():
    ledger = EvidenceLedger(
        task_id="GRO-TEST",
        agent_id="fake_agent",
        model="fake_model",
        commit_sha="not-a-valid-sha",
        tree_sha="also-bad",
        clean_diff_check=True,
    )
    receipt = VerificationReceipt.from_execution(
        stage=ReceiptStage.POST_REPAIR_GREEN,
        command="pytest",
        exit_code=0,
        stdout="pass",
        stderr="",
        duration_seconds=0.1,
    )
    ledger.add_receipt(receipt)
    manifest = DualManifest(
        task_id="GRO-TEST",
        summary="Bad SHA attempt",
        status="VERIFIED_SUCCESS",
        ledger=ledger,
    )
    report = AntiDeceptionContracts.evaluate(manifest, require_git_tree=True)
    assert report.passed is False
    assert any("Commit Binding" in v.name for v in report.violations)


def test_invariant_4_fails_on_dirty_diff_warnings():
    ledger = EvidenceLedger(
        task_id="GRO-TEST",
        agent_id="fake_agent",
        model="fake_model",
        commit_sha="a" * 40,
        tree_sha="b" * 40,
        clean_diff_check=False,  # FAILED
    )
    receipt = VerificationReceipt.from_execution(
        stage=ReceiptStage.POST_REPAIR_GREEN,
        command="pytest",
        exit_code=0,
        stdout="pass",
        stderr="",
        duration_seconds=0.1,
    )
    ledger.add_receipt(receipt)
    manifest = DualManifest(
        task_id="GRO-TEST",
        summary="Whitespace error attempt",
        status="VERIFIED_SUCCESS",
        ledger=ledger,
    )
    report = AntiDeceptionContracts.evaluate(manifest, require_git_tree=True)
    assert report.passed is False
    assert any("Clean Diff" in v.name for v in report.violations)


def test_invariant_6_fails_if_status_is_success_with_failed_receipt():
    ledger = EvidenceLedger(
        task_id="GRO-TEST",
        agent_id="fake_agent",
        model="fake_model",
        commit_sha="a" * 40,
        tree_sha="b" * 40,
        clean_diff_check=True,
    )
    failed_receipt = VerificationReceipt.from_execution(
        stage=ReceiptStage.POST_REPAIR_GREEN,
        command="pytest tests/",
        exit_code=1,  # FAILED
        stdout="FAILED test_something",
        stderr="",
        duration_seconds=0.1,
    )
    ledger.add_receipt(failed_receipt)
    manifest = DualManifest(
        task_id="GRO-TEST",
        summary="Lying about success",
        status="VERIFIED_SUCCESS",
        ledger=ledger,
    )
    report = AntiDeceptionContracts.evaluate(manifest)
    assert report.passed is False
    assert any("Manifest Synchronization Integrity" in v.name for v in report.violations)


def test_all_invariants_pass_on_valid_manifest():
    ledger = EvidenceLedger(
        task_id="GRO-PASS",
        agent_id="agy",
        model="claude-3.7-sonnet",
        commit_sha="f" * 40,
        tree_sha="e" * 40,
        clean_diff_check=True,
    )
    r1 = VerificationReceipt.from_execution(
        stage=ReceiptStage.PRE_REPAIR_RED,
        command="pytest tests/broken.py",
        exit_code=1,
        stdout="FAILED",
        stderr="",
        duration_seconds=0.2,
    )
    r2 = VerificationReceipt.from_execution(
        stage=ReceiptStage.POST_REPAIR_GREEN,
        command="pytest tests/broken.py",
        exit_code=0,
        stdout="PASSED",
        stderr="",
        duration_seconds=0.15,
    )
    ledger.add_receipt(r1)
    ledger.add_receipt(r2)

    manifest = DualManifest(
        task_id="GRO-PASS",
        summary="Legitimate repair with RED->GREEN proof",
        status="VERIFIED_SUCCESS",
        ledger=ledger,
    )
    report = AntiDeceptionContracts.evaluate(manifest, require_red_green=True, require_git_tree=True)
    assert report.passed is True
    assert len(report.violations) == 0
    assert len(report.passed_invariants) == 10


