"""
SwarmProof CLI: Universal Multi-Agent Verification & Evidence Engine.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from swarmproof.core.git_oracle import GitOracle
from swarmproof.core.runner import TestRunner
from swarmproof.core.synchronizer import ManifestSynchronizer
from swarmproof.core.verifier import GatekeeperVerifier
from swarmproof.schemas.evidence import EvidenceLedger
from swarmproof.schemas.manifest import DualManifest
from swarmproof.schemas.receipt import ReceiptStage, VerificationReceipt


def cmd_run(args: argparse.Namespace) -> int:
    """Execute a verification command and print/save the receipt."""
    runner = TestRunner()
    stage = args.stage or ReceiptStage.GENERIC_VERIFICATION
    print(f"[SwarmProof] Running verification command ({stage}): {args.test}")
    receipt = runner.run_command(args.test, stage=stage, timeout_seconds=args.timeout)

    status_str = "[PASSED]" if receipt.passed else "[FAILED]"
    print(f"{status_str} Exit Code: {receipt.exit_code} | Duration: {receipt.duration_seconds}s")
    print(f"Stdout SHA-256: {receipt.stdout_sha256}")

    if args.save:
        out_file = Path(args.save)
        out_file.write_text(json.dumps(receipt.to_dict(), indent=2), encoding="utf-8")
        print(f"Saved receipt to {out_file}")

    return receipt.exit_code


def cmd_seal(args: argparse.Namespace) -> int:
    """Collect git evidence and receipts to seal a dual manifest."""
    print(f"[SwarmProof] Sealing evidence manifest for task: {args.task}")
    git = GitOracle()
    git_evidence = git.collect_git_evidence()

    ledger = EvidenceLedger(
        task_id=args.task,
        agent_id=args.agent,
        model=args.model or "unspecified",
        commit_sha=str(git_evidence["commit_sha"]),
        tree_sha=str(git_evidence["tree_sha"]),
        clean_diff_check=bool(git_evidence["clean_diff_check"]),
        diff_stat=str(git_evidence["diff_stat"]),
    )

    # Load any receipts from file if specified
    if args.receipts:
        for r_path in args.receipts:
            try:
                r_data = json.loads(Path(r_path).read_text(encoding="utf-8"))
                ledger.add_receipt(VerificationReceipt.from_dict(r_data))
            except Exception as e:
                print(f"Warning: could not load receipt {r_path}: {e}")

    manifest = DualManifest(
        task_id=args.task,
        summary=args.summary or "Automated task completion verified by SwarmProof.",
        status="VERIFIED_SUCCESS",
        ledger=ledger,
    )

    out_dir = Path(args.dir) if args.dir else Path.cwd()
    md_path, json_path = ManifestSynchronizer.write_dual_manifest(manifest, output_dir=out_dir)

    print("Successfully sealed dual manifests:")
    print(f"   - Markdown: {md_path}")
    print(f"   - Machine Packet: {json_path}")
    print(f"   - Manifest Digest: {manifest.compute_manifest_hash()[:16]}...")
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    """Fail-closed verification check against a result packet."""
    target_file = Path(args.packet or "result-packet.json")
    print(f"[SwarmProof] Verifying evidence packet: {target_file}")

    passed, report = GatekeeperVerifier.verify_file(
        target_file,
        strict_red_green=args.strict,
        require_git=not args.no_git,
    )

    print("\n=== SWARMPROOF VERIFICATION REPORT ===")
    for passed_inv in report.passed_invariants:
        print(f"  [OK] {passed_inv}")

    if report.violations:
        print("\n[FAIL] INVARIANT VIOLATIONS:")
        for v in report.violations:
            prefix = "FATAL" if v.fatal else "WARNING"
            print(f"  [X] [{prefix}] Invariant {v.invariant_number} ({v.name}): {v.message}")
        print("\nGATE DECISION: REJECTED (Fail-Closed)")
        return 1

    print("\nGATE DECISION: APPROVED (All Invariants Verified)")
    return 0


def cmd_guard(args: argparse.Namespace) -> int:
    """Analyze test file or compare with baseline for assertion weakening."""
    from swarmproof.core.ast_guard import ASTAssertionGuard

    cand_path = Path(args.candidate)
    if not cand_path.exists():
        print(f"Error: Candidate file not found: {cand_path}")
        return 1

    cand_code = cand_path.read_text(encoding="utf-8")

    if args.baseline:
        base_path = Path(args.baseline)
        if not base_path.exists():
            print(f"Error: Baseline file not found: {base_path}")
            return 1
        base_code = base_path.read_text(encoding="utf-8")
        report = ASTAssertionGuard.diff_metrics(base_code, cand_code)

        print("\n=== SWARMPROOF AST GUARD DIFF REPORT ===")
        print(f"  Baseline Asserts: {report.baseline_asserts} | Candidate Asserts: {report.candidate_asserts}")
        if report.violations:
            print("\n[FAIL] AST VIOLATIONS DETECTED:")
            for v in report.violations:
                print(f"  ❌ {v}")
            return 1
        print("\n[OK] Test suite assertions verified intact (No weakening detected).")
        return 0
    else:
        metrics = ASTAssertionGuard.analyze_code(cand_code)
        print("\n=== SWARMPROOF AST ANALYSIS ===")
        print(f"  Total Asserts: {metrics.assert_count}")
        print(f"  Tautological Asserts: {len(metrics.tautological_asserts)}")
        print(f"  Skip Decorators: {len(metrics.skip_decorators)}")
        print(f"  Suppression Blocks: {len(metrics.suppression_blocks)}")
        if metrics.tautological_asserts or metrics.skip_decorators or metrics.suppression_blocks:
            print("\n[WARN] Potential test anti-patterns found.")
            return 1
        print("\n[OK] Test file is clean.")
        return 0


def cmd_shadow(args: argparse.Namespace) -> int:
    """Execute test oracle using immutable quarantined baseline test."""
    from swarmproof.core.quarantine import ShadowQuarantineEngine

    engine = ShadowQuarantineEngine()
    print(f"[SwarmProof] Running shadow quarantined test: {args.test_file} (ref: {args.ref})")
    receipt = engine.run_quarantined_test(
        test_file_path=args.test_file,
        test_command=args.cmd,
        git_ref=args.ref,
    )
    status_str = "[PASSED]" if receipt.passed else "[FAILED]"
    print(f"{status_str} Exit Code: {receipt.exit_code} | Duration: {receipt.duration_seconds}s")
    print(f"Stdout SHA-256: {receipt.stdout_sha256}")
    return receipt.exit_code


def cmd_hook(args: argparse.Namespace) -> int:
    """Install or uninstall universal SwarmProof git hooks."""
    from swarmproof.core.hooks import GitHookInstaller

    target_dir = args.dir or "."
    if args.action == "install":
        try:
            installed = GitHookInstaller.install_hooks(target_dir=target_dir)
            print("Successfully installed SwarmProof git hooks:")
            for name, path in installed.items():
                print(f"  ✅ {name} -> {path}")
            return 0
        except Exception as e:
            print(f"Error installing hooks: {e}")
            return 1
    elif args.action == "uninstall":
        uninstalled = GitHookInstaller.uninstall_hooks(target_dir=target_dir)
        print("SwarmProof hook removal results:")
        for name, res in uninstalled.items():
            print(f"  {'✅ Removed' if res else '⚪ Not Found'}: {name}")
        return 0
    return 1


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="swarmproof",
        description="SwarmProof: Universal Multi-Agent Verification & Truth Oracle Engine",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # run
    p_run = subparsers.add_parser("run", help="Run a verification test command")
    p_run.add_argument("--test", "-t", required=True, help="Command to execute")
    p_run.add_argument("--stage", "-s", choices=["PRE_REPAIR_RED", "POST_REPAIR_GREEN", "SMOKE_CHECK", "GENERIC_VERIFICATION"], default="GENERIC_VERIFICATION")
    p_run.add_argument("--timeout", type=float, default=60.0, help="Command timeout in seconds")
    p_run.add_argument("--save", help="Path to save output VerificationReceipt JSON")
    p_run.set_defaults(func=cmd_run)

    # seal
    p_seal = subparsers.add_parser("seal", help="Seal dual manifests from git and execution evidence")
    p_seal.add_argument("--task", required=True, help="Task or Linear Issue identifier (e.g. GRO-4768)")
    p_seal.add_argument("--agent", required=True, help="Agent identity (e.g. agy, hermes, fred)")
    p_seal.add_argument("--model", default="claude-3.7-sonnet", help="Model used (e.g. gemini-2.5-pro)")
    p_seal.add_argument("--summary", help="Human readable completion summary")
    p_seal.add_argument("--receipts", nargs="*", help="Receipt JSON files to include in ledger")
    p_seal.add_argument("--dir", default=".", help="Output directory for RESULT.md and result-packet.json")
    p_seal.set_defaults(func=cmd_seal)

    # verify
    p_verify = subparsers.add_parser("verify", help="Fail-closed evaluation of result packet")
    p_verify.add_argument("packet", nargs="?", default="result-packet.json", help="Path to result-packet.json")
    p_verify.add_argument("--strict", action="store_true", help="Require strict RED->GREEN trace")
    p_verify.add_argument("--no-git", action="store_true", help="Skip git commit/tree SHA checks")
    p_verify.set_defaults(func=cmd_verify)

    # guard
    p_guard = subparsers.add_parser("guard", help="AST analysis and assertion diffing")
    p_guard.add_argument("--candidate", "-c", required=True, help="Path to candidate test file")
    p_guard.add_argument("--baseline", "-b", help="Path to baseline test file for diff comparison")
    p_guard.set_defaults(func=cmd_guard)

    # shadow
    p_shadow = subparsers.add_parser("shadow", help="Run test oracle with quarantined baseline test")
    p_shadow.add_argument("--test-file", required=True, help="Relative path to test file")
    p_shadow.add_argument("--cmd", required=True, help="Test execution command")
    p_shadow.add_argument("--ref", default="HEAD~1", help="Git reference for baseline test")
    p_shadow.set_defaults(func=cmd_shadow)

    # hook
    p_hook = subparsers.add_parser("hook", help="Install universal git pre-commit & pre-push hooks")
    p_hook.add_argument("action", choices=["install", "uninstall"], help="Action to perform")
    p_hook.add_argument("--dir", default=".", help="Repository path")
    p_hook.set_defaults(func=cmd_hook)

    args = parser.parse_args()
    exit_code = args.func(args)
    sys.exit(exit_code)



if __name__ == "__main__":
    main()
