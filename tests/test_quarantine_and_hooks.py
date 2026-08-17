"""Tests for Shadow Quarantine Engine and Universal Git Hook Installer."""

import os
import subprocess
import sys
import tempfile
from pathlib import Path

from swarmproof.core.hooks import GitHookInstaller
from swarmproof.core.quarantine import ShadowQuarantineEngine


def test_git_hook_installation_and_removal():
    with tempfile.TemporaryDirectory() as tmp_dir:
        repo_dir = Path(tmp_dir)
        # Initialize test git repo
        subprocess.run(["git", "init"], cwd=repo_dir, capture_output=True)

        # Install hooks
        installed = GitHookInstaller.install_hooks(target_dir=repo_dir)
        assert "pre-commit" in installed
        assert "pre-push" in installed

        pre_commit_path = Path(installed["pre-commit"])
        assert pre_commit_path.exists()
        assert "SwarmProof" in pre_commit_path.read_text(encoding="utf-8")

        # Uninstall hooks
        uninstalled = GitHookInstaller.uninstall_hooks(target_dir=repo_dir)
        assert uninstalled.get("pre-commit") is True
        assert uninstalled.get("pre-push") is True
        assert not pre_commit_path.exists()


def test_shadow_quarantine_executes_baseline_and_restores():
    with tempfile.TemporaryDirectory() as tmp_dir:
        repo_dir = Path(tmp_dir)
        # 1. Initialize git repo
        subprocess.run(["git", "init"], cwd=repo_dir, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=repo_dir, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=repo_dir, capture_output=True)

        # 2. Create baseline test file
        test_file = repo_dir / "test_sample.py"
        test_file.write_text("def test_ok():\n    assert 1 == 1\n", encoding="utf-8")

        subprocess.run(["git", "add", "."], cwd=repo_dir, capture_output=True)
        subprocess.run(["git", "commit", "-m", "initial test"], cwd=repo_dir, capture_output=True)

        # 3. Agent modifies test file to something broken in worktree
        test_file.write_text("def test_broken():\n    assert 1 == 2\n", encoding="utf-8")

        engine = ShadowQuarantineEngine(repo_root=repo_dir)

        # Run shadow quarantined test pointing to HEAD (which has assert 1 == 1)
        receipt = engine.run_quarantined_test(
            test_file_path="test_sample.py",
            test_command=f'"{sys.executable}" -m pytest test_sample.py',
            git_ref="HEAD",
        )

        # The quarantined run should have passed because it ran baseline HEAD (assert 1 == 1)!
        assert receipt.passed is True

        # And after the test completes, working tree content is restored to the agent's worktree!
        assert "assert 1 == 2" in test_file.read_text(encoding="utf-8")
