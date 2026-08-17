"""Tests for SwarmProof CLI commands."""

import subprocess
import sys
import tempfile
from pathlib import Path


def test_cli_help():
    res = subprocess.run(
        [sys.executable, "-m", "swarmproof", "--help"],
        cwd=r"C:\Users\Michael Gulden\Github\swarmproof",
        capture_output=True,
        text=True,
    )
    assert res.returncode == 0
    assert "SwarmProof: Universal Multi-Agent Verification" in res.stdout


def test_cli_run_command():
    with tempfile.TemporaryDirectory() as tmp_dir:
        save_path = Path(tmp_dir) / "receipt.json"
        cmd_str = f'"{sys.executable}" -c "print(\'CLI_TEST_OK\')"'
        res = subprocess.run(
            [
                sys.executable,
                "-m",
                "swarmproof",
                "run",
                "--test",
                cmd_str,
                "--stage",
                "POST_REPAIR_GREEN",
                "--save",
                str(save_path),
            ],
            cwd=r"C:\Users\Michael Gulden\Github\swarmproof",
            capture_output=True,
            text=True,
        )
        assert res.returncode == 0
        assert "PASSED" in res.stdout
        assert save_path.exists()


def test_cli_seal_and_verify():
    with tempfile.TemporaryDirectory() as tmp_dir:
        # 1. Run and save a receipt
        rcpt_file = Path(tmp_dir) / "rcpt.json"
        cmd_exit_0 = f'"{sys.executable}" -c "exit(0)"'
        subprocess.run(
            [
                sys.executable,
                "-m",
                "swarmproof",
                "run",
                "--test",
                cmd_exit_0,
                "--save",
                str(rcpt_file),
            ],
            cwd=r"C:\Users\Michael Gulden\Github\swarmproof",
            capture_output=True,
            text=True,
        )

        # 2. Seal
        res_seal = subprocess.run(
            [
                sys.executable,
                "-m",
                "swarmproof",
                "seal",
                "--task",
                "GRO-CLI-123",
                "--agent",
                "agy",
                "--receipts",
                str(rcpt_file),
                "--dir",
                str(tmp_dir),
            ],
            cwd=r"C:\Users\Michael Gulden\Github\swarmproof",
            capture_output=True,
            text=True,
        )
        assert res_seal.returncode == 0
        assert (Path(tmp_dir) / "RESULT.md").exists()
        assert (Path(tmp_dir) / "result-packet.json").exists()

        # 3. Verify
        packet_path = Path(tmp_dir) / "result-packet.json"
        res_verify = subprocess.run(
            [
                sys.executable,
                "-m",
                "swarmproof",
                "verify",
                str(packet_path),
                "--no-git",
            ],
            cwd=r"C:\Users\Michael Gulden\Github\swarmproof",
            capture_output=True,
            text=True,
        )
        assert res_verify.returncode == 0
        assert "APPROVED" in res_verify.stdout
