"""
Git Oracle for SwarmProof.

Deterministic, read-only git inspections computing candidate commit SHA,
tree SHA, diff cleanliness, and workspace status.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Dict, Optional, Tuple


class GitOracle:
    """Deterministic Git metadata extractor and integrity validator."""

    def __init__(self, repo_root: Optional[str | Path] = None) -> None:
        self.repo_root = Path(repo_root) if repo_root else Path.cwd()

    def _run_git(self, args: list[str]) -> Tuple[int, str, str]:
        """Run a low-level git command in the repository directory."""
        try:
            res = subprocess.run(
                ["git"] + args,
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                timeout=15,
                encoding="utf-8",
            )
            return res.returncode, res.stdout.strip(), res.stderr.strip()
        except Exception as e:
            return 1, "", str(e)

    def get_head_commit_sha(self) -> str:
        """Return the exact 40-character SHA of HEAD."""
        code, out, _ = self._run_git(["rev-parse", "HEAD"])
        return out if code == 0 else ""

    def get_tree_sha(self) -> str:
        """Return the exact 40-character write-tree SHA of current index."""
        code, out, _ = self._run_git(["write-tree"])
        return out if code == 0 else ""

    def check_diff_cleanliness(self) -> bool:
        """Check for whitespace errors or formatting corruption (git diff --check)."""
        code, _, _ = self._run_git(["diff", "--check"])
        return code == 0

    def get_diff_stat(self) -> str:
        """Return human-readable diff statistics against HEAD~1 or working tree."""
        code, out, _ = self._run_git(["diff", "--stat", "HEAD~1"])
        if code == 0 and out:
            return out
        code, out, _ = self._run_git(["diff", "--stat"])
        return out if code == 0 else ""

    def is_working_tree_clean(self) -> bool:
        """Return True if working tree has no uncommitted changes."""
        code, out, _ = self._run_git(["status", "--porcelain"])
        return code == 0 and len(out) == 0

    def collect_git_evidence(self) -> Dict[str, str | bool]:
        """Collect all git evidence into a single dictionary."""
        return {
            "commit_sha": self.get_head_commit_sha(),
            "tree_sha": self.get_tree_sha(),
            "clean_diff_check": self.check_diff_cleanliness(),
            "diff_stat": self.get_diff_stat(),
            "working_tree_clean": self.is_working_tree_clean(),
        }
