"""Tests for TestRunner, ManifestSynchronizer, and GatekeeperVerifier."""

import tempfile
from pathlib import Path
from swarmproof.core.runner import TestRunner
from swarmproof.core.synchronizer import ManifestSynchronizer
from swarmproof.core.verifier import GatekeeperVerifier
from swarmproof.schemas.evidence import EvidenceLedger
from swarmproof.schemas.manifest import DualManifest
from swarmproof.schemas.receipt import ReceiptStage, VerificationReceipt


def test_test_runner_command_capture():
    import sys
    runner = TestRunner()
    # Cross platform command (Python -c) using current python executable
    cmd = f'"{sys.executable}" -c "print(12345)"'
    receipt = runner.run_command(cmd)
    assert receipt.exit_code == 0
    assert receipt.passed is True
    assert "12345" in receipt.stdout_preview
    assert len(receipt.stdout_sha256) == 64


def test_manifest_synchronizer_write_and_verify():
    with tempfile.TemporaryDirectory() as tmp_dir:
        ledger = EvidenceLedger(
            task_id="GRO-SYNC",
            agent_id="test_agent",
            model="test_model",
            commit_sha="1" * 40,
            tree_sha="2" * 40,
            clean_diff_check=True,
        )
        receipt = VerificationReceipt.from_execution(
            stage=ReceiptStage.POST_REPAIR_GREEN,
            command="pytest",
            exit_code=0,
            stdout="OK",
            stderr="",
            duration_seconds=0.05,
        )
        ledger.add_receipt(receipt)
        manifest = DualManifest(
            task_id="GRO-SYNC",
            summary="Testing synchronization",
            status="VERIFIED_SUCCESS",
            ledger=ledger,
        )

        md_path, json_path = ManifestSynchronizer.write_dual_manifest(manifest, output_dir=tmp_dir)
        assert md_path.exists()
        assert json_path.exists()

        is_synced = ManifestSynchronizer.verify_synchronization(dir_path=tmp_dir)
        assert is_synced is True

        loaded = ManifestSynchronizer.load_from_directory(dir_path=tmp_dir)
        assert loaded is not None
        assert loaded.task_id == "GRO-SYNC"

        # Gatekeeper evaluation on disk file
        passed, report = GatekeeperVerifier.verify_file(json_path)
        assert passed is True
        assert len(report.violations) == 0
