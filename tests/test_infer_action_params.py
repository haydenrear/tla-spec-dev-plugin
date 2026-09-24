"""MF-029: action-parameter recovery, with a negative control per action.

THE TRAP THIS FILE EXISTS TO PREVENT
------------------------------------
MF-028's spike defaulted ``spec_root`` from ``case.after`` and then "checked"
the result against ``case.after``. The check could not fail, so it passed
vacuously. It was caught only because a negative control that SHOULD have
failed, passed.

So every action here gets two things:

1. a POSITIVE test, deriving the expected parameter by hand from the
   before-state and the transition -- never from the field being checked; and
2. a NEGATIVE CONTROL, a deliberately wrong expectation that MUST make the
   check fail.

``test_every_negative_control_actually_fails`` then executes every negative
control and asserts each one raises. A check that cannot fail is not a check,
and that test is what proves these can. It is the regression guard, and if it
ever goes green-by-vacuity the whole file is worthless.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = REPO_ROOT / "skills" / "spec-double-2"
sys.path.insert(0, str(SKILL_ROOT / "scripts"))

from infer_action_params import (  # noqa: E402
    ENTERED,
    EXCEPT_INDEX,
    EXCEPT_VALUE,
    GUARD_PINNED,
    LEFT,
    SET_MEMBERSHIP,
    UNCHECKED,
    UNRECOVERABLE,
    WRITTEN_THROUGH,
    build_recipes,
    build_recipes_from_path,
    infer_params,
    measure_recovery,
    render_audit,
)

# The live model is specs/current while a ticket workflow is open, and the
# accepted specs/program_model baseline once the workflow has closed (a
# promoted default-branch tree has no current/). The two are reconciled
# identical at every close, so either is the real repository model.
_CURRENT = REPO_ROOT / "specs" / "current" / "TlaSpecDevCli.tla"
LIVE_MODEL = _CURRENT if _CURRENT.exists() else REPO_ROOT / "specs" / "program_model" / "TlaSpecDevCli.tla"

# Every parameterisable action label of TlaSpecDevCli, exhaustively. The issue
# said "thirteen"; the module defined FOURTEEN (plus Stutter, which produces no
# edge under [][Next]_vars), AC-01 added AnalyzeArchitecture for FIFTEEN, RC-01
# added GenerateCases and CloseTicketWeakened for SEVENTEEN, and 2026-08-04
# removed AnalyzeArchitecture with the static architecture scanners for SIXTEEN.
# Auditing the superset is the honest reading of "audit all the labels".
ALL_ACTIONS = (
    "BuildSkillCli",
    "InstallLocalCli",
    "ScaffoldProject",
    "RecordBudgets",
    "ScaffoldWorkflow",
    "OpenTicket",
    "UpdateTicketDesired",
    "UpdateTicketCurrent",
    "AnalyzeComplexity",
    "AnalyzeCorpus",
    "GenerateCases",
    "RunEffectConformance",
    "RunSpecUnitTests",
    "CloseTicket",
    "CloseTicketWeakened",
    # SI-20: the skt surface. All three are NULLARY -- the nondeterminism is the
    # checkout's, quantified inside the action, because nobody passes "is the
    # epic unique" to `skt status`. So there is nothing for a caller to have
    # chosen and nothing for recovery to recover, which is what EXPECTED says.
    "SktStatus",
    "SktCheck",
    "SktTicketSweep",
)


@pytest.fixture(scope="module")
def recipes():
    return build_recipes_from_path(LIVE_MODEL)


# ---------------------------------------------------------------------------
# State-pair fixtures, written by hand from the model's own guards.
# ---------------------------------------------------------------------------

TICKETS = ("cli_entrypoint", "cli_workflow", "cli_validation")

# SI-20: the skt surface's resting answer. Mirrors SktSilent in the module.
SKT_SILENT = {
    "epic_named": False,
    "epic_unique": False,
    "membership_claim": False,
    "membership_joined": False,
    "verdict_current": False,
    "surfaces_measured": False,
    "sweep_planned": False,
    "containment_known": False,
}


def state(
    *,
    setup_phase: int,
    spec_root: str,
    ticket_state: dict[str, int] | None = None,
    last_command: str = "Init",
    complexity_gate: str = "unknown",
    corpus_gate: str = "unknown",
    effect_conformance: str = "unknown",
    skt_answer: dict | None = None,
) -> dict:
    base = {ticket: 0 for ticket in TICKETS}
    base.update(ticket_state or {})
    return {
        "setup_phase": setup_phase,
        "spec_root": spec_root,
        "ticket_state": base,
        "lastCommand": last_command,
        "result": {"accepted": True, "reason": "NoReason", "next": "x"},
        "complexity_gate": complexity_gate,
        "corpus_gate": corpus_gate,
        "effect_conformance": effect_conformance,
        "skt_answer": skt_answer or SKT_SILENT,
    }


def pair(action: str) -> tuple[dict, dict]:
    """One legitimate before/after state pair per action label."""
    if action in ("SktStatus", "SktCheck", "SktTicketSweep"):
        # Only skt_answer moves, and it moves to the honest answer: the guarded
        # field and the claim it licenses go TRUE together, which is exactly
        # what the four invariants require. A pair where the claim outran its
        # evidence would be a model violation, not a fixture.
        answered = dict(SKT_SILENT)
        if action == "SktStatus":
            answered.update(epic_unique=True, epic_named=True,
                            membership_joined=True, membership_claim=True)
        elif action == "SktCheck":
            answered.update(surfaces_measured=True, verdict_current=True)
        else:
            answered.update(containment_known=True, sweep_planned=True)
        return (
            state(setup_phase=5, spec_root="custom_specs"),
            state(setup_phase=5, spec_root="custom_specs",
                  last_command=action, skt_answer=answered),
        )
    if action == "BuildSkillCli":
        return (
            state(setup_phase=0, spec_root="NoRoot"),
            state(setup_phase=1, spec_root="NoRoot", last_command="BuildSkillCli"),
        )
    if action == "InstallLocalCli":
        return (
            state(setup_phase=1, spec_root="NoRoot"),
            state(setup_phase=2, spec_root="NoRoot", last_command="InstallLocalCli"),
        )
    if action == "ScaffoldProject":
        # NOTE: before.spec_root is NoRoot. The argument is NOT in the
        # before-state at all -- it only becomes visible because the action
        # writes it through. That is why this action is the trap case.
        return (
            state(setup_phase=2, spec_root="NoRoot"),
            state(setup_phase=3, spec_root="custom_specs"),
        )
    if action == "RecordBudgets":
        return (
            state(setup_phase=3, spec_root="custom_specs"),
            state(setup_phase=4, spec_root="custom_specs"),
        )
    if action == "ScaffoldWorkflow":
        return (
            state(setup_phase=4, spec_root="custom_specs"),
            state(setup_phase=5, spec_root="custom_specs"),
        )
    if action == "OpenTicket":
        return (
            state(setup_phase=5, spec_root="custom_specs"),
            state(setup_phase=5, spec_root="custom_specs", ticket_state={"cli_workflow": 1}),
        )
    if action == "UpdateTicketDesired":
        return (
            state(setup_phase=5, spec_root="custom_specs", ticket_state={"cli_validation": 1}),
            state(setup_phase=5, spec_root="custom_specs", ticket_state={"cli_validation": 2}),
        )
    if action == "UpdateTicketCurrent":
        return (
            state(setup_phase=5, spec_root="custom_specs", ticket_state={"cli_entrypoint": 2}),
            state(setup_phase=5, spec_root="custom_specs", ticket_state={"cli_entrypoint": 3}),
        )
    if action == "AnalyzeComplexity":
        return (
            state(setup_phase=4, spec_root="default_specs"),
            state(setup_phase=4, spec_root="default_specs", complexity_gate="pass"),
        )
    if action == "AnalyzeCorpus":
        return (
            state(setup_phase=4, spec_root="default_specs"),
            state(setup_phase=4, spec_root="default_specs", corpus_gate="pass"),
        )
    if action == "GenerateCases":
        # RC-01 (MF-026 G-6). Writes no verdict: generation produces the corpus,
        # AnalyzeCorpus measures it. The only observable change is the command
        # record, which is why `root` has to be recovered guard-pinned rather
        # than read off a variable this action wrote.
        return (
            state(setup_phase=4, spec_root="default_specs"),
            state(
                setup_phase=4,
                spec_root="default_specs",
                last_command="tla-spec-dev generate cases",
            ),
        )
    if action == "RunEffectConformance":
        return (
            state(setup_phase=4, spec_root="default_specs"),
            state(setup_phase=4, spec_root="default_specs", effect_conformance="clean"),
        )
    if action == "RunSpecUnitTests":
        return (
            state(
                setup_phase=5,
                spec_root="custom_specs",
                ticket_state={"cli_workflow": 3},
                complexity_gate="pass",
            ),
            state(
                setup_phase=5,
                spec_root="custom_specs",
                ticket_state={"cli_workflow": 4},
                complexity_gate="pass",
                corpus_gate="pass",
                effect_conformance="clean",
            ),
        )
    if action == "CloseTicket":
        return (
            state(setup_phase=5, spec_root="default_specs", ticket_state={"cli_validation": 4}),
            state(setup_phase=5, spec_root="default_specs", ticket_state={"cli_validation": 5}),
        )
    if action == "CloseTicketWeakened":
        # RC-01: the guard-weakening close. Note the BEFORE stage -- 1
        # (TicketOpened), not 4. That is the whole point of the transition: the
        # ticket never passed a spec-unit run, and `--accept-new` /
        # `--allow-open` close it anyway. The after stage is 6,
        # TicketClosedWeakened, which is a HIGHER ordinal than TicketClosed and
        # certifies strictly less.
        return (
            state(setup_phase=5, spec_root="default_specs", ticket_state={"cli_entrypoint": 1}),
            state(setup_phase=5, spec_root="default_specs", ticket_state={"cli_entrypoint": 6}),
        )
    raise AssertionError(f"no fixture for {action}")


# Expected arguments, derived BY HAND from the before-state and the transition.
# Compare each against pair() above: none of these is copied out of a field the
# test then goes on to check.
EXPECTED = {
    "BuildSkillCli": {},
    "InstallLocalCli": {},
    "ScaffoldProject": {"root": "custom_specs"},
    "RecordBudgets": {"root": "custom_specs"},
    "ScaffoldWorkflow": {"root": "custom_specs"},
    "OpenTicket": {"root": "custom_specs", "ticket": "cli_workflow"},
    "UpdateTicketDesired": {"ticket": "cli_validation"},
    "UpdateTicketCurrent": {"ticket": "cli_entrypoint"},
    "AnalyzeComplexity": {"root": "default_specs"},
    "AnalyzeCorpus": {"root": "default_specs"},
    "GenerateCases": {"root": "default_specs"},
    "RunEffectConformance": {"root": "default_specs"},
    # CD-09 (G2): the `override` parameter left the model with the withdrawn
    # blocking gate -- RunSpecUnitTests is (root, ticket) now.
    "RunSpecUnitTests": {
        "root": "custom_specs",
        "ticket": "cli_workflow",
    },
    "CloseTicket": {"root": "default_specs", "ticket": "cli_validation"},
    "CloseTicketWeakened": {"root": "default_specs", "ticket": "cli_entrypoint"},
    "SktStatus": {},
    "SktCheck": {},
    "SktTicketSweep": {},
}

# A deliberately WRONG expectation per action. Each must make the check fail.
NEGATIVE_CONTROLS = {
    # Nullary actions: claiming any argument at all must fail.
    "SktStatus": {"root": "default_specs"},
    "SktCheck": {"ticket": "cli_workflow"},
    "SktTicketSweep": {"root": "custom_specs"},
    "BuildSkillCli": {"root": "default_specs"},
    "InstallLocalCli": {"ticket": "cli_workflow"},
    # written-through: the other root in SpecRoots.
    "ScaffoldProject": {"root": "default_specs"},
    # guard-pinned: swap the root.
    "RecordBudgets": {"root": "default_specs"},
    "ScaffoldWorkflow": {"root": "default_specs"},
    "AnalyzeComplexity": {"root": "custom_specs"},
    "AnalyzeCorpus": {"root": "custom_specs"},
    "GenerateCases": {"root": "custom_specs"},
    "RunEffectConformance": {"root": "custom_specs"},
    # except-index: name a ticket that did not change.
    "OpenTicket": {"root": "custom_specs", "ticket": "cli_entrypoint"},
    "UpdateTicketDesired": {"ticket": "cli_workflow"},
    "UpdateTicketCurrent": {"ticket": "cli_validation"},
    "CloseTicket": {"root": "default_specs", "ticket": "cli_entrypoint"},
    "CloseTicketWeakened": {"root": "default_specs", "ticket": "cli_validation"},
    # CD-09: `override` no longer exists on this action, so claiming it is
    # claiming a phantom argument -- the check must fail rather than ignore
    # the extra key.
    "RunSpecUnitTests": {
        "root": "custom_specs",
        "ticket": "cli_workflow",
        "override": True,
    },
}


def check_params(recipes, action, expected) -> None:
    """The check under test. Raises AssertionError when the arguments differ."""
    before, after = pair(action)
    actual = infer_params(action, before, after, recipes)
    assert actual == expected, f"{action}: recovered {actual!r}, expected {expected!r}"


# ---------------------------------------------------------------------------
# Positive tests
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("action", ALL_ACTIONS)
def test_params_recovered_from_state_pair(recipes, action):
    check_params(recipes, action, EXPECTED[action])


# ---------------------------------------------------------------------------
# Negative controls -- the point of the file
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("action", ALL_ACTIONS)
def test_every_negative_control_actually_fails(recipes, action):
    """Every deliberately wrong expectation must make the check FAIL.

    If any of these stops raising, parameter recovery has become vacuous and
    the corpus is back to proving reachability only.
    """
    wrong = NEGATIVE_CONTROLS[action]
    assert wrong != EXPECTED[action], f"{action}: negative control is not actually wrong"
    with pytest.raises(AssertionError):
        check_params(recipes, action, wrong)


def test_negative_controls_cover_every_action():
    assert set(NEGATIVE_CONTROLS) == set(ALL_ACTIONS)
    assert set(EXPECTED) == set(ALL_ACTIONS)


# ---------------------------------------------------------------------------
# Anti-tautology tests: recovery must READ the state pair.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "action,variable",
    [
        ("RecordBudgets", "spec_root"),
        ("ScaffoldWorkflow", "spec_root"),
        ("AnalyzeComplexity", "spec_root"),
        ("AnalyzeCorpus", "spec_root"),
        ("RunEffectConformance", "spec_root"),
        ("OpenTicket", "spec_root"),
        ("CloseTicket", "spec_root"),
        ("RunSpecUnitTests", "spec_root"),
    ],
)
def test_guard_pinned_root_tracks_the_before_state(recipes, action, variable):
    """Perturbing the BEFORE state must move the recovered argument.

    This is what MF-028's spike lacked. A recovery that ignored the state and
    returned a constant would pass the positive test and fail here.
    """
    before, after = pair(action)
    original = infer_params(action, before, after, recipes)["root"]

    perturbed_before = dict(before)
    perturbed_before[variable] = "a_different_root"
    perturbed_after = dict(after)
    perturbed_after[variable] = "a_different_root"
    moved = infer_params(action, perturbed_before, perturbed_after, recipes)["root"]

    assert moved == "a_different_root"
    assert moved != original


@pytest.mark.parametrize(
    "action",
    [
        "RecordBudgets",
        "ScaffoldWorkflow",
        "AnalyzeComplexity",
        "AnalyzeCorpus",
        "RunEffectConformance",
        "OpenTicket",
        "CloseTicket",
        "RunSpecUnitTests",
    ],
)
def test_guard_pinned_reads_the_before_state_not_the_after_state(recipes, action):
    """Discriminate before-derivation from after-derivation. THE TRAP TEST.

    Every guard-pinned action leaves `spec_root` UNCHANGED, so in any state pair
    the model can actually produce, before and after agree -- and a recovery
    that wrongly read the AFTER state would return the identical value and pass
    every other test in this file. That mutation genuinely survived the suite
    until this test existed.

    So this test feeds a state pair the model would never emit, where the two
    disagree, purely to force the distinction. The guard is `root = spec_root`
    on the UNPRIMED variable, so the answer must be the BEFORE value. This is
    the difference between recovering a parameter and reading it back off the
    thing you are about to check.
    """
    before, after = pair(action)
    before = dict(before)
    after = dict(after)
    before["spec_root"] = "root_before"
    after["spec_root"] = "root_after"

    recovered = infer_params(action, before, after, recipes)["root"]
    assert recovered == "root_before", (
        f"{action}: guard-pinned recovery must read the before-state; "
        f"got {recovered!r}, which is the after-state value"
    )
    assert recovered != "root_after"


@pytest.mark.parametrize(
    "action,changed_ticket",
    [
        ("OpenTicket", "cli_workflow"),
        ("UpdateTicketDesired", "cli_validation"),
        ("UpdateTicketCurrent", "cli_entrypoint"),
        ("CloseTicket", "cli_validation"),
        ("RunSpecUnitTests", "cli_workflow"),
    ],
)
def test_except_index_tracks_which_entry_changed(recipes, action, changed_ticket):
    """The recovered ticket must be the index that actually differs."""
    before, after = pair(action)
    assert infer_params(action, before, after, recipes)["ticket"] == changed_ticket

    # Move the change to a different index; the recovered argument must follow.
    other = next(t for t in TICKETS if t != changed_ticket)
    swapped_before = dict(before)
    swapped_after = dict(after)
    swapped_before["ticket_state"] = {
        other: before["ticket_state"][changed_ticket],
        **{t: before["ticket_state"][t] for t in TICKETS if t != other},
    }
    swapped_before["ticket_state"][changed_ticket] = before["ticket_state"][other]
    swapped_after["ticket_state"] = dict(swapped_before["ticket_state"])
    swapped_after["ticket_state"][other] = after["ticket_state"][changed_ticket]

    assert infer_params(action, swapped_before, swapped_after, recipes)["ticket"] == other


def test_scaffold_project_root_is_not_in_the_before_state(recipes):
    """The written-through case, stated explicitly.

    `root` is recovered from `spec_root'`. It is therefore legitimate to
    recover, and ILLEGITIMATE to then check `spec_root` in the after-state
    against it -- that comparison is the MF-028 tautology. The recipe reports
    the field as unavailable so a consumer cannot make that mistake silently.
    """
    before, after = pair("ScaffoldProject")
    assert before["spec_root"] == "NoRoot"  # the argument is genuinely absent here
    recovered = infer_params("ScaffoldProject", before, after, recipes)["root"]
    assert recovered == after["spec_root"]
    assert recipes["ScaffoldProject"].unavailable_checks == ("spec_root",)


def test_only_written_through_actions_block_a_check(recipes):
    """No guard-pinned or except-index action sacrifices an after-state field."""
    blocking = {
        action: recipe.unavailable_checks
        for action, recipe in recipes.items()
        if recipe.unavailable_checks
    }
    assert blocking == {"ScaffoldProject": ("spec_root",)}


# ---------------------------------------------------------------------------
# UNCHECKED is never fabricated and never permissive.
# ---------------------------------------------------------------------------


def test_override_is_gone_from_the_model_not_inferred(recipes):
    """CD-09 (G2): the withdrawn --allow-over-budget override left the model.

    The parameter list is parsed from the module source, so this is a
    regression against the blocking gate quietly returning: RunSpecUnitTests
    must infer exactly (root, ticket) and nothing may fabricate an `override`.
    """
    before, after = pair("RunSpecUnitTests")
    params = infer_params("RunSpecUnitTests", before, after, recipes)
    assert "override" not in params
    assert set(params) == {"root", "ticket"}


@pytest.mark.parametrize("value", [True, False, None, 0, "", "TRUE", "override"])
def test_unchecked_never_equals_a_concrete_value(value):
    assert UNCHECKED != value
    assert value != UNCHECKED
    assert not (UNCHECKED == value)


def test_unchecked_equals_only_itself():
    from infer_action_params import Unchecked

    assert UNCHECKED == UNCHECKED
    assert UNCHECKED == Unchecked()  # singleton
    assert repr(UNCHECKED) == "UNCHECKED"


def test_except_index_returns_unchecked_when_nothing_changed(recipes):
    """RunSpecUnitTests on a failing gate leaves ticket_state unchanged.

    The model's `ticket_state' = IF ... THEN [... EXCEPT ![ticket] ...] ELSE
    ticket_state` means the EXCEPT branch is not always taken. On the ELSE edge
    the ticket argument is genuinely not determined by the state pair, so it
    must come back UNCHECKED rather than guessed -- and the case is still a
    case.
    """
    before = state(
        setup_phase=5,
        spec_root="custom_specs",
        ticket_state={"cli_workflow": 3},
        complexity_gate="pass",
    )
    after = state(
        setup_phase=5,
        spec_root="custom_specs",
        ticket_state={"cli_workflow": 3},  # unchanged: gate failed
        complexity_gate="pass",
        corpus_gate="fail",
        effect_conformance="clean",
    )
    params = infer_params("RunSpecUnitTests", before, after, recipes)
    assert params["ticket"] is UNCHECKED
    assert params["root"] == "custom_specs"  # still recovered, guard-pinned


def test_ambiguous_multi_index_diff_is_unchecked(recipes):
    """Two changed indices do not justify picking one."""
    before = state(setup_phase=5, spec_root="custom_specs")
    after = state(
        setup_phase=5,
        spec_root="custom_specs",
        ticket_state={"cli_workflow": 1, "cli_entrypoint": 1},
    )
    assert infer_params("OpenTicket", before, after, recipes)["ticket"] is UNCHECKED


# ---------------------------------------------------------------------------
# The audit itself
# ---------------------------------------------------------------------------


def test_audit_covers_every_action(recipes):
    audit = render_audit(recipes)
    for action in ALL_ACTIONS:
        assert f"`{action}`" in audit, f"{action} missing from the audit"
    # CD-09: no parameter anywhere in the model is unrecoverable any more --
    # `override`, the one UNCHECKED parameter, left with the withdrawn gate.
    assert "override" not in audit


def test_mechanism_classification_matches_the_model(recipes):
    def mechanism(action, param):
        return next(p.mechanism for p in recipes[action].params if p.name == param)

    assert mechanism("ScaffoldProject", "root") == WRITTEN_THROUGH
    assert mechanism("OpenTicket", "root") == GUARD_PINNED
    assert mechanism("OpenTicket", "ticket") == EXCEPT_INDEX
    assert mechanism("CloseTicket", "root") == GUARD_PINNED
    assert mechanism("CloseTicket", "ticket") == EXCEPT_INDEX
    assert recipes["BuildSkillCli"].params == ()
    assert recipes["InstallLocalCli"].params == ()


def test_every_action_label_is_audited(recipes):
    """Completeness: every Next disjunct appears, none is silently skipped.

    AC-01 added the fifteenth, AnalyzeArchitecture. RC-01 added the sixteenth
    and seventeenth: GenerateCases (MF-026 G-6, case-module generation, which
    the model did not contain at all) and CloseTicketWeakened (the close taken
    around the precondition TLC proves over the whole state space). 2026-08-04
    removed AnalyzeArchitecture with the static architecture scanners, which is
    the first time this count has gone DOWN -- and the reason the assertion is
    set equality rather than a length: a label that disappears must fail here
    just as loudly as one that appears. CA-04 removed the mutation kill test
    (RM-03-DF-05) and this set was updated DELIBERATELY rather than repaired --
    it tracks the model's action set by construction, so an action removed from
    the model must leave it. The test fired exactly as designed.
    """
    audited = set(recipes) - {"Stutter"}
    assert audited == set(ALL_ACTIONS), f"unaudited: {audited ^ set(ALL_ACTIONS)}"


# ---------------------------------------------------------------------------
# Revertibility and inertness
# ---------------------------------------------------------------------------


def test_inference_is_off_without_recipes():
    """Passing no recipes restores the old params={} behavior exactly."""
    before, after = pair("OpenTicket")
    assert infer_params("OpenTicket", before, after, None) == {}
    assert infer_params("OpenTicket", before, after, {}) == {}


def test_unknown_action_yields_no_params(recipes):
    before, after = pair("OpenTicket")
    assert infer_params("NotAnAction", before, after, recipes) == {}


def test_module_without_parameters_produces_empty_recipes():
    source = """
VARIABLES x

Init == x = 0

Tick ==
  /\\ x' = x + 1
"""
    recipes = build_recipes(source)
    assert recipes["Tick"].params == ()
    assert recipes["Tick"].fully_recoverable


# ---------------------------------------------------------------------------
# RP-02: set-membership recovery, and an audit that reports what a run measured
# ---------------------------------------------------------------------------
#
# Two defects, one ticket. MF-029 recovered 0 of 5 parameters on a set-valued
# model, so every case carried `params={'i': UNCHECKED}` and the ex4 adapter
# re-derived the argument by diffing before against after -- from the ORACLE
# (EV-01-DF-01). Meanwhile the audit printed "Every parameter of every action
# is recoverable from its state pair" on a run that had just reported
# `0/38 cases carry arguments`, because it was rendered from the module's
# SYNTAX and never from the corpus (EV-02-DF-03).
#
# The same discipline as the rest of this file applies: every positive check
# below is paired with a case that MUST make it fail. A recovery that cannot
# return UNCHECKED is not a recovery, it is a fabricator.

SET_MODEL = """
VARIABLES inbox, accepted, queue, delivered, failed, ledger

Init ==
  /\\ inbox = Items
  /\\ accepted = {}

Accept(i) ==
  /\\ i \\in inbox
  /\\ inbox' = inbox \\ {i}
  /\\ accepted' = accepted \\cup {i}
  /\\ UNCHANGED << queue, delivered, failed, ledger >>

Enqueue(i) ==
  /\\ i \\in accepted
  /\\ i \\notin queue
  /\\ queue' = queue \\cup {i}
  /\\ UNCHANGED << inbox, accepted, delivered, failed, ledger >>

Deliver(i) ==
  /\\ i \\in queue
  /\\ queue' = queue \\ {i}
  /\\ delivered' = delivered \\cup {i}
  /\\ UNCHANGED << inbox, accepted, failed, ledger >>

Record(i) ==
  /\\ i \\in delivered
  /\\ ledger' = {i} \\union ledger
  /\\ UNCHANGED << inbox, accepted, queue, delivered, failed >>
"""


@pytest.fixture
def set_recipes():
    return build_recipes(SET_MODEL)


def set_state(**overrides):
    state = {
        name: frozenset()
        for name in ("inbox", "accepted", "queue", "delivered", "failed", "ledger")
    }
    state.update({name: frozenset(value) for name, value in overrides.items()})
    return state


@pytest.mark.parametrize(
    "action, sources",
    [
        ("Accept", (("inbox", LEFT), ("accepted", ENTERED))),
        ("Enqueue", (("queue", ENTERED),)),
        ("Deliver", (("queue", LEFT), ("delivered", ENTERED))),
        # `{i} \union ledger` -- the singleton on the left, the alternate spelling.
        ("Record", (("ledger", ENTERED),)),
    ],
)
def test_set_membership_is_classified_with_every_witness(set_recipes, action, sources):
    recovery = set_recipes[action].params[0]
    assert recovery.mechanism == SET_MEMBERSHIP
    assert recovery.sources == sources
    assert recovery.recoverable


def test_the_whole_set_valued_model_recovers(set_recipes):
    """The measured defect, inverted: MF-029 recovered 0 of 4 here."""
    assert all(recipe.fully_recoverable for recipe in set_recipes.values())
    assert not any(
        param.mechanism == UNRECOVERABLE
        for recipe in set_recipes.values()
        for param in recipe.params
    )


@pytest.mark.parametrize(
    "action, before, after, expected, wrong",
    [
        (
            "Accept",
            set_state(inbox=["i1", "i2"]),
            set_state(inbox=["i1"], accepted=["i2"]),
            "i2",
            "i1",
        ),
        (
            "Enqueue",
            set_state(accepted=["i1", "i2"]),
            set_state(accepted=["i1", "i2"], queue=["i1"]),
            "i1",
            "i2",
        ),
        (
            "Deliver",
            set_state(queue=["i1", "i2"]),
            set_state(queue=["i2"], delivered=["i1"]),
            "i1",
            "i2",
        ),
        (
            "Record",
            set_state(delivered=["i1", "i2"]),
            set_state(delivered=["i1", "i2"], ledger=["i2"]),
            "i2",
            "i1",
        ),
    ],
)
def test_set_membership_recovers_the_element_that_moved(
    set_recipes, action, before, after, expected, wrong
):
    assert infer_params(action, before, after, set_recipes) == {"i": expected}
    # NEGATIVE CONTROL. The check above is worthless unless it can fail, and a
    # recovery that returned the wrong item would still be a `str`.
    assert infer_params(action, before, after, set_recipes) != {"i": wrong}


def test_two_elements_moving_at_once_is_unchecked(set_recipes):
    """The soundness bound, stated as a test rather than as a comment."""
    before = set_state(accepted=["i1", "i2", "i3"])
    after = set_state(accepted=["i1", "i2", "i3"], queue=["i1", "i2"])
    assert infer_params("Enqueue", before, after, set_recipes) == {"i": UNCHECKED}


def test_witnesses_that_disagree_are_unchecked(set_recipes):
    """`Deliver` has two witnesses; a state pair where they name different
    elements does not determine the argument, and no witness gets to win."""
    before = set_state(queue=["i1", "i2"])
    after = set_state(queue=["i2"], delivered=["i3"])
    assert infer_params("Deliver", before, after, set_recipes) == {"i": UNCHECKED}


def test_a_witness_that_saw_nothing_move_does_not_veto_one_that_did(set_recipes):
    """`delivered` gaining i1 while `queue` is unchanged still recovers i1.

    An inapplicable witness is absent evidence, not contrary evidence.
    """
    before = set_state(queue=["i1"], delivered=["i9"])
    after = set_state(queue=["i1"], delivered=["i9", "i1"])
    assert infer_params("Deliver", before, after, set_recipes) == {"i": "i1"}


def test_nothing_moving_anywhere_is_unchecked(set_recipes):
    unchanged = set_state(inbox=["i1"], accepted=["i2"])
    assert infer_params("Accept", unchanged, unchanged, set_recipes) == {"i": UNCHECKED}


def test_non_set_values_are_unchecked_not_coerced(set_recipes):
    before = {"queue": "not-a-set", "delivered": "not-a-set"}
    after = {"queue": "not-a-set-either", "delivered": "still-not"}
    assert infer_params("Deliver", before, after, set_recipes) == {"i": UNCHECKED}


def test_set_difference_is_not_confused_with_set_union():
    """`\\cup` and `\\` both start with a backslash; the directions must not swap."""
    recipes = build_recipes(
        """
VARIABLES a

Drop(i) ==
  /\\ a' = a \\ {i}
"""
    )
    assert recipes["Drop"].params[0].sources == (("a", LEFT),)
    assert infer_params(
        "Drop", {"a": frozenset({"x", "y"})}, {"a": frozenset({"y"})}, recipes
    ) == {"i": "x"}
    # NEGATIVE CONTROL: read as a union it would find nothing entering and
    # report UNCHECKED, so this assertion fails if the direction ever flips.
    assert infer_params(
        "Drop", {"a": frozenset({"x", "y"})}, {"a": frozenset({"y"})}, recipes
    ) != {"i": UNCHECKED}


def test_a_before_state_pin_still_beats_a_set_conjunct():
    """Preference order is unchanged: the mechanism reading the least of the
    after-state wins, and guard-pinned reads none of it."""
    recipes = build_recipes(
        """
VARIABLES root, seen

Visit(p) ==
  /\\ p = root
  /\\ seen' = seen \\cup {p}
"""
    )
    assert recipes["Visit"].params[0].mechanism == GUARD_PINNED
    assert infer_params(
        "Visit", {"root": "r", "seen": frozenset()}, {"root": "r", "seen": frozenset({"r"})}, recipes
    ) == {"p": "r"}


def test_a_set_conjunct_beats_a_written_through_conjunct():
    recipes = build_recipes(
        """
VARIABLES seen, last

Visit(p) ==
  /\\ seen' = seen \\cup {p}
  /\\ last' = p
"""
    )
    recovery = recipes["Visit"].params[0]
    assert recovery.mechanism == SET_MEMBERSHIP
    # And therefore `last` is NOT declared tautological -- the recovery never
    # read it, so an adapter may still check it.
    assert recipes["Visit"].unavailable_checks == ()


def test_set_membership_reports_the_observation_it_consumed(set_recipes):
    assert set_recipes["Accept"].consumed_observations == (
        "which element entered `accepted`",
        "which element left `inbox`",
    )
    # It is NOT the stronger claim: no whole after-state field is tautological.
    assert set_recipes["Accept"].unavailable_checks == ()


# ---------------------------------------------------------------------------
# The audit must agree with the corpus it audits (EV-02-DF-03)
# ---------------------------------------------------------------------------

BANNED_CLAIM = "Every parameter of every action is recoverable from its state pair."


def measured(recipes, observations):
    return render_audit(recipes, measure_recovery(observations))


def test_measure_recovery_counts_cases_not_syntax():
    measurement = measure_recovery(
        [
            ("Accept", {"i": "i1"}),
            ("Accept", {"i": UNCHECKED}),
            ("Enqueue", {"i": UNCHECKED}),
        ]
    )
    assert measurement.total_cases == 3
    assert measurement.action_cases == {"Accept": 2, "Enqueue": 1}
    assert measurement.for_param("Accept", "i").recovered == 1
    assert measurement.for_param("Accept", "i").verdict == "partial"
    assert measurement.for_param("Enqueue", "i").verdict == "UNRECOVERABLE"
    assert measurement.for_param("Deliver", "i").verdict == "not exercised"
    assert not measurement.fully_recovered


def test_the_audit_never_claims_recoverability_over_a_corpus_carrying_nothing(set_recipes):
    """THE REGRESSION GUARD FOR EV-02-DF-03.

    Statically every parameter here is recoverable. If the run recovered none,
    the audit must say UNRECOVERABLE anyway -- the measurement is the finding.
    """
    audit = measured(
        set_recipes,
        [(action, {"i": UNCHECKED}) for action in ("Accept", "Enqueue", "Deliver", "Record")] * 10,
    )
    assert BANNED_CLAIM not in audit
    assert "UNRECOVERABLE ON THIS CORPUS" in audit
    for action in ("Accept", "Enqueue", "Deliver", "Record"):
        assert f"`{action}(i)` -- 0 of 10 cases carry an argument" in audit
    assert "recovered on every one of its cases" not in audit


def test_the_audit_reports_a_partially_failing_run_as_partial(set_recipes):
    """The ticket's own acceptance: an audit on a run where recovery PARTLY
    fails must show the partial failure, per class, and claim nothing more."""
    observations = [("Accept", {"i": "i1"})] * 7 + [("Accept", {"i": UNCHECKED})] * 3
    observations += [("Enqueue", {"i": "i2"})] * 5
    audit = measured(set_recipes, observations)

    assert BANNED_CLAIM not in audit
    assert "**PARTIAL -- 7 of 10 cases carry it**" in audit
    assert "`Accept(i)` -- 7 of 10 cases carry an argument, 3 carry `UNCHECKED`" in audit
    assert "recovered in 5 of 5 cases" in audit
    # Deliver and Record were never entered, and the audit says so instead of
    # counting them as either a success or a failure.
    assert audit.count("*not exercised by this corpus (0 cases)*") == 2
    assert "recovered on every one of its cases" not in audit


def test_a_fully_recovered_run_scopes_its_claim_to_the_run(set_recipes):
    audit = measured(
        set_recipes,
        [(action, {"i": "i1"}) for action in ("Accept", "Enqueue", "Deliver", "Record")],
    )
    assert BANNED_CLAIM not in audit
    assert "THIS CORPUS EXERCISES" in audit
    assert "it is not a claim about actions no case reached" in audit
    assert "UNRECOVERABLE ON THIS CORPUS" not in audit


def test_an_empty_corpus_makes_no_claim_at_all(set_recipes):
    audit = measured(set_recipes, [])
    assert BANNED_CLAIM not in audit
    assert "The corpus is EMPTY (0 cases)" in audit
    assert "no recoverability claim is made" in audit


def test_an_unmeasured_audit_declares_itself_static(set_recipes):
    audit = render_audit(set_recipes)
    assert BANNED_CLAIM not in audit
    assert "STATIC AUDIT -- NO CORPUS WAS MEASURED" in audit
    assert "states NOTHING about how many cases carry an argument" in audit
    assert "Measured on this corpus" not in audit


def test_the_live_model_audit_carries_no_unmeasured_claim(recipes):
    """The repository's own model, through the same guard."""
    assert BANNED_CLAIM not in render_audit(recipes)


def test_model_declared_arguments_are_not_credited_as_recovered():
    """EV-02-DF-03 in its original shape: a NULLARY model, 7 cases with args.

    `reminder_worker` declares no formal parameter anywhere and states its
    arguments through an action marker instead. The old audit read the module,
    found nothing unrecoverable, and printed "Every parameter of every action
    is recoverable from its state pair" -- a vacuous universal over an empty
    set, published next to a corpus this module had contributed nothing to.
    """
    recipes = build_recipes(
        """
VARIABLES status, lastInternalAction

Process ==
  /\\ status' = "done"
  /\\ lastInternalAction' = [name |-> "Process"]
"""
    )
    assert recipes["Process"].params == ()

    audit = render_audit(
        recipes, measure_recovery([("Process", {"scenario": "empty"})] * 7)
    )
    assert BANNED_CLAIM not in audit
    assert "**Model-declared, not recovered.**" in audit
    assert "`Process(scenario)` -- stated by the model on 7 of 7 cases" in audit
    assert "this module recovered nothing and makes no recoverability claim" in audit
    assert "was recovered on every one of its cases" not in audit


# ---------------------------------------------------------------------------
# EVAL-STABLE: `except-value` -- the parameter written INTO a function entry
# ---------------------------------------------------------------------------
#
# The mechanism exists because of a measured red control, not because a shape
# looked reachable. `Reserve(t, a, r)` in the quota-ledger fixture writes
# `amt' = [amt EXCEPT ![r] = a]`: the amount is in the state pair as plainly as
# anything can be, and the four earlier mechanisms all miss it because they only
# ever look at INDICES and WHOLE variables. The measured consequence was that 0
# of 588 `Reserve` cases carried an argument, every one was skipped, and the
# evaluation's positive control -- a fault seeded inside `reserve` -- survived
# every generated instrument.

VALUE_MODEL = """
VARIABLES amt, available, holder

Reserve(t, a, r) ==
  /\\ available' = [available EXCEPT ![t] = @ - a]
  /\\ holder' = [holder EXCEPT ![r] = t]
  /\\ amt' = [amt EXCEPT ![r] = a]
"""


@pytest.fixture
def value_recipes():
    return build_recipes(VALUE_MODEL)


def test_except_value_recovers_the_written_amount(value_recipes):
    """The whole point: `a` is recoverable and it used to be UNRECOVERABLE."""
    recovery = {param.name: param for param in value_recipes["Reserve"].params}
    assert recovery["a"].mechanism == EXCEPT_VALUE
    assert recovery["a"].variable == "amt"
    # And the two mechanisms that already worked are untouched.
    assert recovery["t"].mechanism == EXCEPT_INDEX
    assert recovery["r"].mechanism == EXCEPT_INDEX

    before = {
        "amt": {"r1": 0, "r2": 0},
        "available": {"t1": 2, "t2": 2},
        "holder": {"r1": "none", "r2": "none"},
    }
    after = {
        "amt": {"r1": 2, "r2": 0},
        "available": {"t1": 0, "t2": 2},
        "holder": {"r1": "t1", "r2": "none"},
    }
    assert infer_params("Reserve", before, after, value_recipes) == {
        "t": "t1", "a": 2, "r": "r1",
    }
    # NEGATIVE CONTROL: derived by hand from the transition, so a mechanism that
    # silently returned the INDEX rather than the VALUE would fail here.
    assert infer_params("Reserve", before, after, value_recipes)["a"] != "r1"


def test_an_expression_containing_the_parameter_is_not_recovered_as_its_value():
    """`![t] = @ - a` writes an EXPRESSION, and the entry is not `a`.

    This is the soundness bound of the mechanism and the one way it could
    fabricate: matching a right-hand side that merely MENTIONS the parameter
    would have read `available'[t]` -- the remaining quota -- and called it the
    amount. Every downstream comparison would then have agreed with a number the
    oracle invented.
    """
    recipes = build_recipes(
        """
VARIABLES available

Spend(t, a) ==
  /\\ available' = [available EXCEPT ![t] = @ - a]
"""
    )
    recovery = {param.name: param for param in recipes["Spend"].params}
    assert recovery["t"].mechanism == EXCEPT_INDEX
    assert recovery["a"].mechanism == UNRECOVERABLE
    assert infer_params(
        "Spend", {"available": {"t1": 5}}, {"available": {"t1": 3}}, recipes
    ) == {"t": "t1", "a": UNCHECKED}


def test_except_value_is_unchecked_when_the_entry_did_not_change(value_recipes):
    """Writing the value already there leaves the state pair silent about it."""
    unchanged = {
        "amt": {"r1": 0, "r2": 0},
        "available": {"t1": 2, "t2": 2},
        "holder": {"r1": "none", "r2": "none"},
    }
    assert infer_params("Reserve", unchanged, unchanged, value_recipes)["a"] is UNCHECKED


def test_except_value_is_unchecked_when_two_entries_changed(value_recipes):
    """An ambiguous diff is not a licence to pick one."""
    before = {"amt": {"r1": 0, "r2": 0}, "available": {"t1": 2}, "holder": {"r1": "none"}}
    after = {"amt": {"r1": 1, "r2": 2}, "available": {"t1": 1}, "holder": {"r1": "t1"}}
    assert infer_params("Reserve", before, after, value_recipes)["a"] is UNCHECKED


def test_except_value_declares_the_entry_it_read_as_no_longer_checkable(value_recipes):
    """The MF-028 price, paid out loud: `amt` is tautological for this action."""
    assert value_recipes["Reserve"].unavailable_checks == ("amt",)


def test_except_value_is_last_so_no_existing_recipe_moves():
    """Every earlier mechanism still wins over the same body.

    Appending at the end is what makes the change incapable of re-classifying a
    parameter some other mechanism already reached; only `UNRECOVERABLE` can
    become `except-value`.
    """
    recipes = build_recipes(
        """
VARIABLES pinned, seen, last, table

PinWins(p) ==
  /\\ p = pinned
  /\\ table' = [table EXCEPT ![1] = p]

SetWins(p) ==
  /\\ seen' = seen \\cup {p}
  /\\ table' = [table EXCEPT ![1] = p]

WrittenWins(p) ==
  /\\ last' = p
  /\\ table' = [table EXCEPT ![1] = p]
"""
    )
    assert recipes["PinWins"].params[0].mechanism == GUARD_PINNED
    assert recipes["SetWins"].params[0].mechanism == SET_MEMBERSHIP
    assert recipes["WrittenWins"].params[0].mechanism == WRITTEN_THROUGH


def test_the_quota_ledger_fixture_now_recovers_every_reserve_argument():
    """The regression this mechanism exists for, on the fixture that measured it."""
    model = REPO_ROOT / "examples/validation/ab/model/QuotaLedger.tla"
    recipes = build_recipes_from_path(model)
    mechanisms = {param.name: param.mechanism for param in recipes["Reserve"].params}
    assert mechanisms == {"t": EXCEPT_INDEX, "a": EXCEPT_VALUE, "r": EXCEPT_INDEX}
    assert recipes["Reserve"].fully_recoverable
