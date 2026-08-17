"""
Test Runner & Black-Box Execution Oracle for SwarmProof.

Executes test suites and verification assertions, capturing empirical
execution receipts with timing and stdout/stderr hashes.
"""

from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path
from typing import Optional

from swarmproof.schemas.receipt import ReceiptStage, VerificationReceipt


class TestRunner:
    """Executes black-box test assertions and generates VerificationReceipts."""

    __test__ = False

    def __init__(self, working_dir: Optional[str | Path] = None) -> None:
        self.working_dir = Path(working_dir) if working_dir else Path.cwd()

    def run_command(
        self,
        command: str | list[str],
        stage: ReceiptStage | str = ReceiptStage.GENERIC_VERIFICATION,
        timeout_seconds: float = 60.0,
        env_vars: Optional[dict[str, str]] = None,
        use_shell: Optional[bool] = None,
    ) -> VerificationReceipt:
        """
        Execute a test command, time it, capture output, and seal a receipt.
        Supports both safe tokenized execution (shell=False) and string commands.
        """
        from swarmproof.core.git_oracle import GitOracle

        env = os.environ.copy()
        if env_vars:
            env.update(env_vars)

        is_list = isinstance(command, list)
        is_shell = use_shell if use_shell is not None else (not is_list)
        cmd_str = " ".join(command) if is_list else command

        # Attach commit SHA if git repository is present
        commit_sha = GitOracle(self.working_dir).get_head_commit_sha() or None

        start_time = time.time()
        try:
            res = subprocess.run(
                command,
                shell=is_shell,
                cwd=self.working_dir,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                env=env,
            )
            duration = time.time() - start_time
            return VerificationReceipt.from_execution(
                stage=stage,
                command=cmd_str,
                exit_code=res.returncode,
                stdout=res.stdout,
                stderr=res.stderr,
                duration_seconds=duration,
                cwd=str(self.working_dir),
                commit_sha=commit_sha,
            )
        except subprocess.TimeoutExpired as e:
            duration = time.time() - start_time
            stdout = e.stdout.decode("utf-8", errors="replace") if isinstance(e.stdout, bytes) else (e.stdout or "")
            stderr = e.stderr.decode("utf-8", errors="replace") if isinstance(e.stderr, bytes) else (e.stderr or "")
            stderr += f"\n[SwarmProof] Command timed out after {timeout_seconds}s"
            return VerificationReceipt.from_execution(
                stage=stage,
                command=cmd_str,
                exit_code=124,
                stdout=stdout,
                stderr=stderr,
                duration_seconds=duration,
                cwd=str(self.working_dir),
                commit_sha=commit_sha,
            )
        except Exception as exc:
            duration = time.time() - start_time
            return VerificationReceipt.from_execution(
                stage=stage,
                command=cmd_str,
                exit_code=1,
                stdout="",
                stderr=f"[SwarmProof] Execution failure: {exc}",
                duration_seconds=duration,
                cwd=str(self.working_dir),
                commit_sha=commit_sha,
            )

    def run_red_green_pair(
        self,
        test_command: str | list[str],
        pre_repair_check: bool = True,
        timeout_seconds: float = 60.0,
    ) -> list[VerificationReceipt]:
        """
        Execute a paired RED -> GREEN verification lifecycle on the SAME test target.
        Enforces command equivalence between pre-repair failure and post-repair success.
        """
        receipts = []
        if pre_repair_check:
            # Pre-repair test run should fail (RED)
            red_receipt = self.run_command(
                test_command,
                stage=ReceiptStage.PRE_REPAIR_RED,
                timeout_seconds=timeout_seconds,
            )
            receipts.append(red_receipt)

        # Post-repair test run should pass (GREEN)
        green_receipt = self.run_command(
            test_command,
            stage=ReceiptStage.POST_REPAIR_GREEN,
            timeout_seconds=timeout_seconds,
        )
        receipts.append(green_receipt)
        return receipts

