"""Spec-unit conformance for the AnalyzeCorpus action (MF-014).

The TLA+ model says `corpus_gate` records a pass/fail verdict over the
GENERATED CORPUS, and -- unlike `complexity_gate` -- no override input reaches
it. This runs the real CLI on both sides of the cap and checks the production
behavior matches that guard.

The load-bearing assertion is `test_a_failing_gate_never_removes_a_case`: the
same corpus that fails at cap 50 passes unchanged at cap 500, with every case
still present. Cases are never dropped, filtered, sampled, or truncated to fit
a budget.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path


def load_adapters():
    path = Path(__file__).resolve().parents[1] / "production_adapters.py"
    spec = importlib.util.spec_from_file_location("mf014_production_adapters", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_case_cap_is_a_hard_gate_on_both_sides(tmp_path: Path) -> None:
    adapters = load_adapters()
    result = adapters.AnalyzeCorpusAdapter().apply(tmp_path)

    assert result["over_cap_exit_code"] == 1, result["stderr"]
    assert result["raised_cap_exit_code"] == 0, result["stderr"]
    assert result["accepted"] is True, result


def test_a_failing_gate_never_removes_a_case(tmp_path: Path) -> None:
    """The corpus is complete whether the gate passes or fails."""
    adapters = load_adapters()
    result = adapters.AnalyzeCorpusAdapter().apply(tmp_path)
    assert result["corpus_unchanged_by_failing_gate"] is True
    assert result["never_offers_to_trim"] is True


def test_failure_reports_the_distribution_and_what_varies(tmp_path: Path) -> None:
    """The actionable part: the cause, not just the count."""
    adapters = load_adapters()
    result = adapters.AnalyzeCorpusAdapter().apply(tmp_path)
    assert result["reports_count_per_action_and_label_class"] is True
    assert result["reports_dominant_strata"] is True
    assert result["reports_starved_strata"] is True
    assert result["reports_what_varies_across_redundant_group"] is True
    assert result["names_representation_cause"] is True


def test_raising_the_cap_is_the_offered_accept_path(tmp_path: Path) -> None:
    """Caps are per-program and negotiable; trimming is not an option at all."""
    adapters = load_adapters()
    result = adapters.AnalyzeCorpusAdapter().apply(tmp_path)
    assert result["cap_raise_accept_path_offered"] is True


def test_over_cap_output_asks_the_redesign_question_never_prescribes(tmp_path: Path) -> None:
    """CD-04: the gate states the finding and asks the redesign question,
    naming the complexity descriptor and references/complexity_intuition.md
    as the judgment inputs; prescriptive-move wording must never return."""
    adapters = load_adapters()
    result = adapters.AnalyzeCorpusAdapter().apply(tmp_path)
    assert result["asks_redesign_question_never_prescribes"] is True


def test_named_regression_traces_are_always_retained(tmp_path: Path) -> None:
    adapters = load_adapters()
    result = adapters.AnalyzeCorpusAdapter().apply(tmp_path)
    assert result["regression_traces_retained"] is True
