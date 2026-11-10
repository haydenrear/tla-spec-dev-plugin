"""Spec-unit conformance for the RunEffectConformance action (MF-013).

The TLA+ model says `effect_conformance` records a clean/gaps/dead_surface
verdict, that no override or justification input reaches it, and that a ticket
advances only on "clean". This runs the real CLI and checks the production
behavior matches that guard.

The load-bearing assertion is
`test_a_recorded_justification_does_not_prevent_the_failure`: two spec
directories identical except that one carries a recorded justification produce
the same verdict and the same exit code. That is the INVERSE test the
2026-07-18 degeneracy audit required. There is deliberately no test asserting
that suppression works -- out-of-contract justifications are withdrawn, and
this test is the regression guard against reintroducing them.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path


def load_adapters():
    path = Path(__file__).resolve().parents[1] / "production_adapters.py"
    spec = importlib.util.spec_from_file_location("mf013_production_adapters", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_findings_fail_the_command(tmp_path: Path) -> None:
    """A finding exits nonzero. Recording it is not an alternative to failing."""
    adapters = load_adapters()
    result = adapters.RunEffectConformanceAdapter().apply(tmp_path)

    assert result["findings_exit_code"] == 1, result["stderr"]
    assert result["report_written_as_evidence"] is True, result
    assert result["accepted"] is True, result


def test_a_recorded_justification_does_not_prevent_the_failure(tmp_path: Path) -> None:
    """THE inverse test. Nothing suppresses a gap report."""
    adapters = load_adapters()
    result = adapters.RunEffectConformanceAdapter().apply(tmp_path)

    assert result["justification_does_not_change_the_verdict"] is True, result
    assert result["justified_exit_code"] == result["findings_exit_code"] == 1, result


def test_suppression_attempts_are_reported_not_silently_ignored(tmp_path: Path) -> None:
    """A silently dropped waiver would let an author believe it worked."""
    adapters = load_adapters()
    result = adapters.RunEffectConformanceAdapter().apply(tmp_path)

    assert result["suppression_attempt_reported_not_honored"] is True, result
    assert result["suppression_policy_recorded_in_report"] is True, result


def test_absent_declarations_are_an_error_not_a_silent_pass(tmp_path: Path) -> None:
    """A gate that disables itself when its input is absent is degeneracy."""
    adapters = load_adapters()
    result = adapters.RunEffectConformanceAdapter().apply(tmp_path)

    assert result["no_declarations_exit_code"] == 2, result
