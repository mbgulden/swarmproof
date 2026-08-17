"""
AST Assertion & Anti-Weakening Guard for SwarmProof.

Parses Python Abstract Syntax Trees (AST) to detect test assertion degradation,
tautological assert fraud, error suppression, and skip decorator injection.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Set


@dataclass
class ASTTestMetrics:
    """Quantitative and qualitative AST metrics of a test file."""

    assert_count: int = 0
    tautological_asserts: List[str] = field(default_factory=list)
    suppression_blocks: List[str] = field(default_factory=list)
    skip_decorators: List[str] = field(default_factory=list)
    test_function_names: Set[str] = field(default_factory=set)


@dataclass
class ASTDiffReport:
    """Evaluation of changes between baseline and candidate test files."""

    is_clean: bool
    violations: List[str] = field(default_factory=list)
    baseline_asserts: int = 0
    candidate_asserts: int = 0


class ASTAssertionGuard:
    """Inspects Python test files to prevent test weakening and assertion tampering."""

    @classmethod
    def is_tautological_expression(cls, node: ast.AST) -> bool:
        """
        Check if an assert test expression is mathematically trivial/tautological.
        Examples: assert True, assert 1 == 1, assert x == x, assert not False.
        """
        # assert True / assert 1
        if isinstance(node, ast.Constant):
            if bool(node.value) is True:
                return True

        # assert not False / assert not 0
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
            if isinstance(node.operand, ast.Constant) and bool(node.operand.value) is False:
                return True

        # assert x == x / assert 1 == 1
        if isinstance(node, ast.Compare):
            if len(node.ops) == 1 and isinstance(node.ops[0], (ast.Eq, ast.Is)):
                left = node.left
                right = node.comparators[0]
                # Compare AST dumps to catch literal equality like "a" == "a" or x == x
                if ast.dump(left) == ast.dump(right):
                    return True

        return False

    @classmethod
    def analyze_code(cls, source_code: str) -> ASTTestMetrics:
        """Parse source code string into ASTTestMetrics."""
        metrics = ASTTestMetrics()
        try:
            tree = ast.parse(source_code)
        except SyntaxError:
            metrics.suppression_blocks.append("SYNTAX_ERROR_IN_TEST_FILE")
            return metrics

        for node in ast.walk(tree):
            # 1. Inspect Assert nodes
            if isinstance(node, ast.Assert):
                metrics.assert_count += 1
                if cls.is_tautological_expression(node.test):
                    metrics.tautological_asserts.append(ast.unparse(node.test) if hasattr(ast, "unparse") else "tautological_assert")

            # 2. Inspect Function definitions for test functions
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name.startswith("test_") or node.name.startswith("test"):
                    metrics.test_function_names.add(node.name)

                    # Check for skip decorators (@pytest.mark.skip, @unittest.skip)
                    for decorator in node.decorator_list:
                        dec_str = ast.unparse(decorator) if hasattr(ast, "unparse") else ""
                        if any(s in dec_str.lower() for s in ["skip", "xfail"]):
                            metrics.skip_decorators.append(f"{node.name}: @{dec_str}")

                    # Check for try...except pass blocks inside test functions
                    for sub in ast.walk(node):
                        if isinstance(sub, ast.Try):
                            for handler in sub.handlers:
                                if len(handler.body) == 1 and isinstance(handler.body[0], ast.Pass):
                                    metrics.suppression_blocks.append(f"{node.name}: try/except pass")

                    # Check for exec/eval/compile calls inside test functions
                    for sub in ast.walk(node):
                        if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Name):
                            if sub.func.id in ('exec', 'eval', 'compile'):
                                metrics.suppression_blocks.append(f"{node.name}: {sub.func.id}() call")

            # 3. Check for import aliases
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name in ('pytest', 'unittest') and alias.asname:
                        metrics.suppression_blocks.append(f"ImportAlias: {alias.name} as {alias.asname}")
            elif isinstance(node, ast.ImportFrom):
                if node.module in ('pytest', 'unittest'):
                    for alias in node.names:
                        if alias.asname:
                            metrics.suppression_blocks.append(f"ImportAlias: {alias.name} as {alias.asname} from {node.module}")

        return metrics

    @classmethod
    def analyze_file(cls, file_path: str | Path) -> ASTTestMetrics:
        """Analyze a test file from disk."""
        path = Path(file_path)
        if not path.exists():
            return ASTTestMetrics()
        try:
            code = path.read_text(encoding="utf-8")
            return cls.analyze_code(code)
        except Exception:
            return ASTTestMetrics()

    @classmethod
    def diff_metrics(
        cls,
        baseline_code: str,
        candidate_code: str,
        allow_new_tests: bool = True,
    ) -> ASTDiffReport:
        """
        Compare baseline test code with candidate test code.
        Rejects assertion count decreases, new skip decorators, or tautologies.
        """
        base = cls.analyze_code(baseline_code)
        cand = cls.analyze_code(candidate_code)

        report = ASTDiffReport(
            is_clean=True,
            baseline_asserts=base.assert_count,
            candidate_asserts=cand.assert_count,
        )

        # 1. Assertion Count Check
        if cand.assert_count < base.assert_count:
            report.is_clean = False
            report.violations.append(
                f"ASSERTION_DEGRADED: Assertion count decreased from {base.assert_count} to {cand.assert_count}."
            )

        # 2. Tautological Assertions Check
        if len(cand.tautological_asserts) > len(base.tautological_asserts):
            new_tauts = [t for t in cand.tautological_asserts if t not in base.tautological_asserts]
            report.is_clean = False
            report.violations.append(
                f"TAUTOLOGY_DETECTED: Injected {len(new_tauts)} trivial assertions: {new_tauts}"
            )

        # 3. Skip Decorators Check
        if len(cand.skip_decorators) > len(base.skip_decorators):
            new_skips = [s for s in cand.skip_decorators if s not in base.skip_decorators]
            report.is_clean = False
            report.violations.append(
                f"SKIP_INJECTED: Injected {len(new_skips)} skip decorators: {new_skips}"
            )

        # 4. Suppression Blocks Check
        if len(cand.suppression_blocks) > len(base.suppression_blocks):
            new_supps = [s for s in cand.suppression_blocks if s not in base.suppression_blocks]
            report.is_clean = False
            report.violations.append(
                f"SUPPRESSION_INJECTED: Injected {len(new_supps)} try/except pass blocks: {new_supps}"
            )

        return report
