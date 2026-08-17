"""
Security & Credential Sanitization Engine for SwarmProof.

Protects against credential leakage, command injection, and path traversal
attacks in verification receipts and evidence ledgers.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import List, Tuple

# Comprehensive regex patterns for high-entropy secrets and credentials
SECRET_PATTERNS: List[Tuple[str, re.Pattern]] = [
    ("GITHUB_PAT", re.compile(r"(ghp_[a-zA-Z0-9]{36}|github_pat_[a-zA-Z0-9_]{82})")),
    ("LINEAR_API_KEY", re.compile(r"lin_api_[a-zA-Z0-9]{40}")),
    ("OPENAI_KEY", re.compile(r"sk-[a-zA-Z0-9_-]{20,100}")),
    ("ANTHROPIC_KEY", re.compile(r"sk-ant-[a-zA-Z0-9_-]{20,100}")),
    ("GOOGLE_AI_KEY", re.compile(r"AIza[0-9A-Za-z-_]{35}")),
    ("AWS_KEY", re.compile(r"(AKIA|ASIA)[0-9A-Z]{16}")),
    ("BEARER_TOKEN", re.compile(r"(Bearer\s+)[a-zA-Z0-9\._\-]{20,}", re.IGNORECASE)),
    ("PRIVATE_KEY", re.compile(r"-----BEGIN[ A-Z_-]*PRIVATE KEY-----.*?-----END[ A-Z_-]*PRIVATE KEY-----", re.DOTALL)),
    ("PASSWORD_PARAM", re.compile(r"(password|passwd|secret|token|api_key)=['\"]?(?!\[REDACTED_SECRET\])[^&'\";\s]+['\"]?", re.IGNORECASE)),
]


class SecretScrubber:
    """Detects and redacts sensitive credentials from strings, commands, and logs."""

    @classmethod
    def scrub(cls, text: str, replacement: str = "[REDACTED_SECRET]") -> str:
        """Replace all known sensitive token patterns with redaction placeholder."""
        if not text:
            return ""
        scrubbed = text
        for name, pattern in SECRET_PATTERNS:
            scrubbed = pattern.sub(replacement, scrubbed)
        return scrubbed

    @classmethod
    def has_secrets(cls, text: str) -> bool:
        """Return True if any known sensitive token pattern is detected."""
        if not text:
            return False
        return any(pattern.search(text) for _, pattern in SECRET_PATTERNS)


class PathSanitizer:
    """Prevents directory traversal attacks when loading or saving manifests."""

    @classmethod
    def sanitize(cls, base_dir: str | Path, target_path: str | Path) -> Path:
        """
        Resolve target_path within base_dir, raising ValueError if it escapes base_dir.
        """
        base = Path(base_dir).resolve()
        target = (base / target_path).resolve()

        try:
            target.relative_to(base)
        except ValueError:
            raise ValueError(f"Path traversal detected: '{target_path}' escapes base directory '{base}'")

        return target
