"""
Swarmlock 2PL Barrier Bridge for SwarmProof v2.
Connects multi-oracle verifications directly to swarmlock's VALIDATING state machine.
"""

from __future__ import annotations

import json
import logging
import os
import socket
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from swarmproof.diagnostics import DiagnosticFrame
from swarmproof.oracles.ast_oracle import ASTOracle
from swarmproof.oracles.sandbox_oracle import SandboxTestOracle
from swarmproof.oracles.type_oracle import TypeOracle
from swarmproof.proof import ProofCertificate, ProofCertificateGenerator
from swarmproof.rules import InvariantEngine

logger = logging.getLogger("swarmproof.bridge")
SWARMLOCK_SOCK = "/tmp/swarmlock.sock"


def send_swarmlock_ipc(payload: Dict[str, Any], socket_path: str = SWARMLOCK_SOCK) -> Optional[Dict[str, Any]]:
    if not os.path.exists(socket_path):
        return None
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
            client.settimeout(2.0)
            client.connect(socket_path)
            client.sendall(json.dumps(payload).encode("utf-8") + b"\n")
            line = client.recv(8192)
            if line:
                return json.loads(line.decode("utf-8").strip())
    except Exception as exc:
        logger.debug("Failed IPC send to swarmlock daemon: %s", exc)
        return None
    return None


class SwarmproofBridge:
    """
    Coordinates multi-oracle verification and drives swarmlock COMMIT / REVERT transitions.
    """

    @classmethod
    def verify_and_settle(
        cls,
        target_file: str | Path,
        tx_id: Optional[str] = None,
        holder: str = "default_agent",
        lock_id: Optional[str] = None,
        run_tests: bool = True
    ) -> Tuple[bool, Optional[ProofCertificate], List[DiagnosticFrame]]:
        path = Path(target_file)
        diagnostics: List[DiagnosticFrame] = []
        oracles_passed: List[str] = []

        if not path.exists():
            return False, None, [DiagnosticFrame(
                status="FAIL",
                error_type="FileNotFoundError",
                file=str(path),
                line=1,
                column=1,
                message=f"File '{path}' does not exist on disk",
                rule="core/file-exists"
            )]

        content = path.read_text(encoding="utf-8", errors="replace")

        # 1. AST & Syntax Oracle
        ast_diags = ASTOracle.verify_file(path, content)
        if ast_diags:
            for ad in ast_diags:
                diagnostics.append(DiagnosticFrame(
                    status="FAIL",
                    error_type=ad.error_type,
                    file=ad.file,
                    line=ad.line,
                    column=ad.column,
                    message=ad.message,
                    rule=ad.rule
                ))
        else:
            oracles_passed.append("ast")

        # 2. Invariant Rules
        inv_diags = InvariantEngine.verify_invariants(path, content)
        if inv_diags:
            diagnostics.extend(inv_diags)
        else:
            oracles_passed.append("invariants")

        # 3. Type Oracle
        type_diags = TypeOracle.verify_file(path, content)
        if type_diags:
            for td in type_diags:
                diagnostics.append(DiagnosticFrame(
                    status="FAIL",
                    error_type=td.error_type,
                    file=td.file,
                    line=td.line,
                    column=td.column,
                    message=td.message,
                    rule=td.rule
                ))
        else:
            oracles_passed.append("types")

        # 4. Sandbox Test Oracle (if matching test exists)
        if run_tests:
            test_candidate = Path("tests") / f"test_{path.stem}.py"
            if test_candidate.exists():
                res = SandboxTestOracle.run_targeted_test(test_candidate)
                if not res.passed:
                    diagnostics.append(DiagnosticFrame(
                        status="FAIL",
                        error_type="TestFailureError",
                        file=str(test_candidate),
                        line=1,
                        column=1,
                        message=f"Targeted test {test_candidate} failed with exit code {res.exit_code}: {res.stderr or res.stdout[:200]}",
                        rule="sandbox/test-pass"
                    ))
                else:
                    oracles_passed.append("sandbox")

        passed = len(diagnostics) == 0

        # Settle Swarmlock Barrier
        if passed:
            cert = ProofCertificateGenerator.generate(path, content, oracles_passed)
            send_swarmlock_ipc({
                "action": "COMMIT",
                "resource": f"file:{path}",
                "holder": holder,
                "lock_id": lock_id,
                "tx_id": tx_id
            })
            return True, cert, []
        else:
            send_swarmlock_ipc({
                "action": "REVERT",
                "resource": f"file:{path}",
                "holder": holder,
                "lock_id": lock_id,
                "tx_id": tx_id
            })
            return False, None, diagnostics