"""
Verification Receipt Schema for SwarmProof.

Immutable execution record capturing deterministic command executions,
exit codes, standard output/error digests, and environment fingerprints.
"""

from __future__ import annotations

import hashlib
import os
import platform
import sys
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional


class ReceiptStage(str, Enum):
    PRE_REPAIR_RED = "PRE_REPAIR_RED"
    POST_REPAIR_GREEN = "POST_REPAIR_GREEN"
    REGRESSION_CHECK = "REGRESSION_CHECK"
    SMOKE_CHECK = "SMOKE_CHECK"
    GENERIC_VERIFICATION = "GENERIC_VERIFICATION"


@dataclass
class VerificationReceipt:
    """Immutable proof of a single black-box command execution."""

    stage: ReceiptStage | str
    command: str
    exit_code: int
    passed: bool
    duration_seconds: float
    stdout_sha256: str
    stderr_sha256: str
    stdout_preview: str = ""
    stderr_preview: str = ""
    receipt_id: str = field(default_factory=lambda: f"rcpt-{int(time.time() * 1000)}-{str(uuid.uuid4())[:6]}")
    commit_sha: Optional[str] = None
    timestamp: float = field(default_factory=time.time)
    iso_timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    cwd: str = field(default_factory=os.getcwd)
    env_fingerprint: Dict[str, str] = field(default_factory=lambda: {
        "python_version": sys.version.split()[0],
        "os": platform.system(),
        "platform": platform.platform(),
        "node": platform.node(),
    })

    @classmethod
    def from_execution(
        cls,
        stage: ReceiptStage | str,
        command: str,
        exit_code: int,
        stdout: str,
        stderr: str,
        duration_seconds: float,
        cwd: Optional[str] = None,
        commit_sha: Optional[str] = None,
        max_preview_len: int = 65536,  # 64 KB bounded buffer
    ) -> VerificationReceipt:
        """Construct an immutable receipt with automatic secret scrubbing."""
        from swarmproof.core.security import SecretScrubber

        # Scrub sensitive credentials before computing digests or previews
        clean_command = SecretScrubber.scrub(command)
        clean_stdout = SecretScrubber.scrub(stdout)
        clean_stderr = SecretScrubber.scrub(stderr)

        stdout_bytes = clean_stdout.encode("utf-8", errors="replace")
        stderr_bytes = clean_stderr.encode("utf-8", errors="replace")
        stdout_hash = hashlib.sha256(stdout_bytes).hexdigest()
        stderr_hash = hashlib.sha256(stderr_bytes).hexdigest()

        passed = (exit_code == 0) if stage != ReceiptStage.PRE_REPAIR_RED else (exit_code != 0)

        return cls(
            stage=stage if isinstance(stage, ReceiptStage) else ReceiptStage(stage),
            command=clean_command,
            exit_code=exit_code,
            passed=passed,
            duration_seconds=round(duration_seconds, 4),
            stdout_sha256=stdout_hash,
            stderr_sha256=stderr_hash,
            stdout_preview=clean_stdout[:max_preview_len],
            stderr_preview=clean_stderr[:max_preview_len],
            cwd=cwd or os.getcwd(),
            commit_sha=commit_sha,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert receipt to dictionary representation."""
        data = asdict(self)
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> VerificationReceipt:
        """Reconstruct receipt from dictionary."""
        if 'stage' in data:
            data['stage'] = ReceiptStage(data['stage'])
        return cls(**data)
