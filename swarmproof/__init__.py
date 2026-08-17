"""
🛡️ SwarmProof: Universal Multi-Agent Verification & Truth Oracle Engine.
"""

from swarmproof.core.git_oracle import GitOracle
from swarmproof.core.runner import TestRunner
from swarmproof.core.synchronizer import ManifestSynchronizer
from swarmproof.core.verifier import GatekeeperVerifier
from swarmproof.schemas.contracts import AntiDeceptionContracts, ValidationReport
from swarmproof.schemas.evidence import EvidenceLedger
from swarmproof.schemas.manifest import DualManifest
from swarmproof.schemas.receipt import ReceiptStage, VerificationReceipt

__version__ = "0.1.0"

__all__ = [
    "VerificationReceipt",
    "ReceiptStage",
    "EvidenceLedger",
    "DualManifest",
    "ValidationReport",
    "AntiDeceptionContracts",
    "GitOracle",
    "TestRunner",
    "ManifestSynchronizer",
    "GatekeeperVerifier",
]
