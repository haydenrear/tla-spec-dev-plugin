"""MF-014: corpus diagnostics and hard case caps.

The load-bearing tests here are the ones asserting that **nothing is ever
dropped**. Cases are never dropped, filtered, sampled, or truncated to fit a
budget -- not silently, and not with a recorded drop rule either. If a future
change adds such a path, `test_no_api_removes_cases_to_satisfy_a_cap` and
`test_generation_writes_every_case_even_when_the_gate_fails` are the ones that
should fail.
"""

from __future__ import annotations

import inspect
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = ROOT / "skills" / "spec-double-2"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from scripts import corpus_diagnostics as cd
from scripts.generate_cases_from_tlc_dump import ActionMetadata, Edge, render_python_package
from scripts.run_generated_case_adapters import load_cases

from corpus_fixtures import (
    DOCUMENTED_ACTIONS,
    DOCUMENTED_DISTRIBUTION,
    DOCUMENTED_TOTAL,
    DUPLICATE_SUBMISSION_ACTIONS,
    ecommerce_corpus,
    regression_trace_case,
)

EXTERNAL_CAP_50 = {"max_external_cases_per_action": 50}
INTERNAL_CAP_200 = {"max_internal_cases_per_component": 200}


# --------------------------------------------------------------------------
# The fixture reproduces the documented pathological distribution
# --------------------------------------------------------------------------


def test_fixture_matches_the_documented_ecommerce_distribution() -> None:
    cases = ecommerce_corpus()
    assert len(cases) == DOCUMENTED_TOTAL == 732

    per_action: dict[str, int] = {}
    for case in cases:
        per_action[case.input.action] = per_action.get(case.input.action, 0) + 1
    assert len(per_action) == DOCUMENTED_ACTIONS == 11
    assert per_action == {a: n for a, n, _ in DOCUMENTED_DISTRIBUTION}

    duplicates = sum(n for a, n, _ in DOCUMENTED_DISTRIBUTION if a in DUPLICATE_SUBMISSION_ACTIONS)
    assert duplicates == 504
    assert round(duplicates / DOCUMENTED_TOTAL * 100) == 69, "69% duplicate-submission variants"

    assert per_action["SubmitDuplicateAddCartItem"] == 200
    assert per_action["SubmitCreateAccount"] == 2


# --------------------------------------------------------------------------
# Nothing is ever dropped. These are the tests that define the ticket.
# --------------------------------------------------------------------------


def test_analyze_reports_every_case_and_returns_none_of_them() -> None:
    """The report accounts for the whole corpus and hands back no cases."""
    cases = ecommerce_corpus()
    report = cd.analyze_corpus(cases, view="external", budgets=EXTERNAL_CAP_50)

    assert report.total_cases == len(cases) == 732
    assert sum(report.group_counts.values()) == 732
    # Strata double-count multi-label cases by design, but every case must
    # appear in at least one stratum.
    assert sum(s.count for s in report.strata) >= 732

    # The report is counts, not cases. Nothing here can be mistaken for a
    # filtered corpus and written back out.
    assert not hasattr(report, "cases")
    assert not hasattr(report, "selected")
    assert not hasattr(report, "dropped")


def test_no_api_removes_cases_to_satisfy_a_cap() -> None:
    """No public function returns a proper subset of the corpus it was given.

    This is the structural guarantee. A distillation/trim/sample helper would
    have to return fewer cases than it received, so no function may do that.
    """
    cases = ecommerce_corpus()
    forbidden = ("distill", "trim", "sample", "prune", "truncate", "drop", "select_survivors")
    for name in dir(cd):
        assert not any(word in name.lower() for word in forbidden), (
            f"corpus_diagnostics.{name} looks like a case-removal API; "
            "cases are never dropped to fit a budget"
        )

    for name, func in inspect.getmembers(cd, inspect.isfunction):
        if func.__module__ != cd.__name__:
            continue
        source = inspect.getsource(func)
        assert "[:cap]" not in source and "[: cap]" not in source, f"{name} truncates to the cap"

    # And the observable behavior: analysis is pure with respect to the corpus.
    before = list(cases)
    cd.analyze_corpus(cases, view="external", budgets=EXTERNAL_CAP_50)
    assert cases == before, "analyze_corpus mutated the corpus it was given"


def test_there_is_no_distill_flag_on_any_entry_point() -> None:
    """An opt-in filter is still a filter. It must not exist."""
    for script in ("generate_cases_from_tlc_dump.py", "export_testgraph_cases.py", "corpus_diagnostics.py"):
        text = (SKILL_ROOT / "scripts" / script).read_text(encoding="utf-8")
        for flag in ("--distill", "--trim", "--sample", "--prune", "--max-cases"):
            assert flag not in text, f"{script} offers {flag}; opt-in filtering is forbidden"


def test_generation_writes_every_case_even_when_the_gate_fails(tmp_path: Path) -> None:
    """The package on disk is complete whether the cap gate passes or fails."""
    states = {str(i): {"n": i} for i in range(12)}
    edges = [Edge(str(i), str(i + 1), "Step") for i in range(11)]
    package_dir = tmp_path / "cases"
    prepared = render_python_package(
        module="Program", states=states, edges=edges, package_dir=package_dir, view="internal"
    )
    assert len(prepared) == 11

    # A cap of 3 against 11 cases. The gate must refuse -- and leave all 11.
    manifest = tmp_path / "spec_manifest.yaml"
    manifest.write_text(
        "module: Program\nbudgets:\n  max_internal_cases_per_component: 3\n", encoding="utf-8"
    )
    with pytest.raises(SystemExit) as excinfo:
        cd.enforce_case_cap(
            prepared, view="internal", manifest_path=manifest, source="test",
            stream=sys.stderr,
        )
    assert excinfo.value.code == 2

    written = list(load_cases(package_dir).CASES)
    assert len(written) == 11, "generation trimmed the package to fit a cap"


def test_gate_refuses_over_cap_but_the_corpus_is_untouched(tmp_path: Path) -> None:
    cases = ecommerce_corpus()
    passed, message = cd.gate_report(cases, view="external", budgets={"max_external_cases_per_action": 50})
    assert passed is False
    assert "FAIL" in message
    assert "Nothing was" in message and "trimmed" in message
    assert len(cases) == 732


# --------------------------------------------------------------------------
# Hard gate, in the shape of MF-011's state-space bound
# --------------------------------------------------------------------------


def test_cap_is_a_hard_gate_that_fails_over_budget() -> None:
    cases = ecommerce_corpus()
    report = cd.analyze_corpus(cases, view="external", budgets={"max_external_cases_per_action": 50})
    assert report.passed is False
    over = {g.key: g.count for g in report.over_cap}
    assert over["SubmitDuplicateAddCartItem"] == 200
    assert "SubmitCreateAccount" not in over, "a 2-case action is not over a 50 cap"


def test_raising_the_cap_is_the_accept_path_and_makes_the_gate_pass() -> None:
    """Caps are per-program and negotiable; raising one is how you accept."""
    cases = ecommerce_corpus()
    assert cd.analyze_corpus(cases, view="external", budgets={"max_external_cases_per_action": 50}).passed is False
    raised = cd.analyze_corpus(cases, view="external", budgets={"max_external_cases_per_action": 200})
    assert raised.passed is True
    assert raised.total_cases == 732, "accepting via the cap kept every case"


def test_accept_path_snippet_names_the_budget_the_value_and_the_rationale() -> None:
    report = cd.analyze_corpus(
        ecommerce_corpus(), view="external", budgets={"max_external_cases_per_action": 50}
    )
    snippet = cd.accept_path_snippet(report)
    assert "max_external_cases_per_action: 200" in snippet
    assert "# was 50" in snippet
    assert "source: negotiated" in snippet
    assert "rationale:" in snippet
    assert "one line" in snippet
    assert "never" in snippet and "dropped, filtered, sampled, or truncated" in snippet


def test_internal_cap_is_per_component_and_external_cap_is_per_action() -> None:
    cases = ecommerce_corpus()
    internal = cd.analyze_corpus(cases, view="internal", budgets={"max_internal_cases_per_component": 200})
    assert internal.scope == "component"
    assert internal.cap_budget == "max_internal_cases_per_component"
    # 732 cases in one component, cap 200 -> over.
    assert internal.passed is False
    assert [g.key for g in internal.over_cap] == ["component"]

    external = cd.analyze_corpus(cases, view="external", budgets={"max_external_cases_per_action": 50})
    assert external.scope == "action"
    assert external.cap_budget == "max_external_cases_per_action"


def test_caps_are_read_through_budgets_module(tmp_path: Path) -> None:
    manifest = tmp_path / "spec_manifest.yaml"
    manifest.write_text(
        "module: X\nbudgets:\n  max_external_cases_per_action: 500\n"
        "  rationale:\n    max_external_cases_per_action: \"duplicate-submission sweep is intentional\"\n",
        encoding="utf-8",
    )
    report = cd.analyze_corpus(ecommerce_corpus(), view="external", manifest_path=manifest, warn=False)
    assert report.cap == 500
    assert report.passed is True


# --------------------------------------------------------------------------
# The actionable part: what varies across the redundant group
# --------------------------------------------------------------------------


def _group(report: cd.CorpusReport, key: str) -> cd.RedundantGroup:
    return next(g for g in report.over_cap if g.key == key)


@pytest.fixture(scope="module")
def failing_report() -> cd.CorpusReport:
    return cd.analyze_corpus(
        ecommerce_corpus(), view="external", budgets={"max_external_cases_per_action": 50}
    )


def test_diagnoses_action_enabled_across_equivalent_states(failing_report: cd.CorpusReport) -> None:
    group = _group(failing_report, "SubmitDuplicateAddCartItem")
    assert group.cause == "action enabled across equivalent states"
    assert group.distinct_change_shapes == 1
    assert group.distinct_source_states == 200


def test_diagnoses_interchangeable_values(failing_report: cd.CorpusReport) -> None:
    group = _group(failing_report, "SubmitDuplicateCheckout")
    assert group.cause == "interchangeable values"
    fields = {v.field for v in group.varying}
    assert "params.client" in fields and "params.sku" in fields


def test_diagnoses_unconstrained_ordering(failing_report: cd.CorpusReport) -> None:
    group = _group(failing_report, "SubmitDuplicateCreateAccount")
    assert group.cause == "unconstrained ordering"
    assert any(v.permutation_family for v in group.varying)


def test_reports_counts_dominant_and_starved_strata(failing_report: cd.CorpusReport) -> None:
    dominant, starved = cd.dominant_and_starved(failing_report.strata)
    assert dominant[0].action == "SubmitDuplicateAddCartItem"
    assert dominant[0].count == 200
    assert starved[-1].action == "SubmitCreateAccount"
    assert starved[-1].count == 2


def test_report_names_what_varies_and_what_is_held_constant(failing_report: cd.CorpusReport) -> None:
    rendered = cd.render_report(failing_report)
    assert "What VARIES across the redundant group" in rendered
    assert "Held CONSTANT across the group" in rendered
    assert "permutations of one multiset" in rendered
    assert "Skew:" in rendered and "100x" in rendered


# The exact wording family CD-04 removed (resolving VAL-13). If any of these
# reappears in gate output or help text, the redesign-question doctrine has
# regressed to prescribing moves.
PRESCRIPTIVE_MOVE_WORDING = (
    "Suggested move",
    "SUGGESTED MOVE",
    "RECOMMENDATION REQUIRING USER APPROVAL",
    "Apply the suggested",
    "Abstract the before-state",
    "Add a state constraint",
    "Declare the interchangeable values",
    "FIX THE DIAGRAM",
)


def test_over_cap_output_asks_the_redesign_question_and_prescribes_nothing(
    failing_report: cd.CorpusReport,
) -> None:
    """CD-04: the gate states the measurement, then asks a question.

    It never prescribes a move and nothing is auto-applied; the judgment
    inputs it names are the complexity descriptor (`analyze complexity`) and
    references/complexity_intuition.md.
    """
    rendered = cd.render_report(failing_report)
    assert "REDESIGN QUESTION" in rendered
    assert "redesigned to make the" in rendered and "program simpler" in rendered
    assert "analyze complexity" in rendered
    assert "references/complexity_intuition.md" in rendered
    assert "applied automatically" in rendered  # "nothing is applied automatically"
    for banned in PRESCRIPTIVE_MOVE_WORDING:
        assert banned not in rendered, f"prescriptive-move wording returned: {banned!r}"


# --------------------------------------------------------------------------
# Labelers are diagnostic strata, never selection criteria
# --------------------------------------------------------------------------


def test_labels_stratify_the_report_but_never_change_the_case_count() -> None:
    cases = ecommerce_corpus()
    baseline = cd.analyze_corpus(cases, view="external", budgets=EXTERNAL_CAP_50)

    # Relabel everything into a single class. Strata collapse; counts do not.
    relabelled = [
        type(c)(**{**c.__dict__, "labels": frozenset({c.input.action, "one_class"})})
        for c in cases
    ]
    after = cd.analyze_corpus(relabelled, view="external", budgets=EXTERNAL_CAP_50)

    assert {s.label_class for s in after.strata} == {"one_class"}
    assert after.total_cases == baseline.total_cases == 732
    assert after.group_counts == baseline.group_counts


def test_unlabelled_cases_are_still_a_stratum_not_a_gap() -> None:
    cases = ecommerce_corpus()[:10]
    bare = [type(c)(**{**c.__dict__, "labels": frozenset({c.input.action})}) for c in cases]
    report = cd.analyze_corpus(bare, view="external", budgets=EXTERNAL_CAP_50)
    assert {s.label_class for s in report.strata} == {cd.UNLABELED}
    assert sum(s.count for s in report.strata) == 10


# --------------------------------------------------------------------------
# Named regression traces are always retained
# --------------------------------------------------------------------------


def test_named_regression_traces_are_retained_and_reported() -> None:
    cases = [*ecommerce_corpus(), regression_trace_case()]
    report = cd.analyze_corpus(cases, view="external", budgets=EXTERNAL_CAP_50)

    assert report.total_cases == 733
    assert report.regression_cases == ("case_9001_SubmitCheckout",)
    assert "Named regression traces (always retained): 1" in cd.render_report(report)

    # Still retained when the cap is raised to a passing value.
    passing = cd.analyze_corpus(cases, view="external", budgets={"max_external_cases_per_action": 500})
    assert passing.passed is True
    assert passing.regression_cases == ("case_9001_SubmitCheckout",)


# --------------------------------------------------------------------------
# The export path gates the full corpus, before any selection
# --------------------------------------------------------------------------


def _external_package(tmp_path: Path, count: int) -> Path:
    states = {str(i): {"n": i} for i in range(count + 1)}
    edges = [Edge(str(i), str(i + 1), "Submit") for i in range(count)]
    package_dir = tmp_path / "external_cases"
    render_python_package(
        module="Program",
        states=states,
        edges=edges,
        package_dir=package_dir,
        view="external",
        action_metadata={"Submit": ActionMetadata("Submit", "external", "e2e_direct", ("testgraph",))},
    )
    return package_dir


def _external_bindings(tmp_path: Path) -> Path:
    """MF-015: export requires a validated external contract for the actions."""
    adapters = tmp_path / "export_adapters.py"
    adapters.write_text(
        "class SubmitHttpAdapter:\n"
        "    def run(self, case, work_dir=None):\n"
        "        return {'ok': True}\n",
        encoding="utf-8",
    )
    path = tmp_path / "testgraph_bindings.yml"
    path.write_text(
        "external:\n"
        "  production_package: program_under_test\n"
        "  port_bindings:\n"
        "    RequestPort: real\n"
        "actions:\n"
        "  Submit:\n"
        "    view: external\n"
        "    channel: http\n"
        "    adapter: export_adapters:SubmitHttpAdapter\n",
        encoding="utf-8",
    )
    return path


def test_export_limit_cannot_bring_an_over_cap_corpus_under_cap(tmp_path: Path) -> None:
    """--limit is a focused-run selection, never a way to satisfy a budget."""
    package_dir = _external_package(tmp_path, 60)
    manifest = tmp_path / "spec_manifest.yaml"
    manifest.write_text("module: Program\nbudgets:\n  max_external_cases_per_action: 50\n", encoding="utf-8")

    result = subprocess.run(
        [sys.executable, str(SKILL_ROOT / "scripts" / "export_testgraph_cases.py"), str(package_dir),
         "--out", str(tmp_path / "traces"), "--limit", "5", "--manifest", str(manifest),
         "--bindings", str(_external_bindings(tmp_path))],
        capture_output=True, text=True, cwd=ROOT,
    )
    assert result.returncode == 2, result.stdout + result.stderr
    assert "corpus gate FAIL" in result.stderr
    assert "60 cases, cap 50" in result.stderr
    assert not (tmp_path / "traces").exists(), "export proceeded despite a failing cap gate"


def test_export_proceeds_when_the_corpus_is_within_cap(tmp_path: Path) -> None:
    package_dir = _external_package(tmp_path, 10)
    manifest = tmp_path / "spec_manifest.yaml"
    manifest.write_text("module: Program\nbudgets:\n  max_external_cases_per_action: 50\n", encoding="utf-8")

    result = subprocess.run(
        [sys.executable, str(SKILL_ROOT / "scripts" / "export_testgraph_cases.py"), str(package_dir),
         "--out", str(tmp_path / "traces"), "--manifest", str(manifest),
         "--bindings", str(_external_bindings(tmp_path))],
        capture_output=True, text=True, cwd=ROOT,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "corpus gate PASS" in result.stdout
    assert len(list((tmp_path / "traces").glob("*.json"))) == 11  # 10 traces + manifest


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------


def _cli(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SKILL_ROOT / "scripts" / "tla_spec_dev.py"), "--spec-root", "specs",
         "analyze", "corpus", *args],
        capture_output=True, text=True, cwd=ROOT,
    )


def test_cli_passes_on_the_committed_example_corpus() -> None:
    # BS-08: the committed example corpus moved here from
    # examples/distributed_history/specs/generated/, which 76ef2758 ("removed
    # generated", 2026-09-14) deleted and gitignored. Restored byte-for-byte from
    # 76ef2758^ as a TEST fixture, outside any directory a generator writes.
    result = _cli("tests/fixtures/distributed_history_generated/testgraph/ecommerce_external_cases")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "corpus gate PASS" in result.stdout
    assert "cap max_external_cases_per_action = 50 per action" in result.stdout
    assert "No case was dropped, filtered, sampled, or truncated." in result.stdout


def test_cli_exits_nonzero_over_cap(tmp_path: Path) -> None:
    package_dir = _external_package(tmp_path, 60)
    manifest = tmp_path / "spec_manifest.yaml"
    manifest.write_text("module: Program\nbudgets:\n  max_external_cases_per_action: 50\n", encoding="utf-8")
    result = _cli(str(package_dir), "--view", "external", "--manifest", str(manifest))
    assert result.returncode == 1, result.stdout + result.stderr
    assert "corpus gate FAIL" in result.stdout
    assert "ACCEPT PATH" in result.stdout
    assert "REDESIGN QUESTION" in result.stdout
    assert "references/complexity_intuition.md" in result.stdout
    for banned in PRESCRIPTIVE_MOVE_WORDING:
        assert banned not in result.stdout, f"prescriptive-move wording returned: {banned!r}"


def test_cli_help_states_that_nothing_is_dropped_and_asks_not_prescribes() -> None:
    result = subprocess.run(
        [sys.executable, str(SKILL_ROOT / "scripts" / "tla_spec_dev.py"), "analyze", "corpus", "--help"],
        capture_output=True, text=True, cwd=ROOT,
    )
    assert result.returncode == 0
    # argparse re-wraps the description, so compare against unwrapped text.
    unwrapped = " ".join(result.stdout.split())
    assert "NOTHING IS EVER DROPPED" in unwrapped
    assert "REDESIGN QUESTION" in unwrapped
    assert "complexity_intuition.md" in unwrapped
    for banned in PRESCRIPTIVE_MOVE_WORDING:
        assert banned not in unwrapped, f"prescriptive-move wording returned: {banned!r}"
