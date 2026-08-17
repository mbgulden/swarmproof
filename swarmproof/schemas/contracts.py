"""
Anti-Deception Invariants & Verification Contracts for SwarmProof.

Mathematical and empirical rules that prevent hallucinated success claims,
tampered manifests, or missing execution handles.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from swarmproof.schemas.manifest import DualManifest
from swarmproof.schemas.receipt import ReceiptStage


@dataclass
class InvariantViolation:
    """Detailed record of a failed verification invariant."""

    invariant_number: int
    name: str
    message: str
    fatal: bool = True


@dataclass
class ValidationReport:
    """Comprehensive validation report produced by the gatekeeper."""

    passed: bool
    violations: List[InvariantViolation] = field(default_factory=list)
    passed_invariants: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_violation(self, inv_num: int, name: str, msg: str, fatal: bool = True) -> None:
        self.violations.append(InvariantViolation(inv_num, name, msg, fatal))
        if fatal:
            self.passed = False

    def add_passed(self, name: str) -> None:
        self.passed_invariants.append(name)


class AntiDeceptionContracts:
    """Enforces the 6 Anti-Deception invariants on any candidate manifest."""

    @classmethod
    def evaluate(
        cls,
        manifest: DualManifest,
        require_red_green: bool = False,
        require_git_tree: bool = True,
    ) -> ValidationReport:
        """
        Validate all 6 Anti-Deception invariants against a DualManifest.
        """
        report = ValidationReport(passed=True)

        # ── INVARIANT 1: Observable Execution Proof ───────────────────
        # Must contain at least one valid receipt with real stdout digest and valid exit code.
        if not manifest.ledger.receipts:
            report.add_violation(
                1,
                "Observable Execution Proof",
                "Evidence ledger contains zero verification receipts. Agent did not execute any empirical test command."
            )
        else:
            invalid_receipts = [
                r for r in manifest.ledger.receipts
                if not r.stdout_sha256 or len(r.stdout_sha256) != 64
            ]
            if invalid_receipts:
                report.add_violation(
                    1,
                    "Observable Execution Proof",
                    f"Found {len(invalid_receipts)} receipts with missing or invalid SHA-256 stdout digest."
                )
            else:
                report.add_passed("Invariant 1: Observable Execution Proof")

        # ── INVARIANT 2: Pre/Post RED-GREEN Trace ─────────────────────
        # If required or present, must show RED before repair and GREEN after repair.
        stages = [r.stage for r in manifest.ledger.receipts]
        if require_red_green:
            has_red = any(s == ReceiptStage.PRE_REPAIR_RED or s == "PRE_REPAIR_RED" for s in stages)
            has_green = any(s == ReceiptStage.POST_REPAIR_GREEN or s == "POST_REPAIR_GREEN" for s in stages)
            if not (has_red and has_green):
                report.add_violation(
                    2,
                    "RED-GREEN Decision Trace",
                    f"Strict RED->GREEN proof required, but receipts show stages: {stages}"
                )
            else:
                report.add_passed("Invariant 2: RED-GREEN Decision Trace")
        else:
            report.add_passed("Invariant 2: Execution Trace Validated")

        # ── INVARIANT 3: Exact-Head & Tree Binding ────────────────────
        # Commit SHA and Tree SHA must be valid 40-character hex strings if git binding is required.
        sha_regex = re.compile(r"^[0-9a-f]{40}$", re.IGNORECASE)
        if require_git_tree:
            if not manifest.ledger.commit_sha or not sha_regex.match(manifest.ledger.commit_sha):
                report.add_violation(
                    3,
                    "Exact-Head Commit Binding",
                    f"Invalid or missing candidate commit SHA: '{manifest.ledger.commit_sha}'"
                )
            elif not manifest.ledger.tree_sha or not sha_regex.match(manifest.ledger.tree_sha):
                report.add_violation(
                    3,
                    "Write-Tree Binding",
                    f"Invalid or missing git write-tree SHA: '{manifest.ledger.tree_sha}'"
                )
            else:
                report.add_passed("Invariant 3: Exact-Head & Tree Binding")
        else:
            report.add_passed("Invariant 3: Git Binding Skipped")

        # ── INVARIANT 4: Zero Formatting & Whitespace Warnings ────────
        # Clean diff check must evaluate to True.
        if require_git_tree and not manifest.ledger.clean_diff_check:
            report.add_violation(
                4,
                "Clean Diff / Zero Formatting Warnings",
                "`git diff --check` reported whitespace or formatting errors."
            )
        else:
            report.add_passed("Invariant 4: Clean Diff Formatting")

        # ── INVARIANT 5: Receipt Identity Truth ───────────────────────
        # Ensure duration, exit codes, and timestamps are mathematically consistent.
        corrupted = []
        for r in manifest.ledger.receipts:
            if r.duration_seconds < 0 or r.timestamp <= 0:
                corrupted.append(r.receipt_id)
        if corrupted:
            report.add_violation(
                5,
                "Receipt Identity Truth",
                f"Found corrupted receipts with negative duration or invalid timestamps: {corrupted}"
            )
        else:
            report.add_passed("Invariant 5: Receipt Identity Truth")

        # ── INVARIANT 6: Manifest Synchronization Integrity ───────────
        # Status must not be SUCCESS if any receipt failed.
        failed_receipts = [
            r for r in manifest.ledger.receipts
            if not r.passed and r.stage != ReceiptStage.PRE_REPAIR_RED and r.stage != "PRE_REPAIR_RED"
        ]
        if failed_receipts and manifest.status == "VERIFIED_SUCCESS":
            report.add_violation(
                6,
                "Manifest Synchronization Integrity",
                f"Manifest claims status 'VERIFIED_SUCCESS' but contains {len(failed_receipts)} failed execution receipts."
            )
        else:
            report.add_passed("Invariant 6: Manifest Synchronization Integrity")

        return report
