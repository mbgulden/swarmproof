"""
Shadow Quarantine Test Engine for SwarmProof.

Executes test suites using pristine baseline test files extracted from git history,
completely insulating the verification oracle from worktree test tampering.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Optional

from swarmproof.core.runner import TestRunner
from swarmproof.schemas.receipt import ReceiptStage, VerificationReceipt


class ShadowQuarantineEngine:
    """Isolates and executes tests against immutable baseline versions."""

    def __init__(self, repo_root: Optional[str | Path] = None) -> None:
        self.repo_root = Path(repo_root) if repo_root else Path.cwd()

    def extract_git_file(self, file_rel_path: str, git_ref: str = "HEAD~1") -> Optional[str]:
        """
        Extract pristine file contents from git history at git_ref.
        """
        # Normalize path to forward slashes for git
        normalized_path = Path(file_rel_path).as_posix()
        try:
            res = subprocess.run(
                ["git", "show", f"{git_ref}:{normalized_path}"],
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                timeout=10,
            )
            if res.returncode == 0:
                return res.stdout
            return None
        except Exception:
            return None

    def run_quarantined_test(
        self,
        test_file_path: str,
        test_command: str,
        git_ref: str = "HEAD~1",
        stage: ReceiptStage | str = ReceiptStage.GENERIC_VERIFICATION,
        timeout_seconds: float = 60.0,
    ) -> VerificationReceipt:
        """
        Temporarily overlays pristine baseline test file during test execution,
        then restores working tree state in a fail-safe finally block.
        """
        target_path = Path(test_file_path)
        if not target_path.is_absolute():
            target_path = self.repo_root / target_path

        rel_path = target_path.relative_to(self.repo_root).as_posix()
        baseline_content = self.extract_git_file(rel_path, git_ref=git_ref)

        runner = TestRunner(working_dir=self.repo_root)

        if baseline_content is None:
            # Baseline test doesn't exist in git_ref (e.g. brand new test file)
            # Run test as-is
            return runner.run_command(
                command=test_command,
                stage=stage,
                timeout_seconds=timeout_seconds,
            )

        # Backup current working tree content
        original_content = target_path.read_text(encoding="utf-8") if target_path.exists() else None

        try:
            # Mount pristine baseline test file
            target_path.write_text(baseline_content, encoding="utf-8")

            # Execute oracle test runner against pristine test file
            receipt = runner.run_command(
                command=test_command,
                stage=stage,
                timeout_seconds=timeout_seconds,
            )
            return receipt
        finally:
            # Restore working tree content
            if original_content is not None:
                target_path.write_text(original_content, encoding="utf-8")
