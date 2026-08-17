"""
Evidence Ledger Schema for SwarmProof.

Structured aggregation of exact-head git bindings, execution receipts,
diff statistics, and visual UI audits.
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from swarmproof.schemas.receipt import VerificationReceipt


@dataclass
class EvidenceLedger:
    """Cryptographic machine verification evidence ledger."""

    task_id: str
    agent_id: str
    model: str
    commit_sha: str
    tree_sha: str
    clean_diff_check: bool
    receipts: List[VerificationReceipt] = field(default_factory=list)
    diff_stat: str = ""
    visual_audits: List[Dict[str, Any]] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)
    iso_timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_receipt(self, receipt: VerificationReceipt) -> None:
        """Add an execution receipt to the ledger."""
        self.receipts.append(receipt)

    def add_visual_audit(
        self,
        viewport_name: str,
        width: int,
        height: int,
        passed: bool,
        artifact_path: Optional[str] = None,
        notes: str = "",
    ) -> None:
        """Record a visual UI layout audit result."""
        self.visual_audits.append({
            "viewport": viewport_name,
            "width": width,
            "height": height,
            "passed": passed,
            "artifact_path": artifact_path,
            "notes": notes,
            "timestamp": time.time(),
        })

    def compute_ledger_hash(self) -> str:
        """Compute SHA-256 fingerprint over all core evidence attributes."""
        canonical_payload = {
            "task_id": self.task_id,
            "agent_id": self.agent_id,
            "commit_sha": self.commit_sha,
            "tree_sha": self.tree_sha,
            "clean_diff_check": self.clean_diff_check,
            "receipt_hashes": [r.stdout_sha256 + r.stderr_sha256 for r in self.receipts],
        }
        serialized = json.dumps(canonical_payload, sort_keys=True)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        """Serialize evidence ledger to dictionary."""
        return {
            "task_id": self.task_id,
            "agent_id": self.agent_id,
            "model": self.model,
            "commit_sha": self.commit_sha,
            "tree_sha": self.tree_sha,
            "clean_diff_check": self.clean_diff_check,
            "diff_stat": self.diff_stat,
            "receipts": [r.to_dict() for r in self.receipts],
            "visual_audits": self.visual_audits,
            "timestamp": self.timestamp,
            "iso_timestamp": self.iso_timestamp,
            "ledger_hash": self.compute_ledger_hash(),
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> EvidenceLedger:
        """Deserialize evidence ledger from dictionary."""
        receipts_raw = data.get("receipts", [])
        receipts = [VerificationReceipt.from_dict(r) for r in receipts_raw]
        return cls(
            task_id=data.get("task_id", "UNKNOWN"),
            agent_id=data.get("agent_id", "UNKNOWN"),
            model=data.get("model", "UNKNOWN"),
            commit_sha=data.get("commit_sha", ""),
            tree_sha=data.get("tree_sha", ""),
            clean_diff_check=data.get("clean_diff_check", False),
            receipts=receipts,
            diff_stat=data.get("diff_stat", ""),
            visual_audits=data.get("visual_audits", []),
            timestamp=data.get("timestamp", time.time()),
            iso_timestamp=data.get("iso_timestamp", datetime.now(timezone.utc).isoformat()),
            metadata=data.get("metadata", {}),
        )
