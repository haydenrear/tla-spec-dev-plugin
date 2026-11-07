import json
from dataclasses import replace
from pathlib import Path
import sys
import importlib

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.generate_cases_from_tlc_dump import (
    ZeroCaseActionError,
    _expected_zero,
    ActionMetadata,
    Edge,
    labels_for_case,
    load_action_metadata,
    parse_tlc_function,
    parse_state_label,
    parse_tlc_value,
    prepare_cases,
    py_repr,
    render_python_package,
    report_action_coverage,
    report_param_recovery,
)
from scripts.infer_action_params import UNCHECKED, build_recipes


def test_parse_set_keeps_sequence_members_intact() -> None:
    assert parse_tlc_value("{<<1,2>>, <<3,4>>}") == frozenset({(1, 2), (3, 4)})


def test_parse_set_parses_record_members_structurally() -> None:
    assert parse_tlc_value("{[a |-> 1, b |-> 2], [a |-> 3, b |-> 4]}") == frozenset(
        {
            frozenset({("a", 1), ("b", 2)}),
            frozenset({("a", 3), ("b", 4)}),
        }
    )


def test_parse_state_label_keeps_multiline_record_values() -> None:
    assert parse_state_label(
        '/\\ lastExternalAction = [ name |-> "Submit",\\n'
        '  params |-> [account |-> "acct-1", sku |-> "sku-1"] ]\\n'
        '/\\ status = "ok"'
    ) == {
        "lastExternalAction": {
            "name": "Submit",
            "params": {"account": "acct-1", "sku": "sku-1"},
        },
        "status": "ok",
    }


def test_parse_function_ignores_nested_function_separators() -> None:
    assert parse_tlc_function('("outer" :> ("left" :> 1 @@ "right" :> 2) @@ "tail" :> <<3,4>>)') == {
        "outer": {"left": 1, "right": 2},
        "tail": (3, 4),
    }


def test_parse_set_can_contain_function_members() -> None:
    assert parse_tlc_value('{("a" :> 1 @@ "b" :> <<2,3>>)}') == frozenset(
        {frozenset({("a", 1), ("b", (2, 3))})}
    )


def test_py_repr_handles_nested_set_members_deterministically() -> None:
    assert py_repr(frozenset({(3, 4), (1, 2)})) == "frozenset([(1, 2), (3, 4)])"


def test_labels_for_case_adds_labeler_output_after_action() -> None:
    labels = labels_for_case(
        before={"items": frozenset()},
        action="Create",
        after={"items": frozenset({"a"})},
        changes={"items": {"before": frozenset(), "after": frozenset({"a"})}},
        labelers=[lambda before, action, after, changed: ["non_empty", action]],
    )

    assert labels == ["Create", "non_empty"]


def import_generated_cases(tmp_path: Path, package: str):
    for name in list(sys.modules):
        if name == package or name.startswith(f"{package}."):
            del sys.modules[name]
    sys.path.insert(0, str(tmp_path))
    return importlib.import_module(f"{package}.cases")


def tiny_state_graph() -> tuple[dict[str, dict[str, object]], list[Edge]]:
    states = {
        "0": {"status": "none"},
        "1": {"status": "pending"},
        "2": {"status": "visible"},
        "3": {"status": "hidden"},
    }
    edges = [
        Edge(source="0", target="1", action="AcceptRequest"),
        Edge(source="1", target="2", action="Submit"),
        Edge(source="2", target="3", action="HiddenWorkerProgress"),
    ]
    return states, edges


def test_internal_generation_emits_only_spec_unit_internal_actions(tmp_path: Path) -> None:
    states, edges = tiny_state_graph()
    render_python_package(
        module="Program",
        states=states,
        edges=edges,
        package_dir=tmp_path / "internal_cases",
        view="internal",
        action_metadata={
            "AcceptRequest": ActionMetadata("AcceptRequest", "internal", "unit_direct", ("spec_unit",)),
            "Submit": ActionMetadata("Submit", "external", "e2e_direct", ("testgraph",)),
            "HiddenWorkerProgress": ActionMetadata("HiddenWorkerProgress", "internal", "hidden", ()),
        },
    )

    cases_module = import_generated_cases(tmp_path, "internal_cases")

    assert [case.input.action for case in cases_module.CASES] == ["AcceptRequest"]
    case = cases_module.CASES[0]
    assert case.schema_version == "tla-testgraph.trace.v1"
    assert case.view == "internal"
    assert case.layer == "internal"
    assert case.controllability == "unit_direct"
    assert case.generates == frozenset({"spec_unit"})


def test_external_generation_emits_only_testgraph_external_actions(tmp_path: Path) -> None:
    states, edges = tiny_state_graph()
    render_python_package(
        module="Program",
        states=states,
        edges=edges,
        package_dir=tmp_path / "external_cases",
        view="external",
        action_metadata={
            "AcceptRequest": ActionMetadata("AcceptRequest", "internal", "unit_direct", ("spec_unit",)),
            "Submit": ActionMetadata("Submit", "external", "e2e_direct", ("testgraph",), ("smoke",)),
            "HiddenWorkerProgress": ActionMetadata("HiddenWorkerProgress", "internal", "hidden", ()),
        },
    )

    cases_module = import_generated_cases(tmp_path, "external_cases")

    assert [case.input.action for case in cases_module.CASES] == ["Submit"]
    case = cases_module.CASES[0]
    assert case.view == "external"
    assert case.layer == "external"
    assert case.controllability == "e2e_direct"
    assert case.generates == frozenset({"testgraph"})
    assert case.tags == frozenset({"smoke"})


def test_generation_derives_action_params_from_last_action_marker(tmp_path: Path) -> None:
    states = {
        "0": {"lastExternalAction": {"name": "Init", "params": ()}, "status": "none"},
        "1": {
            "lastExternalAction": {
                "name": "Submit",
                "params": {"account": "acct-1", "sku": "sku-1"},
            },
            "status": "visible",
        },
    }
    render_python_package(
        module="Program",
        states=states,
        edges=[Edge(source="0", target="1", action="Submit")],
        package_dir=tmp_path / "external_cases",
        view="external",
        action_metadata={"Submit": ActionMetadata("Submit", "external", "e2e_direct", ("testgraph",))},
    )

    cases_module = import_generated_cases(tmp_path, "external_cases")

    assert cases_module.CASES[0].input.params == {"account": "acct-1", "sku": "sku-1"}


def test_generation_uses_projectors_and_projected_dedupe(tmp_path: Path) -> None:
    states = {
        "0": {"lastExternalAction": {"name": "Init", "params": ()}, "raw": 1, "status": "empty"},
        "1": {"lastExternalAction": {"name": "Submit", "params": {"id": "r1"}}, "raw": 2, "status": "done"},
        "2": {"lastExternalAction": {"name": "Init", "params": ()}, "raw": 3, "status": "empty"},
        "3": {"lastExternalAction": {"name": "Submit", "params": {"id": "r1"}}, "raw": 4, "status": "done"},
    }

    def state_projector(state):
        return {"status": state["status"]}

    def output_projector(**kwargs):
        return {"accepted": kwargs["action"] == "Submit"}

    render_python_package(
        module="Program",
        states=states,
        edges=[Edge(source="0", target="1", action="Submit"), Edge(source="2", target="3", action="Submit")],
        package_dir=tmp_path / "external_cases",
        view="external",
        action_metadata={"Submit": ActionMetadata("Submit", "external", "e2e_direct", ("testgraph",))},
        state_projector=state_projector,
        output_projector=output_projector,
        dedupe="projected",
    )

    cases_module = import_generated_cases(tmp_path, "external_cases")

    assert len(cases_module.CASES) == 1
    assert cases_module.CASES[0].before == {"status": "empty"}
    assert cases_module.CASES[0].after == {"status": "done"}
    assert cases_module.CASES[0].output == {"accepted": True}


def test_legacy_generation_defaults_to_internal_view_without_filtering(tmp_path: Path) -> None:
    states, edges = tiny_state_graph()
    render_python_package(
        module="Program",
        states=states,
        edges=edges,
        package_dir=tmp_path / "legacy_cases",
    )

    cases_module = import_generated_cases(tmp_path, "legacy_cases")

    assert [case.input.action for case in cases_module.CASES] == [
        "AcceptRequest",
        "Submit",
        "HiddenWorkerProgress",
    ]
    assert {case.view for case in cases_module.CASES} == {"internal"}


def test_load_action_metadata_from_actions_yaml(tmp_path: Path) -> None:
    path = tmp_path / "actions.yml"
    path.write_text(
        """actions:
  Submit:
    layer: external
    controllability: e2e_direct
    generates:
      - testgraph
    tags:
      - smoke
""",
        encoding="utf-8",
    )

    metadata = load_action_metadata(path)

    assert metadata["Submit"] == ActionMetadata(
        name="Submit",
        layer="external",
        controllability="e2e_direct",
        generates=("testgraph",),
        tags=("smoke",),
    )


EXTERNAL_METADATA = {
    "AcceptRequest": ActionMetadata("AcceptRequest", "internal", "unit_direct", ("spec_unit",)),
    "Submit": ActionMetadata("Submit", "external", "e2e_direct", ("testgraph",)),
    "Retry": ActionMetadata("Retry", "external", "e2e_direct", ("testgraph",)),
    "Cancel": ActionMetadata("Cancel", "external", "e2e_direct", ("testgraph",)),
    "HiddenWorkerProgress": ActionMetadata("HiddenWorkerProgress", "internal", "hidden", ()),
}


def prepare_external_cases(tmp_path: Path, package: str):
    states, edges = tiny_state_graph()
    return render_python_package(
        module="Aspect_Submit",
        states=states,
        edges=edges,
        package_dir=tmp_path / package,
        view="external",
        action_metadata=EXTERNAL_METADATA,
    )


def write_case_module_manifest(tmp_path: Path, scope: str) -> Path:
    path = tmp_path / "spec_manifest.yaml"
    path.write_text(
        "module: Program\n"
        "case_modules:\n"
        "  Aspect_Submit:\n"
        "    extends: External\n"
        "    form: slice\n"
        f"    actions: [{scope}]\n",
        encoding="utf-8",
    )
    return path


def test_undeclared_zero_case_view_actions_now_FAIL_rather_than_warn(tmp_path: Path, capsys) -> None:
    """R4-DF-04's scope rule is unchanged; the DISPOSITION of a zero is not.

    This used to assert two warning LINES. Warnings were printed, the coverage
    file simply had no entry for the action, and the corpus reported a healthy
    total -- so a corpus silently covering 10 of 11 declared actions passed as
    healthy while the goal it was built to decide named the missing one. The
    zero is now an error, and the record is still written first so the evidence
    of why is on disk.
    """
    prepared = prepare_external_cases(tmp_path, "undeclared_cases")

    with pytest.raises(ZeroCaseActionError) as caught:
        report_action_coverage(
            prepared,
            module="Aspect_Submit",
            view="external",
            action_metadata=EXTERNAL_METADATA,
            package_dir=tmp_path / "undeclared_cases",
            manifest_path=tmp_path / "missing_manifest.yaml",
        )

    assert caught.value.actions == ["Cancel", "Retry"]
    errors = [line for line in capsys.readouterr().err.splitlines() if "ZERO cases" in line]
    assert len(errors) == 2
    assert (tmp_path / "undeclared_cases" / "case_coverage.json").exists()


def test_a_declared_expected_zero_is_reported_and_does_not_fail(tmp_path: Path, capsys) -> None:
    """Case B of #300: a guard unsatisfiable in THIS epic is a legitimate state.

    It was previously indistinguishable from Case A -- a broken alias wrapper --
    because both produced the same silent zero. Declaring it makes the hole read
    as stated, and is what allows the undeclared form above to fail.
    """
    prepared = prepare_external_cases(tmp_path, "expected_zero_cases")
    metadata = dict(EXTERNAL_METADATA)
    for name in ("Cancel", "Retry"):
        metadata[name] = replace(metadata[name], expected_zero=f"guard unsatisfiable until MH-03 ({name})")

    record = report_action_coverage(
        prepared,
        module="Aspect_Submit",
        view="external",
        action_metadata=metadata,
        package_dir=tmp_path / "expected_zero_cases",
        manifest_path=tmp_path / "missing_manifest.yaml",
    )

    assert record["undeclared_zero_actions"] == []
    assert set(record["declared_zero_actions"]) == {"Cancel", "Retry"}
    out = capsys.readouterr().out
    assert "declared zero: external action 'Cancel'" in out
    assert "guard unsatisfiable until MH-03 (Cancel)" in out, "the REASON must reach the operator"


def test_expected_zero_refuses_a_bare_boolean() -> None:
    """A declaration with no reason declares nothing a reader can act on."""
    with pytest.raises(ValueError, match="must be a REASON string"):
        _expected_zero("Retry", True)


def test_declared_case_module_scopes_the_zero_case_warning(tmp_path: Path, capsys) -> None:
    """CM-F2: an action outside the aspect is a design decision, not a hole."""
    prepared = prepare_external_cases(tmp_path, "declared_cases")

    report_action_coverage(
        prepared,
        module="Aspect_Submit",
        view="external",
        action_metadata=EXTERNAL_METADATA,
        package_dir=tmp_path / "declared_cases",
        manifest_path=write_case_module_manifest(tmp_path, "Submit"),
    )

    captured = capsys.readouterr()
    assert "ZERO cases" not in captured.err
    assert "declared slice of External with 1 action(s) in scope" in captured.out
    assert "are NOT reported as coverage holes" in captured.out


def test_an_in_scope_action_with_no_cases_now_fails(tmp_path: Path, capsys) -> None:
    prepared = prepare_external_cases(tmp_path, "in_scope_cases")

    with pytest.raises(ZeroCaseActionError) as caught:
        report_action_coverage(
            prepared,
            module="Aspect_Submit",
            view="external",
            action_metadata=EXTERNAL_METADATA,
            package_dir=tmp_path / "in_scope_cases",
            manifest_path=write_case_module_manifest(tmp_path, "Submit, Retry"),
        )

    assert caught.value.actions == ["Retry"]
    errors = [line for line in capsys.readouterr().err.splitlines() if "ZERO cases" in line]
    assert len(errors) == 1 and "'Retry'" in errors[0]


def test_generating_outside_the_declared_scope_is_reported_as_drift(tmp_path: Path, capsys) -> None:
    prepared = prepare_external_cases(tmp_path, "drift_cases")

    # `Retry` is in scope and generates nothing, so the run now also FAILS --
    # the drift report this test is about is printed before that happens, and
    # the assertions below read it out of the captured stream.
    with pytest.raises(ZeroCaseActionError):
        report_action_coverage(
            prepared,
            module="Aspect_Submit",
            view="external",
            action_metadata=EXTERNAL_METADATA,
            package_dir=tmp_path / "drift_cases",
            manifest_path=write_case_module_manifest(tmp_path, "Retry"),
        )

    err = capsys.readouterr().err
    assert "generated 1 case(s) for 'Submit', which is not in its declared `actions:` scope" in err


def test_coverage_record_is_written_beside_every_generated_package(tmp_path: Path) -> None:
    prepared = prepare_external_cases(tmp_path, "recorded_cases")

    record = report_action_coverage(
        prepared,
        module="Aspect_Submit",
        view="external",
        action_metadata=EXTERNAL_METADATA,
        package_dir=tmp_path / "recorded_cases",
        manifest_path=write_case_module_manifest(tmp_path, "Submit"),
    )

    written = json.loads((tmp_path / "recorded_cases" / "case_coverage.json").read_text())
    assert written == record
    assert written["actions"] == {"Submit": 1}
    assert written["cases"] == 1
    assert written["declared_view_actions"] == ["Cancel", "Retry", "Submit"]
    assert written["case_module"]["form"] == "slice"


if __name__ == "__main__":
    test_parse_set_keeps_sequence_members_intact()
    test_parse_set_parses_record_members_structurally()
    test_parse_state_label_keeps_multiline_record_values()
    test_parse_function_ignores_nested_function_separators()
    test_parse_set_can_contain_function_members()
    test_py_repr_handles_nested_set_members_deterministically()
    test_labels_for_case_adds_labeler_output_after_action()


# ---------------------------------------------------------------------------
# RP-02: set-membership models carry their arguments end to end
# ---------------------------------------------------------------------------
#
# Before this ticket a `\E i \in Items` model recovered nothing: every case
# went out with `params={'i': UNCHECKED}` and the ex4 adapter re-derived the
# argument by diffing `case.before` against `case.after` -- from the oracle
# (EV-01-DF-01). These tests hold the whole path: model source -> recipe ->
# emitted case -> label -> written audit.

SET_MEMBERSHIP_MODULE = """
VARIABLES inbox, accepted

Accept(i) ==
  /\\ i \\in inbox
  /\\ inbox' = inbox \\ {i}
  /\\ accepted' = accepted \\cup {i}
"""


def set_membership_graph():
    states = {
        "0": {"inbox": frozenset({"i1", "i2"}), "accepted": frozenset()},
        "1": {"inbox": frozenset({"i2"}), "accepted": frozenset({"i1"})},
        "2": {"inbox": frozenset({"i1"}), "accepted": frozenset({"i2"})},
    }
    edges = [
        Edge(source="0", target="1", action="Accept"),
        Edge(source="0", target="2", action="Accept"),
    ]
    return states, edges


def test_generated_cases_carry_the_recovered_set_member(tmp_path: Path) -> None:
    states, edges = set_membership_graph()
    render_python_package(
        module="Pipeline",
        states=states,
        edges=edges,
        package_dir=tmp_path / "member_cases",
        view="internal",
        action_metadata={"Accept": ActionMetadata("Accept", "internal", "unit_direct", ("spec_unit",))},
        param_recipes=build_recipes(SET_MEMBERSHIP_MODULE),
    )

    cases_module = import_generated_cases(tmp_path, "member_cases")
    params = [case.input.params for case in cases_module.CASES]

    assert params == [{"i": "i1"}, {"i": "i2"}]
    # NEGATIVE CONTROL: the two edges leave the SAME before-state, so a
    # recovery that ignored the transition would give both cases one argument.
    assert params[0] != params[1]
    assert all("params:recovered" in case.labels for case in cases_module.CASES)
    assert all("params:unchecked" not in case.labels for case in cases_module.CASES)


def test_an_ambiguous_edge_is_marked_unchecked_and_still_emitted(tmp_path: Path) -> None:
    """Evidence integrity: an unrecovered argument is labelled, never dropped."""
    states = {
        "0": {"inbox": frozenset({"i1", "i2"}), "accepted": frozenset()},
        "1": {"inbox": frozenset(), "accepted": frozenset({"i1", "i2"})},
    }
    prepared = prepare_cases(
        states=states,
        edges=[Edge(source="0", target="1", action="Accept")],
        view="internal",
        action_metadata={},
        labelers=[],
        state_projector=None,
        output_projector=None,
        dedupe="none",
        param_recipes=build_recipes(SET_MEMBERSHIP_MODULE),
    )

    assert len(prepared) == 1
    assert prepared[0].params == {"i": UNCHECKED}
    assert "params:unchecked:i" in prepared[0].labels


def test_the_written_audit_reports_what_the_run_measured(tmp_path: Path) -> None:
    """EV-02-DF-03: the audit beside a corpus must describe THAT corpus."""
    states, edges = set_membership_graph()
    recipes = build_recipes(SET_MEMBERSHIP_MODULE)
    prepared = prepare_cases(
        states=states,
        edges=edges,
        view="internal",
        action_metadata={},
        labelers=[],
        state_projector=None,
        output_projector=None,
        dedupe="none",
        param_recipes=recipes,
    )
    package_dir = tmp_path / "member_cases"
    package_dir.mkdir()

    measurement = report_param_recovery(prepared, recipes, package_dir)
    audit = (package_dir / "param_recovery_audit.md").read_text()

    assert measurement.total_cases == 2
    assert measurement.for_param("Accept", "i").recovered == 2
    assert "Measured over the corpus this run generated: 2 cases." in audit
    assert "recovered in 2 of 2 cases" in audit
    assert "Every parameter of every action is recoverable from its state pair." not in audit


def test_a_run_that_recovers_nothing_is_audited_as_unrecoverable(tmp_path: Path) -> None:
    """The exact shape of the contradiction: a corpus carrying nothing.

    `param_recovery_audit.md` used to claim universal recoverability here,
    because it read the module and never the cases.
    """
    states = {
        "0": {"inbox": frozenset({"i1", "i2"}), "accepted": frozenset()},
        "1": {"inbox": frozenset(), "accepted": frozenset({"i1", "i2"})},
    }
    recipes = build_recipes(SET_MEMBERSHIP_MODULE)
    prepared = prepare_cases(
        states=states,
        edges=[Edge(source="0", target="1", action="Accept")],
        view="internal",
        action_metadata={},
        labelers=[],
        state_projector=None,
        output_projector=None,
        dedupe="none",
        param_recipes=recipes,
    )
    package_dir = tmp_path / "empty_args"
    package_dir.mkdir()

    measurement = report_param_recovery(prepared, recipes, package_dir)
    audit = (package_dir / "param_recovery_audit.md").read_text()

    assert [item.param for item in measurement.unrecovered] == ["i"]
    assert "UNRECOVERABLE ON THIS CORPUS" in audit
    assert "`Accept(i)` -- 0 of 1 cases carry an argument" in audit
    assert "Every parameter of every action is recoverable from its state pair." not in audit


# --------------------------------------------------------------------------
# HP-03: the negative corpus
# --------------------------------------------------------------------------

from scripts.generate_cases_from_tlc_dump import (  # noqa: E402
    GuardEvaluator,
    NEGATIVE_LABEL,
    Unevaluable,
    coerce_cfg_constant,
    extract_action_signatures,
    negatable_actions,
    negative_cases_for_corpus,
    parse_tla_definitions,
    parse_tla_expression,
    written_variables,
)
from scripts.analyze_complexity import parse_cfg_constants  # noqa: E402
from scripts.infer_action_params import parse_variables  # noqa: E402


TINY_MODULE = """---- MODULE Tiny ----
EXTENDS Naturals

CONSTANTS Items, Slots

VARIABLES held, closed, outcome

vars == << held, closed, outcome >>

Init ==
  /\\ held = {}
  /\\ closed = FALSE
  /\\ outcome = "init"

Take(i) ==
  /\\ closed = FALSE
  /\\ i \\notin held
  /\\ held' = held \\cup {i}
  /\\ outcome' = "taken"
  /\\ UNCHANGED << closed >>

Drop(i) ==
  /\\ i \\in held
  /\\ held' = held \\ {i}
  /\\ outcome' = "dropped"
  /\\ UNCHANGED << closed >>

RefuseTake(i) ==
  /\\ closed = TRUE
  /\\ outcome' = "refused"
  /\\ UNCHANGED << held, closed >>

Next ==
  \\/ \\E i \\in Items : Take(i)
  \\/ \\E i \\in Items : Drop(i)
  \\/ \\E i \\in Items : RefuseTake(i)

====
"""

TINY_CFG = """SPECIFICATION Spec
CONSTANTS
  Items = {a, b}
  Slots = {s1}
"""


def tiny_evaluator() -> GuardEvaluator:
    definitions = parse_tla_definitions(TINY_MODULE)
    constants = {
        name: coerce_cfg_constant(value) for name, value in parse_cfg_constants(TINY_CFG).items()
    }
    return GuardEvaluator(definitions, constants, parse_variables(TINY_MODULE))


def test_guard_evaluator_answers_false_only_when_the_model_says_so() -> None:
    evaluator = tiny_evaluator()
    body = evaluator.definitions["Take"].body
    # `a` is already held, so `i \notin held` is definitely FALSE.
    truth, witness = evaluator.evaluate(body, {"held": frozenset({"a"}), "closed": False, "i": "a"})
    assert truth is False
    assert witness == "i \\notin held"


def test_guard_evaluator_is_unknown_rather_than_true_on_a_primed_conjunct() -> None:
    evaluator = tiny_evaluator()
    body = evaluator.definitions["Take"].body
    # Every guard holds, but `held'` cannot be evaluated -- so the answer is
    # UNKNOWN, never TRUE. Only FALSE is ever acted on.
    truth, _ = evaluator.evaluate(body, {"held": frozenset(), "closed": False, "i": "a"})
    assert truth is None


def test_a_bulleted_disjunction_is_not_torn_into_top_level_conjuncts() -> None:
    """The one shape that could produce a false rejection.

    A textual split on ``/\\`` would promote ``x = 1`` to a top-level conjunct
    of a disjunction and report the whole body FALSE when it is TRUE.
    """
    evaluator = tiny_evaluator()
    body = "  /\\ \\/ /\\ x = 1\n        /\\ y = 9\n     \\/ y = 2\n"
    truth, _ = evaluator.evaluate(body, {"x": 5, "y": 2})
    assert truth is True
    truth, _ = evaluator.evaluate(body, {"x": 5, "y": 3})
    assert truth is False


def test_quantifiers_and_set_operations_evaluate() -> None:
    evaluator = tiny_evaluator()
    node = parse_tla_expression("\\A i \\in held : i # \"a\"")
    assert evaluator.eval_node(node, {"held": frozenset({"b"})}, 0) is True
    assert evaluator.eval_node(node, {"held": frozenset({"a", "b"})}, 0) is False


def test_unsupported_construct_raises_rather_than_defaulting() -> None:
    with pytest.raises(Unevaluable):
        parse_tla_expression("LET z == 1 IN z = 1")


def test_action_signatures_carry_their_quantifier_domains() -> None:
    evaluator = tiny_evaluator()
    signatures, rejected = extract_action_signatures(evaluator.definitions, evaluator)
    assert set(signatures) == {"Take", "Drop", "RefuseTake"}
    assert signatures["Take"].params == ("i",)
    assert signatures["Take"].domains == (("a", "b"),)
    assert rejected == {}


def test_a_modeled_refusal_is_never_negated() -> None:
    """The complement of a refusal is an acceptance, so negating one would be
    a false rejection -- the single error this mode may not make."""
    evaluator = tiny_evaluator()
    signatures, _ = extract_action_signatures(evaluator.definitions, evaluator)
    chosen, excluded = negatable_actions(signatures, evaluator)
    assert chosen == ["Drop", "Take"]
    assert "RefuseTake" in excluded


def test_written_variables_follows_the_operators_an_action_calls() -> None:
    evaluator = tiny_evaluator()
    signatures, _ = extract_action_signatures(evaluator.definitions, evaluator)
    assert written_variables(signatures["Take"], evaluator.variables, evaluator.definitions) == frozenset(
        {"held", "outcome"}
    )


def tiny_states() -> dict[str, dict]:
    return {
        "1": {"held": frozenset(), "closed": False, "outcome": "init"},
        "2": {"held": frozenset({"a"}), "closed": False, "outcome": "taken"},
        "3": {"held": frozenset({"a"}), "closed": True, "outcome": "taken"},
    }


def negative_corpus(**overrides):
    kwargs = dict(
        states=tiny_states(),
        edges=[Edge(source="1", target="2", action="Take")],
        tla_source=TINY_MODULE,
        cfg_text=TINY_CFG,
        view="internal",
        action_metadata={},
        state_projector=None,
        dedupe="none",
        only_actions=(),
        param_recipes=build_recipes(TINY_MODULE),
        start_index=1,
    )
    kwargs.update(overrides)
    return negative_cases_for_corpus(**kwargs)


def test_negative_cases_are_emitted_for_every_disabled_argument() -> None:
    cases, report = negative_corpus()
    emitted = {(case.edge.source, case.edge.action, case.params["i"]) for case in cases}
    # State 1 holds nothing: every Drop is disabled, no Take is.
    assert ("1", "Drop", "a") in emitted
    assert ("1", "Drop", "b") in emitted
    assert ("1", "Take", "a") not in emitted
    # State 2 holds `a`: Take(a) is disabled, Drop(b) is.
    assert ("2", "Take", "a") in emitted
    assert ("2", "Drop", "b") in emitted
    # State 3 is closed: every Take is disabled.
    assert ("3", "Take", "a") in emitted
    assert ("3", "Take", "b") in emitted
    assert report.negated == ("Drop", "Take")


def test_a_negative_case_asserts_refusal_and_inertness() -> None:
    cases, report = negative_corpus()
    case = next(case for case in cases if case.edge.action == "Take" and case.edge.source == "3")
    assert case.before == case.after
    assert case.edge.source == case.edge.target
    assert NEGATIVE_LABEL in case.labels
    assert "expect:rejected" in case.labels
    assert "closed = FALSE" in case.output_expression
    # Derived from the model's own refusal action, not named by hand.
    assert report.outcome_fields == ("outcome",)


def test_no_negative_case_names_an_argument_the_model_enables() -> None:
    """Zero false rejections, checked against the guard rather than the dump."""
    cases, _ = negative_corpus()
    evaluator = tiny_evaluator()
    signatures, _ = extract_action_signatures(evaluator.definitions, evaluator)
    states = tiny_states()
    for case in cases:
        body = signatures[case.edge.action].body
        truth, _ = evaluator.evaluate(body, {**states[case.edge.source], **case.params})
        assert truth is False, case.name


def test_negative_generation_is_deterministic() -> None:
    first, _ = negative_corpus()
    second, _ = negative_corpus()
    assert [case.name for case in first] == [case.name for case in second]
    assert [case.output_expression for case in first] == [case.output_expression for case in second]


def test_guard_reads_dedupe_collapses_only_identical_tests() -> None:
    exact, exact_report = negative_corpus(dedupe="none")
    collapsed, collapsed_report = negative_corpus(dedupe="guard-reads")
    assert len(collapsed) < len(exact)
    assert collapsed_report.deduped_from == len(exact) - len(collapsed)
    # Every reason present in the exact corpus survives the collapse: a dedupe
    # may drop a duplicate, never a distinct refusal.
    assert set(exact_report.per_reason) == set(collapsed_report.per_reason)


def test_negative_action_override_selects_exactly_what_was_named() -> None:
    _, report = negative_corpus(only_actions=("Drop",))
    assert report.negated == ("Drop",)


def test_only_mode_writes_a_package_of_rejections(tmp_path: Path) -> None:
    reports: list = []
    cases = render_python_package(
        module="Tiny",
        states=tiny_states(),
        edges=[Edge(source="1", target="2", action="Take")],
        package_dir=tmp_path / "neg",
        negative="only",
        negative_dedupe="none",
        tla_source=TINY_MODULE,
        cfg_text=TINY_CFG,
        negative_report_out=reports,
    )
    assert cases and all(NEGATIVE_LABEL in case.labels for case in cases)
    assert reports and reports[0].emitted == len(cases)
    text = (tmp_path / "neg" / "cases.py").read_text()
    assert "StateGraphRejection" in text
    assert "StateGraphRejection" in (tmp_path / "neg" / "types.py").read_text()
    docs = (tmp_path / "neg" / "docs.md").read_text()
    assert "State projection: `none`" in docs
    assert "Negative corpus: `only`" in docs


def test_with_positive_keeps_every_enabled_edge_and_appends_rejections(tmp_path: Path) -> None:
    reports: list = []
    cases = render_python_package(
        module="Tiny",
        states=tiny_states(),
        edges=[Edge(source="1", target="2", action="Take")],
        package_dir=tmp_path / "both",
        negative="with-positive",
        tla_source=TINY_MODULE,
        cfg_text=TINY_CFG,
        negative_report_out=reports,
    )
    positive = [case for case in cases if NEGATIVE_LABEL not in case.labels]
    assert len(positive) == 1
    assert len(cases) == 1 + reports[0].emitted


# -- CA-06-DF-01: the next-state relation is READ, never assumed ---------------
#
# R1 says an instrument ships with a demonstrated failing input on a REAL
# SUBJECT, not a fixture. The subject below is `examples/distributed_history` --
# this repository's own worked example, checked in, named by README.md as the
# active one -- and it is the input that was failing: it spells its next-state
# relations `InternalNext` and `ExternalNext`, so a generator that looks up the
# literal name `Next` found nothing, emitted ZERO negative and ZERO port cases,
# and printed `corpus gate PASS` over the silence.
#
# The two models these modes have ever been measured on are asserted too, and
# they are the reason the defect survived three epics: both are named `Next`.


def test_the_next_state_relation_is_resolved_from_each_models_own_cfg() -> None:
    from scripts.generate_cases_from_tlc_dump import (
        parse_tla_definitions,
        resolve_next_relation,
    )

    subjects = {
        # THE REAL SUBJECT, and the demonstrated failing input.
        "examples/distributed_history/specs/program_model/Internal": "InternalNext",
        "examples/distributed_history/specs/program_model/External": "ExternalNext",
        # The two the negative and port corpora have ever been measured on.
        "examples/validation/ab/model/QuotaLedger": "Next",
    }
    for stem, expected in subjects.items():
        definitions = parse_tla_definitions((ROOT / f"{stem}.tla").read_text())
        cfg_name = "External" if stem.endswith("External") else Path(stem).name
        cfg = ROOT / f"{Path(stem).parent}/{cfg_name if 'distributed_history' in stem else 'QuotaLedger'}.cfg"
        resolved = resolve_next_relation(cfg.read_text(), definitions)
        assert resolved == expected, f"{stem}: resolved {resolved!r}, expected {expected!r}"
        if expected != "Next":
            assert "Next" not in definitions, (
                f"{stem} must have NO definition literally named `Next` -- that is "
                "what made the old hardcoded lookup silently empty"
            )


def test_a_model_whose_cfg_names_nothing_resolvable_still_falls_back_to_next(
    tmp_path: Path,
) -> None:
    """The fallback is the OLD behaviour, kept, so nothing that worked stops."""
    from scripts.generate_cases_from_tlc_dump import (
        parse_tla_definitions,
        resolve_next_relation,
    )

    definitions = parse_tla_definitions("Next == x' = x\n")
    assert resolve_next_relation("INVARIANT Inv\n", definitions) == "Next"


# ---------------------------------------------------------------------------
# BS-07 (#166): a ticket's OWN tlc_projection can be named. Ticket ids carry
# dashes, so `specs.tickets.MH-42.desired.tlc_projection` is not a module
# name; the file form `path/to/file.py:object` is.
# ---------------------------------------------------------------------------


def _ticket_projector(tmp_path: Path) -> Path:
    desired = tmp_path / "specs" / "tickets" / "MH-42" / "desired"
    desired.mkdir(parents=True)
    (desired / "projection_helpers.py").write_text("KIND = 'ticket'\n", encoding="utf-8")
    projector = desired / "tlc_projection.py"
    projector.write_text(
        "from dataclasses import dataclass\n"
        "from projection_helpers import KIND\n\n"
        "@dataclass\n"
        "class Shape:\n"
        "    kind: str\n\n"
        "def project_adapter_output(before, action, after, params):\n"
        "    return {'source': Shape(KIND).kind, 'action': action}\n\n"
        "class Nested:\n"
        "    @staticmethod\n"
        "    def project_state(state):\n"
        "        return {'source': KIND, **state}\n",
        encoding="utf-8",
    )
    return projector


def test_generate_cases_loads_a_dashed_ticket_projector_by_file_path(tmp_path: Path, monkeypatch) -> None:
    from scripts.generate_cases_from_tlc_dump import load_object

    projector = _ticket_projector(tmp_path)
    # A decoy `tlc_projection` that IS importable: the file form must not
    # resolve to it (the PYTHONPATH workaround in #166 would).
    decoy = tmp_path / "decoy"
    decoy.mkdir()
    (decoy / "tlc_projection.py").write_text(
        "def project_adapter_output(before, action, after, params):\n"
        "    return {'source': 'project'}\n",
        encoding="utf-8",
    )
    monkeypatch.syspath_prepend(str(decoy))

    output = load_object(f"{projector}:project_adapter_output")
    assert output({}, "Act", {}, {}) == {"source": "ticket", "action": "Act"}
    state = load_object(f"{projector}:Nested.project_state")
    assert state({"x": 1}) == {"source": "ticket", "x": 1}


def test_generate_cases_loads_a_relative_ticket_projector_path(tmp_path: Path, monkeypatch) -> None:
    from scripts.generate_cases_from_tlc_dump import load_object

    _ticket_projector(tmp_path)
    monkeypatch.chdir(tmp_path)
    output = load_object("specs/tickets/MH-42/desired/tlc_projection.py:project_adapter_output")
    assert output({}, "Act", {}, {})["source"] == "ticket"


def test_generate_cases_dotted_module_form_still_works_and_bad_paths_fail_loudly(tmp_path: Path) -> None:
    from scripts.generate_cases_from_tlc_dump import load_object

    assert load_object("json:dumps") is json.dumps
    with pytest.raises(ValueError, match="module:object"):
        load_object("json")
    with pytest.raises(ValueError, match="not found"):
        load_object(f"{tmp_path}/MH-42/missing.py:fn")
