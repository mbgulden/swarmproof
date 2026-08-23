"""
Hermetic Sandbox Test Oracle for SwarmProof v2.
Runs targeted test suites in isolated subprocesses with timeout enforcement.
"""

from __future__ import annotations

import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional


@dataclass
class TestResult:
    command: str
    exit_code: int
    duration_seconds: float
    stdout: str
    stderr: str
    passed: bool


class SandboxTestOracle:
    """
    Deterministic Isolated Test Execution Oracle.
    """

    @classmethod
    def run_targeted_test(
        cls,
        test_path: str | Path,
        cwd: Optional[str | Path] = None,
        timeout_seconds: float = 30.0
    ) -> TestResult:
        cmd = [sys.executable, "-m", "pytest", str(test_path), "-q", "--tb=short"]
        t_start = time.time()

        try:
            res = subprocess.run(
                cmd,
                cwd=str(cwd) if cwd else None,
                capture_output=True,
                text=True,
                timeout=timeout_seconds
            )
            duration = max(0.001, time.time() - t_start)
            return TestResult(
                command=" ".join(cmd),
                exit_code=res.returncode,
                duration_seconds=duration,
                stdout=res.stdout,
                stderr=res.stderr,
                passed=(res.returncode == 0)
            )
        except subprocess.TimeoutExpired as te:
            duration = time.time() - t_start
            return TestResult(
                command=" ".join(cmd),
                exit_code=124,
                duration_seconds=duration,
                stdout=te.stdout or "",
                stderr=f"Test timed out after {timeout_seconds} seconds",
                passed=False
            )
        except Exception as e:
            duration = time.time() - t_start
            return TestResult(
                command=" ".join(cmd),
                exit_code=1,
                duration_seconds=duration,
                stdout="",
                stderr=str(e),
                passed=False
            )
