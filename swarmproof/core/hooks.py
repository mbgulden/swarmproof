"""
Universal Git Hook Installer for SwarmProof.

Installs fail-closed pre-commit and pre-push hooks across repositories,
ensuring no unverified code can be committed from any IDE, agent, or CLI.
"""

from __future__ import annotations

import os
import stat
from pathlib import Path
from typing import Dict, Optional

HOOK_SCRIPT_TEMPLATE = """#!/bin/sh
# 🛡️ SwarmProof Fail-Closed Git Verification Gate
# Blocks unverified commits lacking cryptographically valid evidence packets.

echo "[SwarmProof] Running verification gate check..."

if [ ! -f "result-packet.json" ]; then
    echo "❌ [SwarmProof REJECTED] No result-packet.json found in workspace root."
    echo "   You must run 'swarmproof seal' before committing."
    exit 1
fi

python -m swarmproof verify result-packet.json
STATUS=$?

if [ $STATUS -ne 0 ]; then
    echo "❌ [SwarmProof REJECTED] Invariant verification failed. Action blocked."
    exit 1
fi

echo "✅ [SwarmProof APPROVED] Evidence verified."
exit 0
"""


class GitHookInstaller:
    """Manages installation and removal of repository git hooks."""

    @classmethod
    def find_git_dir(cls, start_path: Optional[str | Path] = None) -> Optional[Path]:
        """Locate the .git directory for target repository."""
        curr = Path(start_path).resolve() if start_path else Path.cwd().resolve()
        while curr != curr.parent:
            git_candidate = curr / ".git"
            if git_candidate.exists():
                return git_candidate if git_candidate.is_dir() else curr
            curr = curr.parent
        return None

    @classmethod
    def install_hooks(
        cls,
        target_dir: Optional[str | Path] = None,
        install_pre_commit: bool = True,
        install_pre_push: bool = True,
    ) -> Dict[str, str]:
        """Install fail-closed SwarmProof hooks into target repo .git/hooks."""
        git_dir = cls.find_git_dir(target_dir)
        if not git_dir:
            raise ValueError(f"No git repository found at or above: {target_dir or os.getcwd()}")

        hooks_dir = git_dir / "hooks"
        hooks_dir.mkdir(parents=True, exist_ok=True)

        installed = {}

        if install_pre_commit:
            p_commit = hooks_dir / "pre-commit"
            p_commit.write_text(HOOK_SCRIPT_TEMPLATE, encoding="utf-8")
            # Set executable permissions (0o755)
            try:
                p_commit.chmod(p_commit.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
            except Exception:
                pass
            installed["pre-commit"] = str(p_commit)

        if install_pre_push:
            p_push = hooks_dir / "pre-push"
            p_push.write_text(HOOK_SCRIPT_TEMPLATE, encoding="utf-8")
            try:
                p_push.chmod(p_push.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
            except Exception:
                pass
            installed["pre-push"] = str(p_push)

        return installed

    @classmethod
    def uninstall_hooks(cls, target_dir: Optional[str | Path] = None) -> Dict[str, bool]:
        """Remove installed SwarmProof hooks from target repository."""
        git_dir = cls.find_git_dir(target_dir)
        if not git_dir:
            return {}

        hooks_dir = git_dir / "hooks"
        results = {}

        for hook_name in ["pre-commit", "pre-push"]:
            hook_file = hooks_dir / hook_name
            if hook_file.exists():
                text = hook_file.read_text(encoding="utf-8", errors="ignore")
                if "SwarmProof" in text:
                    hook_file.unlink()
                    results[hook_name] = True
                else:
                    results[hook_name] = False
            else:
                results[hook_name] = False

        return results
