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
        command: str,
        stage: ReceiptStage | str = ReceiptStage.GENERIC_VERIFICATION,
        timeout_seconds: float = 60.0,
        env_vars: Optional[dict[str, str]] = None,
    ) -> VerificationReceipt:
        """
        Execute a shell/CLI command, time it, capture output, and seal a receipt.
        """
        env = os.environ.copy()
        if env_vars:
            env.update(env_vars)

        start_time = time.time()
        try:
            res = subprocess.run(
                command,
                shell=True,
                cwd=self.working_dir,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                env=env,
            )
            duration = time.time() - start_time
            return VerificationReceipt.from_execution(
                stage=stage,
                command=command,
                exit_code=res.returncode,
                stdout=res.stdout,
                stderr=res.stderr,
                duration_seconds=duration,
                cwd=str(self.working_dir),
            )
        except subprocess.TimeoutExpired as e:
            duration = time.time() - start_time
            stdout = e.stdout.decode("utf-8", errors="replace") if isinstance(e.stdout, bytes) else (e.stdout or "")
            stderr = e.stderr.decode("utf-8", errors="replace") if isinstance(e.stderr, bytes) else (e.stderr or "")
            stderr += f"\n[SwarmProof] Command timed out after {timeout_seconds}s"
            return VerificationReceipt.from_execution(
                stage=stage,
                command=command,
                exit_code=124,
                stdout=stdout,
                stderr=stderr,
                duration_seconds=duration,
                cwd=str(self.working_dir),
            )
        except Exception as exc:
            duration = time.time() - start_time
            return VerificationReceipt.from_execution(
                stage=stage,
                command=command,
                exit_code=1,
                stdout="",
                stderr=f"[SwarmProof] Execution failure: {exc}",
                duration_seconds=duration,
                cwd=str(self.working_dir),
            )

    def run_red_green_pair(
        self,
        test_command: str,
        pre_repair_check: bool = True,
    ) -> list[VerificationReceipt]:
        """
        Execute a paired RED -> GREEN verification lifecycle.
        """
        receipts = []
        if pre_repair_check:
            # Pre-repair test run should fail (RED)
            red_receipt = self.run_command(test_command, stage=ReceiptStage.PRE_REPAIR_RED)
            receipts.append(red_receipt)

        # Post-repair test run should pass (GREEN)
        green_receipt = self.run_command(test_command, stage=ReceiptStage.POST_REPAIR_GREEN)
        receipts.append(green_receipt)
        return receipts
