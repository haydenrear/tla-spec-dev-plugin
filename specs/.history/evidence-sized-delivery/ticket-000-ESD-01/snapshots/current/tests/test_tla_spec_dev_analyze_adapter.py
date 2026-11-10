"""Spec-unit conformance for the AnalyzeComplexity action.

MF-036: complexity is advisory, not a gate. The TLA+ model's AnalyzeComplexity
action always succeeds (``result' = CommandResult(TRUE, ...)``) and merely
records a pass/fail verdict in ``complexity_gate``. CD-01: the command is a
DESCRIPTOR -- facts, not judgment -- with no suggested move and no
recommendations. This runs the real CLI against fixture specs on both sides of
the threshold and checks the production behavior matches: both sides exit 0,
the over-threshold side emits a warning-bearing REPORT that names a target and
states the fact, and case generation advises rather than refuses.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path


def load_adapters():
    path = Path(__file__).resolve().parents[1] / "production_adapters.py"
    spec = importlib.util.spec_from_file_location("mf011_production_adapters", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_analyze_complexity_adapter_advises_both_sides_and_never_blocks(
    tmp_path: Path,
) -> None:
    adapters = load_adapters()
    result = adapters.AnalyzeComplexityAdapter().apply(tmp_path)

    # MF-036: a complex model is a finding, not a failure -- BOTH sides exit 0.
    assert result["under_budget_exit_code"] == 0, result["stderr"]
    assert result["over_budget_exit_code"] == 0, result["stderr"]
    assert result["prints_dimension_table"] is True
    assert result["over_budget_names_dominant_dimensions"] is True
    # The over-threshold model produces a warning-bearing REPORT, not a block.
    assert result["over_budget_warns_with_facts"] is True
    # Case generation advises and proceeds; it does not refuse.
    assert result["generation_advises_not_refused"] is True
    assert result["accepted"] is True, result


def test_descriptor_makes_no_suggestions(tmp_path: Path) -> None:
    """CD-01: no suggested move, no recommendations, no projected gains.

    Validation project 1 showed the suggested-move chooser confidently wrong on
    standard TLA+ (an aliased invariant made it recommend projecting away every
    variable), so the machinery was removed. The descriptor states facts.
    """
    adapters = load_adapters()
    result = adapters.AnalyzeComplexityAdapter().apply(tmp_path)
    assert result["descriptor_makes_no_suggestions"] is True


def test_output_reports_measured_facts(tmp_path: Path) -> None:
    """Every figure is [MEASURED]; nothing projected remains in the output."""
    adapters = load_adapters()
    result = adapters.AnalyzeComplexityAdapter().apply(tmp_path)
    assert result["reports_measured_facts"] is True


# --------------------------------------------------------------------------
# REMOVED 2026-08-04 (owner direction): the four AnalyzeArchitecture cases.
# The action, the adapter and the two scanner modules behind them are gone.
# What those cases asserted is now written down instead of executed --
# references/architecture_advice.md -- because the checks were defeated
# cheaply and the assertions were passing while that was true. The one that
# survives as doctrine rather than as an assertion:
# test_a_model_that_resists_clustering_is_not_given_an_invented_cut. Refusing
# to certify what you could not see is the requirement any replacement
# inherits first.
# --------------------------------------------------------------------------
