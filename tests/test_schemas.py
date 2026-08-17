"""Tests for SwarmProof core schema models."""

import json
from swarmproof.schemas.evidence import EvidenceLedger
from swarmproof.schemas.manifest import DualManifest
from swarmproof.schemas.receipt import ReceiptStage, VerificationReceipt


def test_verification_receipt_creation_and_roundtrip():
    receipt = VerificationReceipt.from_execution(
        stage=ReceiptStage.POST_REPAIR_GREEN,
        command="pytest tests/",
        exit_code=0,
        stdout="5 passed in 0.2s",
        stderr="",
        duration_seconds=0.205,
    )
    assert receipt.passed is True
    assert receipt.exit_code == 0
    assert len(receipt.stdout_sha256) == 64
    assert len(receipt.stderr_sha256) == 64

    # Dict roundtrip
    d = receipt.to_dict()
    assert d["stage"] == "POST_REPAIR_GREEN"
    reconstructed = VerificationReceipt.from_dict(d)
    assert reconstructed.command == receipt.command
    assert reconstructed.stdout_sha256 == receipt.stdout_sha256


def test_evidence_ledger_hashing_and_serialization():
    ledger = EvidenceLedger(
        task_id="GRO-4768",
        agent_id="agy",
        model="claude-3.7-sonnet",
        commit_sha="a" * 40,
        tree_sha="b" * 40,
        clean_diff_check=True,
    )
    r1 = VerificationReceipt.from_execution(
        stage=ReceiptStage.PRE_REPAIR_RED,
        command="pytest tests/",
        exit_code=1,
        stdout="AssertionError: Expected 200, got 500",
        stderr="",
        duration_seconds=0.15,
    )
    r2 = VerificationReceipt.from_execution(
        stage=ReceiptStage.POST_REPAIR_GREEN,
        command="pytest tests/",
        exit_code=0,
        stdout="1 passed in 0.1s",
        stderr="",
        duration_seconds=0.10,
    )
    ledger.add_receipt(r1)
    ledger.add_receipt(r2)

    ledger_hash = ledger.compute_ledger_hash()
    assert len(ledger_hash) == 64

    d = ledger.to_dict()
    assert len(d["receipts"]) == 2
    assert d["ledger_hash"] == ledger_hash

    reconstructed = EvidenceLedger.from_dict(d)
    assert reconstructed.task_id == "GRO-4768"
    assert len(reconstructed.receipts) == 2


def test_dual_manifest_generation():
    ledger = EvidenceLedger(
        task_id="GRO-4768",
        agent_id="agy",
        model="claude-3.7-sonnet",
        commit_sha="c" * 40,
        tree_sha="d" * 40,
        clean_diff_check=True,
    )
    receipt = VerificationReceipt.from_execution(
        stage=ReceiptStage.POST_REPAIR_GREEN,
        command="pytest tests/",
        exit_code=0,
        stdout="All tests passed",
        stderr="",
        duration_seconds=1.2,
    )
    ledger.add_receipt(receipt)

    manifest = DualManifest(
        task_id="GRO-4768",
        summary="Implemented SwarmProof schema suite.",
        status="VERIFIED_SUCCESS",
        ledger=ledger,
    )

    md = manifest.generate_result_markdown()
    assert "# Verification Result: GRO-4768" in md
    assert "VERIFIED_SUCCESS" in md
    assert "POST_REPAIR_GREEN" in md
    assert "All tests passed" not in md  # table only includes hashes & status

    packet = manifest.generate_result_packet()
    assert packet["task_id"] == "GRO-4768"
    assert packet["status"] == "VERIFIED_SUCCESS"
    assert "manifest_hash" in packet

    # Roundtrip from packet
    reconstructed = DualManifest.from_packet(packet)
    assert reconstructed.task_id == manifest.task_id
    assert reconstructed.compute_manifest_hash() == manifest.compute_manifest_hash()
