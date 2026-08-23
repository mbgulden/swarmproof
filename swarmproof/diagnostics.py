"""
Machine-Actionable Error Diagnostics and Feedback Compactor for SwarmProof v2.
Normalizes heterogeneous error messages into compact, structured JSON diagnostic frames.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class DiagnosticFrame:
    status: str  # "PASS", "FAIL", "WARN"
    error_type: str
    file: str
    line: int
    column: int
    message: str
    rule: str
    snippet: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}


class FeedbackCompactor:
    """
    Extracts isolated snippet context from the failing AST node while discarding verbose terminal noise.
    """

    @staticmethod
    def extract_snippet(file_path: str | Path, line: int, context_lines: int = 2) -> Optional[str]:
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
            if not lines:
                return None
            idx = max(0, line - 1)
            start = max(0, idx - context_lines)
            end = min(len(lines), idx + context_lines + 1)
            return "".join(lines[start:end])
        except Exception:
            return None


class CompilerDiagnosticNormalizer:
    """
    Standardizes unstructured compiler, linter, and runtime error outputs.
    """

    @classmethod
    def normalize_pytest_output(cls, test_file: str, stdout: str, stderr: str) -> List[DiagnosticFrame]:
        diagnostics = []
        full_text = f"{stdout}\n{stderr}"
        
        # Regex to match pytest FAILED lines e.g. "FAILED tests/test_foo.py::test_bar - AssertionError: ..."
        pattern = re.compile(r"FAILED\s+([^:]+)::(\w+)\s+-\s+(\w+):\s*(.*)")
        for match in pattern.finditer(full_text):
            target_path = match.group(1).strip()
            test_fn = match.group(2).strip()
            err_type = match.group(3).strip()
            err_msg = match.group(4).strip()

            snippet = FeedbackCompactor.extract_snippet(target_path, 1)
            diagnostics.append(DiagnosticFrame(
                status="FAIL",
                error_type=err_type,
                file=target_path,
                line=1,
                column=1,
                message=f"In test `{test_fn}`: {err_msg}",
                rule="pytest/test-failure",
                snippet=snippet
            ))

        if not diagnostics and ("ERROR" in full_text or "FAILED" in full_text):
            diagnostics.append(DiagnosticFrame(
                status="FAIL",
                error_type="TestExecutionError",
                file=test_file,
                line=1,
                column=1,
                message=full_text.strip()[-300:],
                rule="pytest/runtime-error"
            ))

        return diagnostics
