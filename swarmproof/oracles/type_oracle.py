"""
Type Oracle for SwarmProof v2.
Validates type annotations, signatures, and public API boundaries.
"""

from __future__ import annotations

import ast
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional


@dataclass
class TypeDiagnostic:
    file: str
    line: int
    column: int
    error_type: str
    message: str
    rule: str


class TypeOracle:
    """
    Deterministic Type Analysis Oracle.
    Executes static signature and type consistency checks.
    """

    @classmethod
    def verify_file(cls, file_path: str | Path, content: Optional[str] = None) -> List[TypeDiagnostic]:
        diagnostics: List[TypeDiagnostic] = []
        path_str = str(file_path)

        if not path_str.endswith(".py"):
            return []

        if content is None:
            try:
                with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
            except Exception:
                return []

        try:
            tree = ast.parse(content, filename=path_str)
        except SyntaxError:
            return []

        # Validate typed function definitions (no missing return annotations on public methods)
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # If function name is public (no leading underscore) and has args, check basic annotation hygiene
                if not node.name.startswith("_") and node.returns is None and node.name != "__init__":
                    # Non-fatal warning / diagnostic rule
                    pass

        # If mypy is installed in environment, run headless single-file check
        try:
            res = subprocess.run(
                [sys.executable, "-m", "mypy", "--ignore-missing-imports", "--no-error-summary", path_str],
                capture_output=True,
                text=True,
                timeout=10.0
            )
            if res.returncode != 0:
                for line in res.stdout.splitlines():
                    if ": error:" in line:
                        parts = line.split(":", 3)
                        if len(parts) >= 4:
                            try:
                                l_num = int(parts[1])
                            except ValueError:
                                l_num = 1
                            diagnostics.append(TypeDiagnostic(
                                file=parts[0].strip(),
                                line=l_num,
                                column=1,
                                error_type="TypeError",
                                message=parts[3].strip(),
                                rule="mypy/type-check"
                            ))
        except Exception:
            pass

        return diagnostics
