"""Tests for SwarmProof AST Assertion & Anti-Weakening Guard."""

from swarmproof.core.ast_guard import ASTAssertionGuard


def test_detects_tautological_assert_true():
    code = """
def test_login():
    assert True
    assert 1 == 1
    assert not False
"""
    metrics = ASTAssertionGuard.analyze_code(code)
    assert metrics.assert_count == 3
    assert len(metrics.tautological_asserts) >= 2


def test_detects_suppressed_try_except_pass():
    code = """
def test_payment():
    try:
        call_unstable_payment()
        assert 1 == 2
    except Exception:
        pass
"""
    metrics = ASTAssertionGuard.analyze_code(code)
    assert len(metrics.suppression_blocks) == 1
    assert "test_payment" in metrics.suppression_blocks[0]


def test_detects_skip_decorator_injection():
    code = """
import pytest

@pytest.mark.skip(reason="broken test bypass")
def test_critical_security():
    assert True
"""
    metrics = ASTAssertionGuard.analyze_code(code)
    assert len(metrics.skip_decorators) == 1
    assert "test_critical_security" in metrics.skip_decorators[0]


def test_diff_metrics_rejects_assertion_reduction():
    baseline = """
def test_auth():
    assert token.is_valid()
    assert token.user_id == 123
    assert token.role == "admin"
"""
    candidate = """
def test_auth():
    assert token.is_valid()
"""
    report = ASTAssertionGuard.diff_metrics(baseline, candidate)
    assert report.is_clean is False
    assert any("ASSERTION_DEGRADED" in v for v in report.violations)


def test_diff_metrics_rejects_injected_tautology():
    baseline = """
def test_auth():
    assert token.is_valid()
"""
    candidate = """
def test_auth():
    assert token.is_valid()
    assert True
"""
    report = ASTAssertionGuard.diff_metrics(baseline, candidate)
    assert report.is_clean is False
    assert any("TAUTOLOGY_DETECTED" in v for v in report.violations)


def test_diff_metrics_accepts_clean_additions():
    baseline = """
def test_auth():
    assert token.is_valid()
"""
    candidate = """
def test_auth():
    assert token.is_valid()
    assert token.role == "admin"
"""
    report = ASTAssertionGuard.diff_metrics(baseline, candidate)
    assert report.is_clean is True
    assert len(report.violations) == 0
    assert report.candidate_asserts == 2
