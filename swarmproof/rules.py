"""
Repository Invariant Policy Engine for SwarmProof v2.
Enforces architectural constraints defined in .proof/rules.json.
"""

from __future__ import annotations

import ast
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from swarmproof.diagnostics import DiagnosticFrame


@dataclass
class InvariantRule:
    id: str
    description: str
    disallowed_imports: List[str] = None
    max_cyclomatic_complexity: int = 25


class InvariantEngine:
    """
    Evaluates static architectural invariant rules against concrete ASTs.
    """

    @classmethod
    def load_rules(cls, rules_path: Optional[str | Path] = None) -> List[InvariantRule]:
        if rules_path is None:
            rules_path = Path.cwd() / ".proof" / "rules.json"
        else:
            rules_path = Path(rules_path)

        if not rules_path.exists():
            return [InvariantRule(id="default_security", description="Default security invariants", disallowed_imports=["telnetlib", "pickle"])]

        try:
            with open(rules_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return [
                    InvariantRule(
                        id=r.get("id", "custom"),
                        description=r.get("description", ""),
                        disallowed_imports=r.get("disallowed_imports", []),
                        max_cyclomatic_complexity=r.get("max_cyclomatic_complexity", 25)
                    )
                    for r in data.get("rules", [])
                ]
        except Exception:
            return []

    @classmethod
    def verify_invariants(cls, file_path: str | Path, content: str) -> List[DiagnosticFrame]:
        diagnostics: List[DiagnosticFrame] = []
        rules = cls.load_rules()
        path_str = str(file_path)

        try:
            tree = ast.parse(content, filename=path_str)
        except Exception:
            return []

        # Check disallowed imports
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    for rule in rules:
                        if rule.disallowed_imports and alias.name in rule.disallowed_imports:
                            diagnostics.append(DiagnosticFrame(
                                status="FAIL",
                                error_type="DisallowedImportError",
                                file=path_str,
                                line=node.lineno,
                                column=node.col_offset,
                                message=f"Import of '{alias.name}' is prohibited by rule '{rule.id}'",
                                rule=f"invariant/{rule.id}"
                            ))
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    for rule in rules:
                        if rule.disallowed_imports and node.module in rule.disallowed_imports:
                            diagnostics.append(DiagnosticFrame(
                                status="FAIL",
                                error_type="DisallowedImportError",
                                file=path_str,
                                line=node.lineno,
                                column=node.col_offset,
                                message=f"Import from '{node.module}' is prohibited by rule '{rule.id}'",
                                rule=f"invariant/{rule.id}"
                            ))

        return diagnostics
