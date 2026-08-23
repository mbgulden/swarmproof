"""
AST & Syntax Oracle for SwarmProof v2.
Validates concrete syntax trees, detects syntax regressions, suppressed exceptions, and tautological asserts.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class ASTDiagnostic:
    file: str
    line: int
    column: int
    error_type: str
    message: str
    rule: str


class ASTOracle:
    """
    Deterministic AST & Syntax Oracle.
    """

    @classmethod
    def verify_file(cls, file_path: str | Path, content: Optional[str] = None) -> List[ASTDiagnostic]:
        diagnostics: List[ASTDiagnostic] = []
        path_str = str(file_path)

        if content is None:
            try:
                with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
            except Exception as e:
                return [ASTDiagnostic(
                    file=path_str,
                    line=1,
                    column=1,
                    error_type="IOError",
                    message=f"Cannot read file: {e}",
                    rule="ast/io-error"
                )]

        # 1. Syntax Validation
        try:
            tree = ast.parse(content, filename=path_str)
        except SyntaxError as syn_err:
            return [ASTDiagnostic(
                file=path_str,
                line=syn_err.lineno or 1,
                column=syn_err.offset or 1,
                error_type="SyntaxError",
                message=str(syn_err.msg),
                rule="syntax/invalid-syntax"
            )]

        # 2. Invariant Traversal
        for node in ast.walk(tree):
            # Flag empty except: pass (suppressed exceptions)
            if isinstance(node, ast.ExceptHandler):
                if len(node.body) == 1 and isinstance(node.body[0], ast.Pass):
                    diagnostics.append(ASTDiagnostic(
                        file=path_str,
                        line=node.lineno,
                        column=node.col_offset,
                        error_type="SuppressedExceptionError",
                        message="Suppressed exception handler ('except: pass') detected",
                        rule="ast/no-suppressed-except"
                    ))

            # Flag tautological assert True
            elif isinstance(node, ast.Assert):
                if isinstance(node.test, ast.Constant) and node.test.value is True:
                    diagnostics.append(ASTDiagnostic(
                        file=path_str,
                        line=node.lineno,
                        column=node.col_offset,
                        error_type="TautologicalAssertError",
                        message="Tautological 'assert True' detected; asserts must test real conditions",
                        rule="ast/no-tautological-assert"
                    ))

        return diagnostics
