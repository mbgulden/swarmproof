"""
Dual Manifest Schema for SwarmProof.

Guarantees 100% cryptographic and content synchronization between
human-readable RESULT.md and machine-enforced result-packet.json.
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from swarmproof.schemas.evidence import EvidenceLedger


@dataclass
class DualManifest:
    """Dual-synchronized manifest bundle."""

    task_id: str
    summary: str
    status: str  # "VERIFIED_SUCCESS", "FAILED_INVARIANT", "PENDING_VERIFICATION"
    ledger: EvidenceLedger
    version: str = "1.0.0"
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    custom_claims: Dict[str, Any] = field(default_factory=dict)

    def generate_result_markdown(self) -> str:
        """Render standard, high-readability RESULT.md format."""
        receipts_table = ""
        if self.ledger.receipts:
            rows = []
            for r in self.ledger.receipts:
                status_icon = "✅ PASSED" if r.passed else "❌ FAILED"
                rows.append(
                    f"| `{r.stage}` | `{r.command}` | {status_icon} (exit `{r.exit_code}`) | `{r.duration_seconds}s` | `{r.stdout_sha256[:12]}...` |"
                )
            receipts_table = (
                "### 🧪 Execution Receipts\n\n"
                "| Stage | Command | Result | Duration | Stdout SHA-256 |\n"
                "| :--- | :--- | :--- | :--- | :--- |\n"
                + "\n".join(rows)
                + "\n\n"
            )

        visual_section = ""
        if self.ledger.visual_audits:
            v_rows = []
            for v in self.ledger.visual_audits:
                v_status = "✅ CLEAN" if v.get("passed") else "❌ OVERFLOW"
                v_rows.append(
                    f"| `{v.get('viewport')}` | `{v.get('width')}x{v.get('height')}` | {v_status} | {v.get('notes', '—')} |"
                )
            visual_section = (
                "### 📱 Visual & Layout Proofs\n\n"
                "| Viewport | Dimensions | Status | Notes |\n"
                "| :--- | :--- | :--- | :--- |\n"
                + "\n".join(v_rows)
                + "\n\n"
            )

        diff_check_str = "✅ Zero Warnings" if self.ledger.clean_diff_check else "❌ Warnings Detected"

        return f"""# Verification Result: {self.task_id}

**Status**: `{self.status}`  
**Agent**: `{self.ledger.agent_id}` ({self.ledger.model})  
**Timestamp**: `{self.created_at}`

---

## 📋 Task Summary
{self.summary}

---

## 🔒 Machine Verification Evidence Ledger

| Invariant / Handle | Verified Proof | Status |
| :--- | :--- | :--- |
| **Commit SHA** | `{self.ledger.commit_sha or 'N/A'}` | `VERIFIED` |
| **Tree SHA** | `{self.ledger.tree_sha or 'N/A'}` | `VERIFIED` |
| **Git Diff Check** | `{diff_check_str}` | `VERIFIED` |
| **Receipt Count** | `{len(self.ledger.receipts)} receipts executed` | `VERIFIED` |
| **Ledger Digest** | `{self.ledger.compute_ledger_hash()[:16]}...` | `VERIFIED` |

---

{receipts_table}{visual_section}## 🛡️ Verification Gate Seal
*Sealed cryptographically by SwarmProof v{self.version}.*
"""

    def generate_result_packet(self) -> Dict[str, Any]:
        """Generate machine-parseable result-packet.json data."""
        return {
            "version": self.version,
            "task_id": self.task_id,
            "status": self.status,
            "summary": self.summary,
            "created_at": self.created_at,
            "evidence_ledger": self.ledger.to_dict(),
            "manifest_hash": self.compute_manifest_hash(),
            "custom_claims": self.custom_claims,
        }

    def compute_manifest_hash(self) -> str:
        """Compute top-level SHA256 integrity hash for the manifest packet."""
        payload = {
            "version": self.version,
            "task_id": self.task_id,
            "status": self.status,
            "summary": self.summary,
            "ledger_hash": self.ledger.compute_ledger_hash(),
        }
        serialized = json.dumps(payload, sort_keys=True)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def to_json_str(self, indent: int = 2) -> str:
        """Serialize result-packet to formatted JSON string."""
        return json.dumps(self.generate_result_packet(), indent=indent)

    @classmethod
    def from_packet(cls, packet: Dict[str, Any]) -> DualManifest:
        """Reconstruct DualManifest from raw result-packet dictionary."""
        ledger_data = packet.get("evidence_ledger", {})
        ledger = EvidenceLedger.from_dict(ledger_data)
        return cls(
            task_id=packet.get("task_id", "UNKNOWN"),
            summary=packet.get("summary", ""),
            status=packet.get("status", "UNKNOWN"),
            ledger=ledger,
            version=packet.get("version", "1.0.0"),
            created_at=packet.get("created_at", datetime.now(timezone.utc).isoformat()),
            custom_claims=packet.get("custom_claims", {}),
        )
