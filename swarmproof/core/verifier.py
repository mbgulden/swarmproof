"""
Fail-Closed Verification Engine for SwarmProof.

Evaluates evidence packets, enforces Anti-Deception rules, and computes
pass/fail gatekeeper verdicts for CI and PR merge control.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from swarmproof.schemas.contracts import AntiDeceptionContracts, ValidationReport
from swarmproof.schemas.manifest import DualManifest


class GatekeeperVerifier:
    """Evaluates result packets and returns fail-closed verification decisions."""

    @classmethod
    def verify_file(
        cls,
        packet_path: str | Path,
        strict_red_green: bool = False,
        require_git: bool = True,
    ) -> Tuple[bool, ValidationReport]:
        """
        Verify a result-packet.json file on disk.
        """
        path = Path(packet_path)
        if not path.exists():
            report = ValidationReport(passed=False)
            report.add_violation(0, "File Access", f"Target manifest file not found: {packet_path}")
            return False, report

        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            manifest = DualManifest.from_packet(data)
            report = AntiDeceptionContracts.evaluate(
                manifest=manifest,
                require_red_green=strict_red_green,
                require_git_tree=require_git,
            )
            return report.passed, report
        except Exception as e:
            report = ValidationReport(passed=False)
            report.add_violation(0, "Parse Error", f"Failed to parse result manifest: {e}")
            return False, report

    @classmethod
    def verify_manifest(
        cls,
        manifest: DualManifest,
        strict_red_green: bool = False,
        require_git: bool = True,
    ) -> Tuple[bool, ValidationReport]:
        """
        Verify an in-memory DualManifest instance.
        """
        report = AntiDeceptionContracts.evaluate(
            manifest=manifest,
            require_red_green=strict_red_green,
            require_git_tree=require_git,
        )
        return report.passed, report
