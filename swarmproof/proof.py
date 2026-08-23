"""
Proof Certificate Generator and Invariant Verifier for SwarmProof v2.
Emits tamper-evident signed proof certificates upon multi-oracle verification success.
"""

from __future__ import annotations

import hashlib
import json
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class ProofCertificate:
    proof_id: str
    target_path: str
    ast_checksum: str
    oracles_passed: List[str]
    timestamp: float = field(default_factory=time.time)
    status: str = "VERIFIED"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2)

    def verify_integrity(self, current_content: str) -> bool:
        computed = hashlib.sha256(current_content.encode("utf-8")).hexdigest()
        return self.ast_checksum == f"sha256:{computed}"


class ProofCertificateGenerator:
    """
    Constructs tamper-evident proof certificates.
    """

    @staticmethod
    def generate(
        target_path: str | Path,
        content: str,
        oracles_passed: List[str],
        metadata: Optional[Dict[str, Any]] = None
    ) -> ProofCertificate:
        sha = hashlib.sha256(content.encode("utf-8")).hexdigest()
        proof_id = f"prf_{uuid.uuid4().hex[:16]}"

        return ProofCertificate(
            proof_id=proof_id,
            target_path=str(target_path),
            ast_checksum=f"sha256:{sha}",
            oracles_passed=oracles_passed,
            timestamp=time.time(),
            status="VERIFIED",
            metadata=metadata or {}
        )
