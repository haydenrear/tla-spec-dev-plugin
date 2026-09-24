"""`analyze complexity` is a DESCRIPTOR: it measures the model and states facts.

The load-bearing properties, in order of how much damage their absence has
already caused this repository:

1. CD-01: the descriptor makes NO suggestions. The suggested-move machinery
   (abstract/decompose/refactor recommendations) was confidently wrong on
   standard TLA+ (an aliased invariant made it recommend projecting away every
   variable) and was removed entirely.
2. CD-01 (F1): invariant aliasing/composition (`INVARIANT Inv` with
   `Inv == RealInv`) resolves transitively, so the read-by-invariant analysis
   reads the invariant's real body, not a one-token alias.
3. CD-01 (F3): with no resolvable variable domain the bound is reported as an
   explicit UNKNOWN, never a silent 1.
4. A generated-states drop at constant distinct states is reported as a RED
   FLAG, because the distinct-state gate is structurally blind to a deleted
   self-loop (MF-020).
5. MF-036: complexity is advisory, not a gate. A model over a threshold gets a
   WARNING that names the component/variable/action -- it exits 0 and case
   generation still proceeds. The command exits nonzero ONLY when it cannot
   analyze the model at all (an unresolved hierarchy); "I could not measure
   this" is an error, "this is complex" is a finding.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = REPO_ROOT / "skills" / "spec-double-2"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import pytest  # noqa: E402

from scripts.analyze_complexity import (  # noqa: E402
    EXIT_BUDGET_EXCEEDED,
    EXIT_PASS,
    UnresolvedExtendsError,
    UnsupportedModuleConstructError,
    analyze,
    bound_completeness,
    compare_tlc_reports,
    gate_report,
    main,
    extract_actions,
    extract_next_actions,
    find_next_relation,
    interaction_graph,
    greedy_communities,
    modularity,
    split_top_level_disjuncts,
    parse_cfg_constants,
    parse_cfg_invariants,
    parse_definitions,
    parse_tlc_report,
    resolve_definition_body,
    resolve_module,
    strip_frame_conditions,
)

# A deliberately small, tractable model: two latching booleans in a chain and
# one bounded counter.
SMALL_TLA = """---------------------------- MODULE Small ----------------------------
EXTENDS Naturals

CONSTANTS Items

VARIABLES started, finished, count

vars == << started, finished, count >>

Init ==
  /\\ started = FALSE
  /\\ finished = FALSE
  /\\ count = 0

Start ==
  /\\ ~started
  /\\ started' = TRUE
  /\\ UNCHANGED << finished, count >>

Finish ==
  /\\ started
  /\\ ~finished
  /\\ finished' = TRUE
  /\\ UNCHANGED << started, count >>

Bump ==
  /\\ started
  /\\ count < 2
  /\\ count' = count + 1
  /\\ UNCHANGED << started, finished >>

Next == Start \\/ Finish \\/ Bump

TypeInvariant ==
  /\\ started \\in BOOLEAN
  /\\ finished \\in BOOLEAN
  /\\ count \\in 0..2

Spec == Init /\\ [][Next]_vars
=============================================================================
"""

SMALL_CFG = """SPECIFICATION Spec

CONSTANTS
  Items = {a, b}

INVARIANTS
  TypeInvariant
"""


def write_small_model(tmp_path: Path, budgets: str = "") -> tuple[Path, Path, Path | None]:
    tla = tmp_path / "Small.tla"
    cfg = tmp_path / "MC.cfg"
    tla.write_text(SMALL_TLA, encoding="utf-8")
    cfg.write_text(SMALL_CFG, encoding="utf-8")
    manifest: Path | None = None
    if budgets:
        manifest = tmp_path / "spec_manifest.yaml"
        manifest.write_text(budgets, encoding="utf-8")
    return tla, cfg, manifest


GENEROUS_BUDGETS = """module: Small
budgets:
  max_distinct_states: 50000
  max_state_space_bound: 1000000
  max_component_variables: 6
  max_component_actions: 8
"""

TIGHT_BUDGETS = """module: Small
budgets:
  max_distinct_states: 4
  max_state_space_bound: 4
  max_component_variables: 2
  max_component_actions: 1
"""


# ---------------------------------------------------------------------------
# Dimension table and state-space bound
# ---------------------------------------------------------------------------


def test_dimension_table_and_bound_are_the_product_of_domains(tmp_path: Path) -> None:
    tla, cfg, _ = write_small_model(tmp_path)
    result = analyze(tla, cfg, None)
    cardinalities = {d.variable: d.cardinality for d in result.dimensions}
    assert cardinalities == {"started": 2, "finished": 2, "count": 3}
    assert result.bound == 2 * 2 * 3


def test_variables_unconstrained_by_type_invariant_are_excluded_not_guessed(
    tmp_path: Path,
) -> None:
    """An unknown domain must stay unknown; inventing one fakes the metric."""
    tla = tmp_path / "Small.tla"
    tla.write_text(SMALL_TLA.replace("  /\\ count \\in 0..2\n", ""), encoding="utf-8")
    cfg = tmp_path / "MC.cfg"
    cfg.write_text(SMALL_CFG, encoding="utf-8")
    result = analyze(tla, cfg, None)
    assert "count" in result.unbounded
    assert result.bound == 4
    note = next(d.note for d in result.dimensions if d.variable == "count")
    assert "unconstrained" in note


# ---------------------------------------------------------------------------
# RP-04 / CM-01-DF-03 -- a PARTIALLY resolved bound compared against the cap
# ---------------------------------------------------------------------------
#
# The fully unresolved case (bound is None) was already refused loudly: an
# explicit UNKNOWN with its own advisory. The partially resolved case was not.
# `examples/distributed_history` resolves 1 of 10 variables, so the bound is 4,
# and the scan compared that 4 against max_state_space_bound 1,000,000 as if it
# were the bound -- "0.0%, within cap", for a model TLC measures at 49,386
# distinct states. The descriptor TEXT named the nine excluded variables the
# whole time; the JSON and the ledger threw the caveat away.


PARTIAL_TLA = """\
---- MODULE Partial ----
VARIABLES flag, free

TypeInvariant ==
  /\\ flag \\in BOOLEAN

Init ==
  /\\ flag = FALSE
  /\\ free = 0

Toggle ==
  /\\ flag' = ~flag
  /\\ free' = free + 1

Next == Toggle
=============================================================================
"""

PARTIAL_CFG = "INIT Init\nNEXT Next\nINVARIANT TypeInvariant\n"


def write_partial_model(tmp_path: Path, budgets: str | None = None):
    tla = tmp_path / "Partial.tla"
    tla.write_text(PARTIAL_TLA, encoding="utf-8")
    cfg = tmp_path / "MC.cfg"
    cfg.write_text(PARTIAL_CFG, encoding="utf-8")
    manifest = None
    if budgets is not None:
        manifest = tmp_path / "spec_manifest.yaml"
        manifest.write_text(budgets, encoding="utf-8")
    return tla, cfg, manifest


def test_rp04_partially_resolved_bound_is_published_as_incomplete(
    tmp_path: Path,
) -> None:
    tla, cfg, _ = write_partial_model(tmp_path)
    result = analyze(tla, cfg, None)
    assert result.bound == 2
    completeness = result.completeness
    assert completeness.complete is False
    assert completeness.resolved == 1
    assert completeness.total == 2
    assert completeness.unresolved == ["free"]
    assert "1 of 2 declared variables" in completeness.caveat()
    assert "LOWER BOUND" in completeness.caveat()


def test_rp04_an_incomplete_bound_under_the_cap_is_never_within_cap(
    tmp_path: Path,
) -> None:
    """The whole defect in one assertion: `bound <= cap` is not a measurement."""
    tla, cfg, _ = write_partial_model(tmp_path)
    result = analyze(tla, cfg, None)
    assert result.bound is not None and result.bound < result.budgets["max_state_space_bound"]
    assert result.completeness.comparable_to_cap(result.bound, 1_000_000) is None
    warning = next(
        (w for w in result.warnings if w.kind == "state_space_bound_partial"), None
    )
    assert warning is not None, "an incomplete bound must be a stated finding"
    assert "INCOMPLETE" in warning.finding
    assert "not a measurement" in warning.finding
    # Advisory, not blocking: this is a finding, not a build failure.
    assert main([str(tla), str(cfg)]) == EXIT_PASS


def test_rp04_an_incomplete_bound_over_the_cap_keeps_the_sound_claim(
    tmp_path: Path,
) -> None:
    """Over the cap survives incompleteness -- the complete bound is larger."""
    tla, cfg, manifest = write_partial_model(
        tmp_path,
        "budgets:\n"
        "  max_state_space_bound: 1\n"
        "  max_distinct_states: 500000\n"
        "  max_component_variables: 8\n"
        "  max_component_actions: 8\n",
    )
    result = analyze(tla, cfg, manifest)
    assert result.completeness.comparable_to_cap(result.bound, 1) is False
    over = next((w for w in result.warnings if w.kind == "state_space_bound"), None)
    assert over is not None
    assert "LOWER bound" in over.finding
    # One claim, not two: the sound over-cap finding replaces the refusal.
    assert not any(w.kind == "state_space_bound_partial" for w in result.warnings)


def test_rp04_completeness_travels_in_the_json_payload(tmp_path: Path, capsys) -> None:
    import json

    tla, cfg, _ = write_partial_model(tmp_path)
    main([str(tla), str(cfg), "--format", "json"])
    measured = json.loads(capsys.readouterr().out)["measured"]
    assert measured["state_space_upper_bound"] == 2
    # Pre-RP-04 the payload published `known` and the excluded names and left a
    # reader to infer -- or not infer -- that the two are related.
    assert measured["state_space_bound_known"] is True
    assert measured["state_space_bound_complete"] is False
    assert measured["state_space_bound_resolved_variables"] == 1
    assert measured["state_space_bound_total_variables"] == 2
    assert measured["state_space_bound_within_cap"] is None
    assert "LOWER BOUND" in measured["state_space_bound_caveat"]


def test_rp04_a_complete_bound_still_reads_as_a_measurement(tmp_path: Path) -> None:
    """The fix must not turn every bound into a caveat."""
    tla, cfg, _ = write_small_model(tmp_path)
    result = analyze(tla, cfg, None)
    assert result.completeness.complete is True
    assert result.completeness.caveat() == ""
    assert result.completeness.comparable_to_cap(result.bound, 1_000_000) is True
    assert not any(w.kind == "state_space_bound_partial" for w in result.warnings)


def test_rp04_descriptor_text_states_the_consequence_next_to_the_number(
    tmp_path: Path, capsys
) -> None:
    tla, cfg, _ = write_partial_model(tmp_path)
    assert main([str(tla), str(cfg)]) == EXIT_PASS
    out = capsys.readouterr().out
    assert "[INCOMPLETE: product over 1 of 2 declared variables" in out
    assert "LOWER BOUND" in out
    assert "'within cap' is NOT a claim this scan can make" in out


def test_rp04_gate_report_clean_message_only_over_a_complete_bound(
    tmp_path: Path,
) -> None:
    tla, cfg, _ = write_partial_model(tmp_path)
    clean, message = gate_report(tla, cfg, None)
    assert clean is False
    assert "within max_state_space_bound" not in message
    small_dir = tmp_path / "small"
    small_dir.mkdir()
    small_tla, small_cfg, _ = write_small_model(small_dir)
    clean, message = gate_report(small_tla, small_cfg, None)
    assert clean is True
    assert "complete: all 3 declared variables resolved" in message


def test_rp04_shipped_example_no_longer_reports_a_partial_bound_within_cap() -> None:
    """The exact reproduction from the ticket, on the checked-in example."""
    root = REPO_ROOT / "examples" / "distributed_history" / "specs" / "program_model"
    tla = root / "External.tla"
    if not tla.is_file():
        return
    result = analyze(tla, root / "External.cfg", root / "spec_manifest.yaml")
    assert result.bound == 4
    assert len(result.variables) == 10
    completeness = result.completeness
    assert completeness.resolved == 1 and completeness.total == 10
    assert completeness.comparable_to_cap(4, result.budgets["max_state_space_bound"]) is None
    assert any(w.kind == "state_space_bound_partial" for w in result.warnings)


def test_bound_completeness_of_an_empty_dimension_table_is_not_complete() -> None:
    """A model with no variables at all is UNKNOWN, not vacuously complete."""
    empty = bound_completeness([])
    assert empty.complete is False
    assert empty.known is False
    assert empty.comparable_to_cap(None, 1_000_000) is None
    assert "no bound to compare" in empty.caveat()


def test_repository_own_model_reproduces_the_recorded_state_space_bound() -> None:
    r"""Calibration against the figures this epic has actually recorded.

    MF-020 recorded 393,216 for the 11-variable shape:
    2*2*3*2*2*2 * 2^3 * 4^3 * 2^3 = 393,216.

    MF-011 then added `complexity_gate` (3 values), making the bound exactly
    3x that: 1,179,648.

    MF-022 then collapsed the five setup booleans into `setup_phase \in 0..5`,
    replacing a 2^5 = 32 factor with a factor of 6:
    1,179,648 / 32 * 6 = 221,184.

    MF-014 then added `corpus_gate` (3 values) as the case-cap hard gate,
    tripling it again: 221,184 * 3 = 663,552. That growth is deliberate --
    an unrepresented gate is not a gate -- and stays inside
    `max_state_space_bound` 1,000,000.

    MF-025 then collapsed the per-ticket lifecycle -- active_tickets,
    closed_tickets and ticket_phase -- into `ticket_state \\in [Tickets -> 0..5]`,
    replacing an 8 * 8 * 64 = 4,096 factor with 6^3 = 216:
    663,552 / 4096 * 216 = 34,992, a factor of 18.96. Reachable states and
    depth were measured unchanged at 9,011 and 24 across that change, so the
    drop is representation, not deleted behavior.

    MF-013 then added `effect_conformance` as the effect-conformance hard
    gate. It was 4-valued, unlike its 3-valued predecessors -- "clean", "gaps"
    and "dead_surface" are distinct findings with distinct remedies and
    distinct CLI next-steps -- so it multiplied the bound by 4:
    34,992 * 4 = 139,968. Same reasoning as MF-014: an unrepresented gate is
    not a gate. Depth was measured unchanged at 24 across the change.

    MF-027 then made that same variable 5-valued by adding "unobservable":
    the effect sandbox observes the in-process CPython runtime only, and a
    target it cannot see must FAIL rather than report clean. That verdict
    selects a distinct `result.next` and a distinct CLI exit path, so leaving
    it unrepresented would make the model blind to a real outcome of a modeled
    command -- which is precisely what the verdict itself exists to report.
    The factor goes 4 -> 5: 34,992 * 5 = 174,960, still well inside
    `max_state_space_bound` 1,000,000. Depth measured unchanged at 24 again,
    and no variable or action was added (still 8 variables), so the whole
    delta is this one domain.

    MF-016 then added `kill_test` as the mutation kill-test gate -- oracle 4,
    the value floor that keeps every cost cap above it honest. It is 4-valued:
    "unknown", "pass", "below_floor", and "incomplete_catalog". The last two
    are kept apart for the same reason MF-013 kept "gaps" apart from
    "dead_surface" -- different findings with different remedies (refine the
    model at the surviving mutant's variable vs. seed a fault for an uncovered
    boundary) and distinct `result.next` strings. All three non-"unknown"
    values were confirmed individually reachable by TLC before the domain was
    fixed at four, so the domain represents the reachable set exactly.
    The factor is 4: 174,960 * 4 = 699,840, still inside
    `max_state_space_bound` 1,000,000. Measured alongside: 8 -> 9 variables,
    depth 24 -> 25, and TLC 1,067,828 -> 5,619,356 generated / 49,875 ->
    231,621 distinct (46.3% of the negotiated max_distinct_states 500,000).

    AC-01 then added `architecture_scan`, the architectural-coherence epic's
    only model delta. It is 4-valued: "unknown", "coherent", "divergent", and
    "unmappable". The last is kept distinct from "unknown" deliberately and by
    owner direction: "unknown" is "the scan has not run", "unmappable" is "the
    scan ran and could not see the target" -- the MF-027 distinction, which is
    the entire reason the effect oracle grew "unobservable". Collapsing them to
    shrink the domain would delete exactly the verdict the epic exists to
    report. The factor is 4: 699,840 * 4 = 2,799,360, which is the first time
    the STATIC bound has gone over `max_state_space_bound` 1,000,000 -- the
    scanner now warns about this model, advisory as always. Measured alongside,
    and recorded in specs/results/tlc-{baseline,desired}-epic-ac.txt: 9 -> 10
    variables, depth 25 -> 26, and TLC 6,209,780 -> 32,122,220 generated /
    283,805 -> 1,292,951 distinct. That 4.6x on reachable states is over the
    negotiated max_distinct_states 500,000, and it is recorded rather than
    negotiated away: the domain represents the reachable verdict set exactly.

    BOTH OF AC-01'S AND RC-01'S FACTORS CAME BACK OUT ON 2026-08-04, when the
    static architecture scanners were removed. Measured on MC.cfg after the
    removal: 13,008,254 generated / 563,963 distinct at depth 25, no error --
    down from 32,122,220 / 1,292,951 at depth 26. Still over
    max_distinct_states 500,000, and still recorded rather than negotiated
    away. This is the first DIVISION in the chain asserted below.

    RP-04 (CM-01-DF-03) then changed nothing about this number and everything
    about what may be said with it. The chain above has ALWAYS been a product
    over 8 of this model's 10 variables -- `lastCommand` and `result` have no
    resolvable domain and the last line of this test has asserted that since
    MF-020. What was never published is the consequence: 2,799,360 is a LOWER
    BOUND on the declared-representation bound, not the bound. Every recorded
    figure in the chain above carries the same caveat, and every multiplication
    in it is still valid, because each ticket's factor multiplied the SAME
    resolved subset -- the two unresolved variables were unresolved before and
    after every one of them. The completeness assertions below fix that
    property in place: if a future ticket resolves `lastCommand` or `result`,
    or loses a domain the resolver used to see, the chain stops being a
    like-for-like comparison and this test says so rather than silently
    multiplying through it.

    Asserting the current figure AND its relationship to each recorded
    predecessor keeps the calibration meaningful across every promotion.
    """
    tla = REPO_ROOT / "specs" / "current" / "TlaSpecDevCli.tla"
    cfg = REPO_ROOT / "specs" / "current" / "MC.cfg"
    if not tla.is_file():
        return
    result = analyze(tla, cfg, None)
    # 2026-08-04 (owner direction): THE BOUND WENT DOWN, for the first time in
    # this project's history. Every prior entry in the chain below is a
    # multiplication. This one is a division by 24, and it is a division for the
    # only honest reason a bound may shrink -- the program stopped producing the
    # outcomes the removed variables represented.
    #
    #   * `architecture_scan` (4-valued, added by AC-01) and
    #     `architecture_delta` (6-valued, added by RC-01 as G-8) were written by
    #     exactly one action, `AnalyzeArchitecture`, and read by no guard. The
    #     command and the two scanner modules behind it (1,192 + 2,325 lines)
    #     were removed; the verdicts no longer exist to record.
    #     26,671,680 / 4 / 6 = 1,111,320.
    #
    # No action left the bound: AnalyzeArchitecture wrote only these two
    # variables plus lastCommand and result, and neither of the latter pair has
    # a resolvable domain (see the completeness assertions at the end).
    #
    # CA-04 (2026-08-13): THE BOUND WENT DOWN A SECOND TIME, by exactly the
    # 4-valued `kill_test` gate, when the mutation kill test was removed
    # (RM-03-DF-05). 1,111,320 / 4 = 277,830. The MF-016 step below is GONE
    # rather than re-based: the chain gets SHORTER when model surface goes away,
    # which is the same property the 2026-08-04 removal recorded above, and it
    # is why only ONE figure in this test moves. Every other number in the chain
    # -- 174,960, 34,992, 663,552, 221,184, 1,179,648, 393,216 -- is unchanged
    # and still asserted, so this is a factor leaving a product, not a figure
    # refitted to a new answer.
    #
    # WHAT DID CHANGE AND IS NO LONGER TRUE OF THIS MODEL: the bound is now
    # UNDER `max_state_space_bound` 1,000,000 for the first time, so the scanner
    # no longer warns about it. The comment above says "a removal that happened
    # to drop the bound under the cap would be worth suspecting" -- so, stated
    # plainly rather than quietly deleted: THIS REMOVAL DID THAT. It is licensed
    # here by the CD-09 validated-refactor basis rather than by assertion --
    # TLC green on the pre-change model (563,963 distinct states, depth 25) and
    # on the post-change model (124,643, depth 24), both recorded under
    # specs/results/scorecards/cut-the-apparatus/CA-04/tlc-{before,after}.txt.
    # The bound fell because the program stopped producing the outcomes the
    # removed variable represented, which is the one honest reason it may.
    assert result.bound == 277_830
    # Undo the RC-01 weakened-close stage. With MF-016's factor gone this now
    # lands directly on the pre-MF-016 figure.
    pre_rc01_stage = result.bound // 343 * 216
    assert pre_rc01_stage == 174_960
    # ...then the MF-027 5-valued effect gate to recover the MF-025 figure...
    pre_mf013 = pre_rc01_stage // 5
    assert pre_mf013 == 34_992
    # ...undo the MF-025 lifecycle collapse to recover the MF-014 figure...
    pre_mf025 = pre_mf013 // 216 * 4096
    assert pre_mf025 == 663_552
    # ...divide out the MF-014 case-cap gate to recover the MF-022 figure...
    assert pre_mf025 // 3 == 221_184
    # ...undo the MF-022 collapse to recover the MF-011 figure...
    assert pre_mf025 // 3 // 6 * 32 == 1_179_648
    # ...and divide out the 3-valued complexity gate for the MF-020 figure.
    assert (pre_mf025 // 3 // 6 * 32) // 3 == 393_216
    # SI-20 ADDED A VARIABLE AND MOVED NO FIGURE IN THE CHAIN ABOVE, which is
    # the first time that has happened here and is worth stating rather than
    # leaving as an absence. `skt_answer` is a RECORD of eight booleans, so the
    # resolver sees no domain for it: it joins `lastCommand` and `result` in the
    # unresolved set, contributes no factor, and every recorded figure --
    # 277,830, 174,960, 34,992, 663,552, 221,184, 1,179,648, 393,216 -- is
    # unchanged and still asserted.
    #
    # That is not a free lunch and the completeness assertions below say so: the
    # product is now over 6 of NINE variables rather than 6 of eight, so the
    # measured bound is a weaker lower bound than it was yesterday. The model
    # surface grew, the STATED bound did not, and the gap between them widened.
    # A future ticket that wants a comparable figure must resolve `skt_answer`
    # -- unfolding the record into named domains would do it -- and not quote
    # 277,830 as though the addition were free.
    assert set(result.unbounded) == {"lastCommand", "result", "skt_answer"}

    # RP-04: the chain is a product over 6 of 8 variables, and says so.
    # The 2026-08-04 removal took two variables the resolver COULD see (both had
    # fixed string domains in TypeInvariant), so both counts moved by two and the
    # unresolved pair is unchanged -- which is exactly the property RP-04's
    # assertions exist to police, now exercised in the subtracting direction:
    # the chain above is still a like-for-like comparison because the removal
    # divided out of the same resolved subset every earlier factor multiplied
    # into. CA-04 took ONE more resolvable variable (`kill_test`, 4-valued),
    # so both counts moved by one again and the unresolved pair is STILL
    # unchanged: 7/9 -> 6/8.
    completeness = result.completeness
    assert completeness.resolved == 6
    # SI-20: 8 -> 9. The resolved count did NOT move, which is the whole content
    # of the change: the skt surface added state the resolver cannot see.
    assert completeness.total == 9
    assert completeness.complete is False
    assert completeness.unresolved == ["lastCommand", "result", "skt_answer"]
    # CA-04: THIS ASSERTION FLIPPED FROM `False` TO `None`, AND THE DIFFERENCE
    # IS THE POINT RP-04 BUILT THIS CLASS TO MAKE. `False` meant "incomplete,
    # but already over the cap" -- a claim that is sound in the direction it is
    # made, because the two unresolved variables can only make the complete
    # bound larger. `None` means the comparison is REFUSED: an incomplete bound
    # at or under the cap supports no statement at all.
    #
    # So the honest reading of the removal is NOT "the model is now within
    # budget". It is "the model can no longer be SAID to be over budget". The
    # measured 277,830 is a product over 6 of 8 variables and the complete bound
    # is unknown. A future ticket must not quote this as a model that came in
    # under 1,000,000.
    assert completeness.comparable_to_cap(result.bound, 1_000_000) is None
    # CA-04: these two SWAPPED, for the same reason the cap comparison went
    # False -> None. The scanner used to raise `state_space_bound` ("exceeds
    # max_state_space_bound"); it now raises `state_space_bound_partial`
    # ("INCOMPLETE and CANNOT be compared ... this scan reports the cap
    # comparison as unknown rather than as within cap"). The model did not
    # become compliant -- it became unmeasurable against the cap, and the
    # scanner says so itself rather than falling silent.
    assert any(w.kind == "state_space_bound_partial" for w in result.warnings)
    assert not any(w.kind == "state_space_bound" for w in result.warnings)


def test_cfg_constant_sets_drive_cardinality() -> None:
    constants = parse_cfg_constants(SMALL_CFG)
    assert constants["Items"] == ["a", "b"]


# ---------------------------------------------------------------------------
# RP-04 / CM-01-DF-02 -- the keyword line that ENDS an INVARIANT block
# ---------------------------------------------------------------------------
#
# The old terminator tested `re.match("^[A-Z]+\\b") and not
# re.fullmatch(identifier)`. Every all-caps keyword ALSO fullmatches the
# identifier pattern, so the guard never fired on a bare keyword line and the
# keyword fell through to the in-block branch as if it were another invariant.
# Harmless for the caller that only looks a name up in a definition table; it
# manufactured a model-pair mismatch for the caller that treats an unresolvable
# invariant name as a finding.


def test_cm01df02_bare_keyword_line_terminating_the_block_is_not_an_invariant() -> None:
    assert parse_cfg_invariants(
        "SPECIFICATION Spec\nINVARIANT Inv\nCONSTANT\n  X = 1\n"
    ) == ["Inv"]


def test_cm01df02_shipped_example_cfg_yields_only_its_invariant() -> None:
    cfg = (
        REPO_ROOT
        / "examples"
        / "distributed_history"
        / "specs"
        / "program_model"
        / "External.cfg"
    )
    if not cfg.is_file():
        return
    # Pre-fix: ['Invariant', 'CONSTANTS'].
    assert parse_cfg_invariants(cfg.read_text(encoding="utf-8")) == ["Invariant"]


@pytest.mark.parametrize(
    "keyword",
    ["CONSTANT", "CONSTANTS", "PROPERTY", "PROPERTIES", "SYMMETRY", "VIEW", "ALIAS"],
)
def test_cm01df02_every_section_keyword_closes_the_block(keyword: str) -> None:
    text = f"INVARIANTS\n  Inv\n{keyword}\n  Later\n"
    assert parse_cfg_invariants(text) == ["Inv"]


def test_cm01df02_a_keyword_carrying_a_value_also_closes_the_block() -> None:
    assert parse_cfg_invariants("INVARIANT Inv\nPROPERTY Live\n  Trailing\n") == ["Inv"]


def test_cm01df02_a_multi_line_invariant_block_still_reads_every_name() -> None:
    assert parse_cfg_invariants("INVARIANTS\n  A\n  B\n  C\nCONSTANTS\n  N = 3\n") == [
        "A",
        "B",
        "C",
    ]


def test_cm01df02_an_invariant_named_like_a_keyword_is_not_swallowed() -> None:
    """Case-sensitive: TLC keywords are uppercase, definitions need not be."""
    assert parse_cfg_invariants("INVARIANTS\n  Alias\n  View\nCONSTANTS\n  N = 3\n") == [
        "Alias",
        "View",
    ]


def test_cm01df02_a_constant_named_like_a_keyword_still_parses() -> None:
    constants = parse_cfg_constants("CONSTANTS\n  Alias = {a, b}\n  View = 3\n")
    assert constants == {"Alias": ["a", "b"], "View": "3"}


def test_cm01df02_a_keyword_with_a_value_closes_the_constants_block() -> None:
    constants = parse_cfg_constants("CONSTANTS\n  N = 3\nALIAS Debug\n  M = 4\n")
    assert constants == {"N": "3"}


def test_cm01df02_the_repository_own_cfg_is_unchanged_by_the_fix() -> None:
    cfg = REPO_ROOT / "specs" / "current" / "MC.cfg"
    if not cfg.is_file():
        return
    names = parse_cfg_invariants(cfg.read_text(encoding="utf-8"))
    assert names[0] == "TypeInvariant"
    assert not any(n.isupper() for n in names), names


# ---------------------------------------------------------------------------
# Read/write matrix and modularity
# ---------------------------------------------------------------------------


def test_read_write_matrix_separates_reads_writes_and_unchanged(tmp_path: Path) -> None:
    tla, cfg, _ = write_small_model(tmp_path)
    result = analyze(tla, cfg, None)
    by_name = {a.name: a for a in result.actions}
    assert set(by_name) == {"Start", "Finish", "Bump"}
    # Bump reads started and count, writes count, and leaves finished alone.
    assert by_name["Bump"].writes == {"count"}
    assert by_name["Bump"].reads == {"started", "count"}
    assert "finished" not in by_name["Bump"].touched


# ---------------------------------------------------------------------------
# Frame-condition fix (MF-036): `v' = v` is UNCHANGED, not a touch
# ---------------------------------------------------------------------------


def test_strip_frame_conditions_removes_exact_v_prime_equals_v() -> None:
    body = "status' = status + 1 /\\ v1' = v1 /\\ v2' = v2"
    stripped = strip_frame_conditions(body, ["status", "v1", "v2"])
    # The genuine write-that-reads survives; the two frame conditions are gone.
    assert "status' = status + 1" in stripped
    assert "v1' = v1" not in stripped
    assert "v2' = v2" not in stripped


def test_strip_frame_conditions_keeps_genuine_writes_that_read() -> None:
    # `v' = v + 1` and `v' = v \cup {x}` genuinely read the old value: never strip.
    body = "a' = a + 1 /\\ b' = b \\cup {x}"
    stripped = strip_frame_conditions(body, ["a", "b"])
    assert "a' = a + 1" in stripped
    assert "b' = b \\cup {x}" in stripped


def test_frame_condition_variable_is_not_counted_as_touched() -> None:
    """A variable left UNCHANGED by `v' = v` is NOT touched by that action."""
    module = (
        "---- MODULE Frame ----\n"
        "VARIABLES status, v1, v2\n"
        "Act == status' = status + 1 /\\ v1' = v1 /\\ v2' = v2\n"
        "====\n"
    )
    defs = parse_definitions(module)
    actions = extract_actions(defs, ["status", "v1", "v2"])
    act = {a.name: a for a in actions}["Act"]
    # Only `status` is genuinely written/read; the two frame conditions vanish.
    assert act.writes == {"status"}
    assert "v1" not in act.touched
    assert "v2" not in act.touched


def test_god_object_frame_conditions_drop_from_10_of_10_to_real_coupling() -> None:
    """The probe: five vars, ten commands, each touching only two.

    Every command frames the three variables it does not use with `v' = v`.
    Counting those as touches (the bug) reports all five variables coupled to all
    ten commands -- a fully dense 10/10 god-state. The fix reveals the real
    coupling: only the shared `status` is touched by all ten; the four domain
    variables drop to their true 2-or-3-of-10.
    """
    variables = ["status", "v1", "v2", "v3", "v4"]
    lines = []
    domain_for = ["v1", "v1", "v1", "v2", "v2", "v2", "v3", "v3", "v4", "v4"]
    for i, dom in enumerate(domain_for, start=1):
        others = [v for v in ("v1", "v2", "v3", "v4") if v != dom]
        frame = " /\\ ".join(f"{o}' = {o}" for o in others)
        lines.append(
            f"Cmd{i:02d} == status' = (status + 1) % 3 /\\ {dom}' = ({dom} + 1) % 3 /\\ {frame}"
        )
    module = "---- MODULE God ----\nVARIABLES status, v1, v2, v3, v4\n" + "\n".join(lines) + "\n====\n"
    defs = parse_definitions(module)

    # With the fix applied (the shipped behavior): real coupling.
    fixed = extract_actions(defs, variables)
    touched_counts = {v: sum(1 for a in fixed if v in a.touched) for v in variables}
    assert touched_counts["status"] == 10
    assert touched_counts["v1"] == 3
    assert touched_counts["v2"] == 3
    assert touched_counts["v3"] == 2
    assert touched_counts["v4"] == 2

    # Contrast with the pre-fix behavior (frame conditions counted as touches):
    # every variable reported touched by all ten commands.
    def unfixed_actions():
        from scripts.analyze_complexity import (
            Action,
            primed_references,
            references,
            strip_unchanged,
        )

        out = []
        for d in defs:
            b = strip_unchanged(d.body)
            w = {v for v in variables if primed_references(b, v)}
            if not w:
                continue
            r = {v for v in variables if references(b, v)}
            out.append(Action(name=d.name, reads=r, writes=w, body=b))
        return out

    before = unfixed_actions()
    before_counts = {v: sum(1 for a in before if v in a.touched) for v in variables}
    assert before_counts == {"status": 10, "v1": 10, "v2": 10, "v3": 10, "v4": 10}

    # The fix de-densifies the R/W interaction graph: the frame-condition bug
    # coupled every pair of variables (a complete graph, C(5,2)=10 edges); the
    # real coupling is a star around `status` (4 edges).
    edges_before = interaction_graph(before, variables)
    edges_after = interaction_graph(fixed, variables)
    assert len(edges_before) == 10
    assert len(edges_after) == 4


def test_modularity_is_deterministic_for_the_same_model(tmp_path: Path) -> None:
    tla, cfg, _ = write_small_model(tmp_path)
    first = analyze(tla, cfg, None)
    second = analyze(tla, cfg, None)
    assert first.modularity_score == second.modularity_score
    assert [sorted(c) for c in first.communities] == [sorted(c) for c in second.communities]


def test_dense_community_analysis_does_not_recompute_every_candidate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The close-ticket ledger must remain tractable on a dense 123-variable model."""
    variables = [f"v{index:03d}" for index in range(123)]
    active_variables = variables[:67]
    weights = {
        (left, right): 1
        for index, left in enumerate(active_variables)
        for right in active_variables[index + 1 :]
    }
    calls = 0

    def counted_modularity(partition: list[set[str]], graph: dict[tuple[str, str], int]) -> float:
        nonlocal calls
        calls += 1
        if calls > 2:
            pytest.fail("candidate partitions must not recompute modularity")
        return modularity(partition, graph)

    monkeypatch.setattr("scripts.analyze_complexity.modularity", counted_modularity)
    communities, score = greedy_communities(variables, weights)

    assert len(communities) == 57
    assert communities[0] == set(active_variables)
    assert all(len(community) == 1 for community in communities[1:])
    assert score == pytest.approx(0.0)
    assert calls == 2


def test_optimized_community_analysis_matches_the_original_search() -> None:
    """The delta formula changes cost, not merge choices or the final score."""

    def original_search(
        variables: list[str], weights: dict[tuple[str, str], int]
    ) -> tuple[list[set[str]], float]:
        partition = [{variable} for variable in variables]
        best_score = modularity(partition, weights)
        if not weights:
            return partition, best_score
        improved = True
        while improved and len(partition) > 1:
            improved = False
            best_pair: tuple[int, int] | None = None
            best_gain = 0.0
            for left_index in range(len(partition)):
                for right_index in range(left_index + 1, len(partition)):
                    connected = any(
                        (left in partition[left_index] and right in partition[right_index])
                        or (left in partition[right_index] and right in partition[left_index])
                        for left, right in weights
                    )
                    if not connected:
                        continue
                    candidate = [
                        community
                        for index, community in enumerate(partition)
                        if index not in (left_index, right_index)
                    ]
                    candidate.append(partition[left_index] | partition[right_index])
                    gain = modularity(candidate, weights) - best_score
                    if gain > best_gain + 1e-12:
                        best_gain = gain
                        best_pair = (left_index, right_index)
            if best_pair is not None:
                left_index, right_index = best_pair
                merged = partition[left_index] | partition[right_index]
                partition = [
                    community
                    for index, community in enumerate(partition)
                    if index not in (left_index, right_index)
                ]
                partition.append(merged)
                best_score += best_gain
                improved = True
        partition.sort(key=lambda community: (-len(community), sorted(community)))
        return partition, modularity(partition, weights)

    variables = ["a", "b", "c", "d", "e", "f"]
    graphs = [
        {},
        {("a", "b"): 1, ("b", "c"): 1, ("d", "e"): 1},
        {
            (left, right): ((left_index + 1) * (right_index + 3)) % 5 + 1
            for left_index, left in enumerate(variables)
            for right_index, right in enumerate(variables[left_index + 1 :], left_index + 1)
            if (left_index + right_index) % 3 != 0
        },
    ]

    for weights in graphs:
        expected_communities, expected_score = original_search(variables, weights)
        communities, score = greedy_communities(variables, weights)
        assert communities == expected_communities
        assert score == pytest.approx(expected_score, abs=1e-12)


# ---------------------------------------------------------------------------
# Landed collapses on the repository's own model
# ---------------------------------------------------------------------------


def test_repository_own_model_has_landed_the_setup_phase_collapse() -> None:
    """MF-022 applied the reduction MF-011's analyzer found on its own.

    MF-011's analyzer derived, from the model alone, that the five setup
    booleans were pinned into a total order by their own action guards so that
    32 declared combinations admitted only 6, and projected the collapse would
    take the declared bound 1,179,648 -> 221,184. MF-022 applied it. This test
    now guards the landed state: the ordinal is present, no five-member
    latching chain remains, and the bound still factors through the projected
    figure -- which is also the check that the analyzer's projection was honest.

    MF-014 later multiplied the bound by 3 by adding `corpus_gate`, so the
    projected 221,184 is asserted as a FACTOR rather than as the total. Gates
    added after the collapse do not invalidate it; a change to the setup-phase
    factor itself would still break this test.
    """
    tla = REPO_ROOT / "specs" / "current" / "TlaSpecDevCli.tla"
    cfg = REPO_ROOT / "specs" / "current" / "MC.cfg"
    if not tla.is_file():
        return
    result = analyze(tla, cfg, None)
    assert "setup_phase" in result.variables
    for removed in (
        "cli_built",
        "cli_installed",
        "project_scaffolded",
        "budgets_recorded",
        "workflow_scaffolded",
    ):
        assert removed not in result.variables
    # MF-025: the per-ticket lifecycle is one ordinal now.
    assert "ticket_state" in result.variables
    for removed in ("active_tickets", "closed_tickets", "ticket_phase"):
        assert removed not in result.variables
    # MF-013 later multiplied the bound by 4 (effect_conformance), MF-027 took
    # that factor to 5 by adding the "unobservable" verdict, MF-016 multiplied
    # by a further 4 (kill_test), and MF-025 divided the bound by 4096/216 (the
    # per-ticket lifecycle collapse) -- which RC-01 then widened from 6^3 to 7^3
    # by adding the weakened-close stage. AC-01's factor of 4
    # (architecture_scan) and RC-01's factor of 6 (architecture_delta) were both
    # REMOVED 2026-08-04 with the static architecture scanners, so they are no
    # longer divided out here: the chain gets SHORTER when model surface goes
    # away, which is the point. CA-04 removed MF-016's factor of 4 the same way
    # (the mutation kill test, RM-03-DF-05), so THAT `// 4` is gone from the
    # chain too -- the third time this has happened and the second removal to do
    # it. Undo the rest before checking the setup-phase factor. A change to the
    # setup-phase factor itself would still break this.
    pre_mf025 = result.bound // 343 * 216 // 5 // 216 * 4096
    # The figure MF-011 projected, still present as a factor of the bound
    # after MF-014's corpus_gate tripled it.
    assert pre_mf025 % 221_184 == 0
    assert pre_mf025 // 221_184 == 3  # corpus_gate, the only later addition


# ---------------------------------------------------------------------------
# CD-01: the descriptor makes no suggestions
# ---------------------------------------------------------------------------


def test_no_suggested_move_output_remains_anywhere(tmp_path: Path, capsys) -> None:
    """CD-01: facts, not judgment -- no abstract/decompose/refactor advice.

    Validation project 1 proved the suggested moves confidently wrong on
    standard TLA+ (an aliased invariant made the scanner recommend projecting
    away EVERY variable), so the machinery was removed entirely.
    """
    import json

    tla, cfg, manifest = write_small_model(tmp_path, TIGHT_BUDGETS)
    assert main([str(tla), str(cfg), "--manifest", str(manifest)]) == EXIT_PASS
    out = capsys.readouterr().out
    for banned in (
        "SUGGESTED MOVE",
        "RECOMMENDATION",
        "recommendation:",
        "ABSTRACT",
        "DECOMPOSE",
        "REFACTOR",
        "[PROJECTED]",
    ):
        assert banned not in out, f"suggested-move remnant in text output: {banned!r}"

    main([str(tla), str(cfg), "--manifest", str(manifest), "--format", "json"])
    payload = json.loads(capsys.readouterr().out)
    assert "suggested_move" not in payload
    assert "projected" not in payload
    for warning in payload["advisory"]["warnings"]:
        assert "recommendation" not in warning


def test_import_surface_has_no_suggestion_machinery() -> None:
    import scripts.analyze_complexity as mod

    for name in ("suggest_move", "OrdinalChain", "latching_booleans", "implication_chains"):
        assert not hasattr(mod, name)


def test_text_output_is_a_measured_descriptor_with_the_self_loop_warning(
    tmp_path: Path, capsys
) -> None:
    tla, cfg, _ = write_small_model(tmp_path, GENEROUS_BUDGETS)
    main([str(tla), str(cfg), "--manifest", str(tmp_path / "spec_manifest.yaml")])
    out = capsys.readouterr().out
    assert "[MEASURED]" in out
    assert "DESCRIPTOR" in out
    assert "Dense rows and columns" in out
    assert "Invariant coverage" in out
    assert "RED FLAG" in out
    assert "not a verdict" in out


# ---------------------------------------------------------------------------
# CD-01 (F1): invariant aliasing/composition resolves transitively
# ---------------------------------------------------------------------------

# Standard TLA+: the cfg names `Inv`, whose body is the one-token alias
# `RealInv`. Pre-fix, the analyzer read only the immediate alias body, saw no
# variable names, judged every variable "read by no invariant", and recommended
# projecting away the entire model.
ALIASED_TLA = SMALL_TLA.replace(
    "Spec == Init /\\ [][Next]_vars",
    "RealInv == count <= 2\n\nInv == RealInv\n\nSpec == Init /\\ [][Next]_vars",
)

ALIASED_CFG = """SPECIFICATION Spec

CONSTANTS
  Items = {a, b}

INVARIANTS
  Inv
"""


def write_aliased_model(tmp_path: Path) -> tuple[Path, Path]:
    tla = tmp_path / "Small.tla"
    cfg = tmp_path / "MC.cfg"
    tla.write_text(ALIASED_TLA, encoding="utf-8")
    cfg.write_text(ALIASED_CFG, encoding="utf-8")
    return tla, cfg


def test_f1_aliased_invariant_variables_are_read_by_invariant(tmp_path: Path) -> None:
    """The F1 regression (fails pre-fix).

    PRE-FIX: `Inv == RealInv` has no variable tokens in its immediate body, so
    unread-by-invariant == ALL variables ([started, finished, count]).
    POST-FIX: the alias resolves to RealInv's body, which reads `count`, so
    `count` is read-by-invariant and only the genuinely unread variables remain.
    """
    tla, cfg = write_aliased_model(tmp_path)
    result = analyze(tla, cfg, None)
    assert "count" not in result.unread_by_invariant
    # The two booleans really are unread by the configured invariant -- the
    # descriptor reports that fact honestly.
    assert set(result.unread_by_invariant) == {"started", "finished"}


def test_f1_composed_invariants_resolve_through_every_level(tmp_path: Path) -> None:
    """Composition `Inv == A /\\ B` with `B == C` resolves transitively."""
    tla = tmp_path / "Small.tla"
    composed = SMALL_TLA.replace(
        "Spec == Init /\\ [][Next]_vars",
        "CountInv == count <= 2\n"
        "BoolInv == started \\in BOOLEAN\n"
        "Middle == BoolInv\n"
        "Inv == CountInv /\\ Middle\n\n"
        "Spec == Init /\\ [][Next]_vars",
    )
    tla.write_text(composed, encoding="utf-8")
    cfg = tmp_path / "MC.cfg"
    cfg.write_text(ALIASED_CFG, encoding="utf-8")
    result = analyze(tla, cfg, None)
    # count via CountInv, started via Inv -> Middle -> BoolInv, two levels deep.
    assert "count" not in result.unread_by_invariant
    assert "started" not in result.unread_by_invariant
    assert result.unread_by_invariant == ["finished"]


def test_resolve_definition_body_guards_against_cycles() -> None:
    defs = {
        d.name: d
        for d in parse_definitions(
            "---- MODULE Cyc ----\nA == B\nB == A /\\ x\n====\n"
        )
    }
    resolved = resolve_definition_body("A", defs)
    assert "x" in resolved  # the cycle terminated and still reached B's body


# ---------------------------------------------------------------------------
# CD-01 (F3): the bound is meaningful or explicitly unknown -- never a silent 1
# ---------------------------------------------------------------------------

NO_TYPE_TLA = """---------------------------- MODULE NoType ----------------------------
EXTENDS Naturals

VARIABLES count

Init == count = 0

Bump ==
  /\\ count < 2
  /\\ count' = count + 1

Next == Bump

SafetyInv == count <= 2

Spec == Init /\\ [][Next]_<< count >>
=============================================================================
"""

NO_TYPE_CFG = "SPECIFICATION Spec\n\nINVARIANTS\n  SafetyInv\n"


def test_f3_bound_is_explicitly_unknown_without_any_resolvable_domain(
    tmp_path: Path, capsys
) -> None:
    """Pre-fix: no TypeInvariant meant bound == 1, silently. Now it is None."""
    tla = tmp_path / "NoType.tla"
    tla.write_text(NO_TYPE_TLA, encoding="utf-8")
    cfg = tmp_path / "MC.cfg"
    cfg.write_text(NO_TYPE_CFG, encoding="utf-8")
    result = analyze(tla, cfg, None)
    assert result.bound is None
    assert result.bound_source is None
    # The unknown is loud: an advisory warning names it.
    assert any(w.kind == "state_space_bound_unknown" for w in result.warnings)

    # And the rendered report says UNKNOWN, never 1.
    assert main([str(tla), str(cfg)]) == EXIT_PASS
    out = capsys.readouterr().out
    assert "UNKNOWN" in out
    assert "bound = 1" not in out


def test_f3_type_ok_is_accepted_as_the_domain_source(tmp_path: Path) -> None:
    """A scaffolded TypeOK bounds the model even when not named TypeInvariant."""
    tla = tmp_path / "Small.tla"
    tla.write_text(SMALL_TLA.replace("TypeInvariant ==", "TypeOK =="), encoding="utf-8")
    cfg = tmp_path / "MC.cfg"
    cfg.write_text(SMALL_CFG.replace("TypeInvariant", "TypeOK"), encoding="utf-8")
    result = analyze(tla, cfg, None)
    assert result.bound == 12
    assert result.bound_source == "TypeOK"


def test_f3_domains_resolve_from_cfg_invariants_when_no_type_invariant_exists(
    tmp_path: Path,
) -> None:
    """Membership conjuncts in configured invariants bound the model (via F1's
    transitive resolution, even behind an alias)."""
    tla = tmp_path / "NoType.tla"
    tla.write_text(
        NO_TYPE_TLA.replace(
            "SafetyInv == count <= 2",
            "RangeInv == count \\in 0..2\n\nSafetyInv == RangeInv",
        ),
        encoding="utf-8",
    )
    cfg = tmp_path / "MC.cfg"
    cfg.write_text(NO_TYPE_CFG, encoding="utf-8")
    result = analyze(tla, cfg, None)
    assert result.bound == 3
    assert result.bound_source == "the configured invariants (resolved transitively)"


# ---------------------------------------------------------------------------
# CD-05: domain resolution -- operator-defined sets (VAL-06), wrapped
# conjuncts (VAL-16), and multi-view invariant naming (VAL-17). Each test
# below FAILED before the CD-05 fix (recorded in
# specs/tickets/CD-05/results/domain_resolution_regressions.txt).
# ---------------------------------------------------------------------------

# VAL-06 shape (validation ex1-run1): TaskStatus defined as an operator in an
# EXTENDS-ed module, used in a function-set membership. Pre-fix, _set_size
# never consulted the definition map resolve_definition_body already walks, so
# `tasks` resolved unknown and the bound was UNKNOWN.
VAL06_CORE_TLA = """---- MODULE TaskCore ----
TaskStatus == {"pending", "running", "done"}
====
"""

VAL06_TASKS_TLA = """---------------------------- MODULE Tasks ----------------------------
EXTENDS Naturals, TaskCore

CONSTANTS Names

VARIABLES tasks

Init == tasks = [n \\in Names |-> "pending"]

Advance ==
  /\\ \\E n \\in Names: tasks' = [tasks EXCEPT ![n] = "done"]

Next == Advance

TypeInvariant == tasks \\in [Names -> TaskStatus]

Spec == Init /\\ [][Next]_<< tasks >>
=============================================================================
"""

VAL06_CFG = """SPECIFICATION Spec

CONSTANTS
  Names = {n1, n2}

INVARIANTS
  TypeInvariant
"""


def test_val06_operator_defined_set_in_extended_module_resolves(tmp_path: Path) -> None:
    """`tasks \\in [Names -> TaskStatus]` with TaskStatus an operator in an
    EXTENDS-ed module resolves to |TaskStatus|^|Names| = 3^2.

    PRE-FIX: _set_size resolved only literals, int ranges, BOOLEAN, unions,
    and cfg constants -- `TaskStatus` fell through every branch, `tasks`
    resolved unknown, and the bound was UNKNOWN (None) despite the invariant
    being found and the operator body being one resolve_definition_body call
    away.
    """
    (tmp_path / "TaskCore.tla").write_text(VAL06_CORE_TLA, encoding="utf-8")
    tla = tmp_path / "Tasks.tla"
    tla.write_text(VAL06_TASKS_TLA, encoding="utf-8")
    cfg = tmp_path / "MC.cfg"
    cfg.write_text(VAL06_CFG, encoding="utf-8")
    result = analyze(tla, cfg, None)
    cardinalities = {d.variable: d.cardinality for d in result.dimensions}
    assert cardinalities["tasks"] == 9  # 3^2 total functions
    assert result.bound == 9
    assert result.bound_source == "TypeInvariant"
    notes = {d.variable: d.note for d in result.dimensions}
    assert "3^2 total functions" in notes["tasks"]


# VAL-16 shape (validation ex1-run2): a membership conjunct wrapped across
# lines -- ordinary TLA+ style for a 9-element set. Pre-fix, the membership
# regex captured to end-of-line only, so `status` silently resolved unknown.
VAL16_TLA = """---------------------------- MODULE Wrapped ----------------------------
EXTENDS Naturals

VARIABLES status, count

Init ==
  /\\ status = "s1"
  /\\ count = 0

Step ==
  /\\ count < 2
  /\\ count' = count + 1
  /\\ UNCHANGED status

Next == Step

TypeInvariant ==
  /\\ status \\in {"s1", "s2", "s3", "s4",
                  "s5", "s6", "s7", "s8",
                  "s9"}
  /\\ count \\in 0..2

Spec == Init /\\ [][Next]_<< status, count >>
=============================================================================
"""

VAL16_CFG = "SPECIFICATION Spec\n\nINVARIANTS\n  TypeInvariant\n"


def test_val16_membership_conjunct_wrapped_across_lines_resolves(tmp_path: Path) -> None:
    """A `\\in` conjunct wrapped across lines resolves like its one-line form.

    PRE-FIX: the `variable \\in <domain>` regex captured `[^\\n]+` -- to
    end-of-line -- so the wrapped set literal arrived truncated at
    `{"s1", "s2", "s3", "s4",`, failed to parse, and `status` silently
    resolved unknown (bound 3 instead of 27). Post-fix the source is parsed
    conjunct-wise, so the domain expression spans lines freely.
    """
    tla = tmp_path / "Wrapped.tla"
    tla.write_text(VAL16_TLA, encoding="utf-8")
    cfg = tmp_path / "MC.cfg"
    cfg.write_text(VAL16_CFG, encoding="utf-8")
    result = analyze(tla, cfg, None)
    cardinalities = {d.variable: d.cardinality for d in result.dimensions}
    assert cardinalities["status"] == 9
    assert cardinalities["count"] == 3
    assert result.bound == 27
    assert result.unbounded == []


# VAL-17 shape (validation ex1-run2): the scaffold's own multi-view layout.
# TLA+ forbids redefining TypeInvariant in an extending view, so the view
# carries its own invariant name, configured in the cfg. Pre-fix, any
# TypeInvariant in the hierarchy became the SOLE domain source and the view's
# variables came back unresolved without renaming tricks.
VAL17_CORE_TLA = """---- MODULE ViewCore ----
VARIABLES mode

CoreInit == mode = "idle"

TypeInvariant == mode \\in {"idle", "busy"}
====
"""

VAL17_INTERNAL_TLA = """---------------------------- MODULE ViewInternal ----------------------------
EXTENDS Naturals, ViewCore

VARIABLES queue

Init ==
  /\\ CoreInit
  /\\ queue = 0

Enqueue ==
  /\\ queue < 4
  /\\ queue' = queue + 1
  /\\ UNCHANGED mode

Next == Enqueue

InternalTypeOK == queue \\in 0..4

Spec == Init /\\ [][Next]_<< mode, queue >>
=============================================================================
"""

VAL17_CFG = """SPECIFICATION Spec

INVARIANTS
  TypeInvariant
  InternalTypeOK
"""


def test_val17_multi_view_layout_merges_domain_sources_per_variable(
    tmp_path: Path,
) -> None:
    """Both views' variables resolve without renaming tricks.

    The core view owns TypeInvariant (bounding `mode`); the extending view
    cannot redefine that name, so its own invariant (`InternalTypeOK`,
    bounding `queue`) is configured in the cfg.

    PRE-FIX: TypeInvariant's presence in the hierarchy made it the SOLE
    domain source -- `queue` resolved unknown and the bound was the partial
    product 2. The run's workaround was naming one view's invariant exactly
    `TypeOK` (the Internal=TypeOK / External=TypeInvariant trick). Post-fix,
    sources merge per-variable in the documented order (TypeInvariant, then
    TypeOK, then configured invariants) -- first source that resolves wins.
    """
    (tmp_path / "ViewCore.tla").write_text(VAL17_CORE_TLA, encoding="utf-8")
    tla = tmp_path / "ViewInternal.tla"
    tla.write_text(VAL17_INTERNAL_TLA, encoding="utf-8")
    cfg = tmp_path / "MC.cfg"
    cfg.write_text(VAL17_CFG, encoding="utf-8")
    result = analyze(tla, cfg, None)
    cardinalities = {d.variable: d.cardinality for d in result.dimensions}
    assert cardinalities["mode"] == 2
    assert cardinalities["queue"] == 5
    assert result.bound == 10
    assert result.unbounded == []
    # Both contributing sources are named, in precedence order.
    assert result.bound_source == (
        "TypeInvariant + the configured invariants (resolved transitively)"
    )
    sources = {d.variable: d.source for d in result.dimensions}
    assert sources["mode"] == "TypeInvariant"
    assert sources["queue"] == "the configured invariants (resolved transitively)"


def test_cd05_genuinely_unresolvable_domain_stays_an_explicit_unknown(
    tmp_path: Path,
) -> None:
    """F3 preserved: a domain the resolver genuinely cannot size is an explicit
    UNKNOWN, never a silent number -- even now that operators are expanded."""
    (tmp_path / "TaskCore.tla").write_text(
        "---- MODULE TaskCore ----\nTaskStatus == UNION {SomeOp(x) : x \\in Vals}\n====\n",
        encoding="utf-8",
    )
    tla = tmp_path / "Tasks.tla"
    tla.write_text(VAL06_TASKS_TLA, encoding="utf-8")
    cfg = tmp_path / "MC.cfg"
    cfg.write_text(VAL06_CFG, encoding="utf-8")
    result = analyze(tla, cfg, None)
    cardinalities = {d.variable: d.cardinality for d in result.dimensions}
    assert cardinalities["tasks"] is None
    assert result.bound is None
    assert result.bound_source is None
    assert any(w.kind == "state_space_bound_unknown" for w in result.warnings)


# ---------------------------------------------------------------------------
# Justification linkage / dead weight
# ---------------------------------------------------------------------------


def test_dead_weight_flagged_only_when_a_justification_table_is_present(
    tmp_path: Path,
) -> None:
    tla, cfg, _ = write_small_model(tmp_path)
    assert analyze(tla, cfg, None).unjustified is None

    manifest = tmp_path / "spec_manifest.yaml"
    manifest.write_text(
        "module: Small\n"
        "justification:\n"
        "  started:\n"
        "    invariants: [TypeInvariant]\n"
        "    effects: []\n"
        "    kill_tests: []\n"
        "  finished:\n"
        "    invariants: []\n"
        "    effects: []\n"
        "    kill_tests: []\n",
        encoding="utf-8",
    )
    result = analyze(tla, cfg, manifest)
    # `finished` has an empty linkage, `count` is absent entirely.
    assert result.unjustified == ["finished", "count"]


def test_a_fully_linked_table_flags_nothing(tmp_path: Path) -> None:
    tla, cfg, _ = write_small_model(tmp_path)
    manifest = tmp_path / "spec_manifest.yaml"
    manifest.write_text(
        "module: Small\n"
        "justification:\n"
        "  started:\n    invariants: [TypeInvariant]\n"
        "  finished:\n    effects: [DoneSignal]\n"
        "  count:\n    kill_tests: [drop_bump]\n",
        encoding="utf-8",
    )
    assert analyze(tla, cfg, manifest).unjustified == []


# ---------------------------------------------------------------------------
# Complexity thresholds -- advisory, not blocking (MF-036)
# ---------------------------------------------------------------------------


def test_clean_within_budget(tmp_path: Path) -> None:
    tla, cfg, manifest = write_small_model(tmp_path, GENEROUS_BUDGETS)
    result = analyze(tla, cfg, manifest)
    assert result.gate_passed
    assert result.warnings == []
    assert result.violations == []
    assert main([str(tla), str(cfg), "--manifest", str(manifest)]) == EXIT_PASS


def test_over_threshold_warns_but_still_exits_zero(tmp_path: Path) -> None:
    """MF-036: over threshold is a WARNING, never a promotion block.

    The scan raises warnings, but `analyze complexity` still exits 0 -- a
    complex model is a finding, not a failure.
    """
    tla, cfg, manifest = write_small_model(tmp_path, TIGHT_BUDGETS)
    result = analyze(tla, cfg, manifest)
    assert not result.gate_passed
    assert result.warnings, "an over-threshold model must raise advisory warnings"
    joined = " ".join(result.violations)
    # MF-022: the STATIC bound is compared against max_state_space_bound, not
    # against max_distinct_states, which caps actual reachable states.
    assert "max_state_space_bound" in joined
    # The exit code is EXIT_PASS despite the warnings -- complexity never blocks.
    assert main([str(tla), str(cfg), "--manifest", str(manifest)]) == EXIT_PASS


def test_every_warning_names_a_target_and_states_only_the_fact(tmp_path: Path) -> None:
    """A warning names the component/variable/action. CD-01: it recommends
    nothing -- the descriptor states facts and the owner decides."""
    tla, cfg, manifest = write_small_model(tmp_path, TIGHT_BUDGETS)
    result = analyze(tla, cfg, manifest)
    assert result.warnings
    for warning in result.warnings:
        assert warning.finding.strip()
        assert not hasattr(warning, "recommendation")
        assert "consider" not in warning.finding.lower()


def test_component_size_thresholds_are_reported_independently(tmp_path: Path) -> None:
    tla, cfg, manifest = write_small_model(tmp_path, TIGHT_BUDGETS)
    findings = " ".join(analyze(tla, cfg, manifest).violations)
    assert "max_component_variables" in findings or "max_component_actions" in findings


def test_gate_report_names_the_dominant_dimensions_without_suggesting(tmp_path: Path) -> None:
    tla, cfg, manifest = write_small_model(tmp_path, TIGHT_BUDGETS)
    clean, message = gate_report(tla, cfg, manifest)
    assert clean is False
    assert "ADVISORY WARNINGS" in message
    assert "Dominant dimensions" in message
    # CD-01: no suggestions anywhere, and it must NOT tell the caller to refuse.
    assert "recommendation" not in message
    assert "Suggested move" not in message
    assert "REFUSING" not in message


def test_evidence_can_be_written_into_a_results_directory(tmp_path: Path) -> None:
    tla, cfg, manifest = write_small_model(tmp_path, GENEROUS_BUDGETS)
    out = tmp_path / "results" / "complexity.txt"
    main([str(tla), str(cfg), "--manifest", str(manifest), "--out", str(out)])
    assert out.is_file()
    assert "Dimension table" in out.read_text(encoding="utf-8")


def test_json_output_is_a_measured_descriptor(tmp_path: Path, capsys) -> None:
    import json

    tla, cfg, manifest = write_small_model(tmp_path, GENEROUS_BUDGETS)
    main([str(tla), str(cfg), "--manifest", str(manifest), "--format", "json"])
    payload = json.loads(capsys.readouterr().out)
    measured = payload["measured"]
    assert measured["state_space_upper_bound"] == 12
    assert measured["state_space_bound_known"] is True
    assert measured["state_space_bound_source"] == "TypeInvariant"
    assert "dense_rows" in measured
    assert "dense_columns" in measured
    assert "unread_by_invariant" in measured
    assert payload["advisory"]["blocks_promotion"] is False


# ---------------------------------------------------------------------------
# The self-loop blindness check (MF-020 finding 1)
# ---------------------------------------------------------------------------


def test_tlc_report_parsing() -> None:
    report = parse_tlc_report(
        "3664 states generated, 919 distinct states found, 0 states left on queue.\n"
        "The depth of the complete state graph search is 21.\n"
    )
    assert (report.generated, report.distinct, report.depth) == (3664, 919, 21)


def test_generated_drop_at_constant_distinct_states_is_a_red_flag() -> None:
    """The exact MF-020 signature: -13.1% generated at identical 919/21."""
    baseline = parse_tlc_report(
        "3664 states generated, 919 distinct states found.\n"
        "The depth of the complete state graph search is 21.\n"
    )
    current = parse_tlc_report(
        "3185 states generated, 919 distinct states found.\n"
        "The depth of the complete state graph search is 21.\n"
    )
    findings = compare_tlc_reports(baseline, current)
    assert findings[0]["level"] == "RED FLAG"
    assert "self-loop" in findings[0]["message"]
    assert "transition" in findings[0]["message"]


def test_a_drop_accompanied_by_fewer_distinct_states_is_not_a_red_flag() -> None:
    baseline = parse_tlc_report(
        "3664 states generated, 919 distinct states found.\n"
        "The depth of the complete state graph search is 21.\n"
    )
    current = parse_tlc_report(
        "2000 states generated, 700 distinct states found.\n"
        "The depth of the complete state graph search is 19.\n"
    )
    findings = compare_tlc_reports(baseline, current)
    assert findings[0]["level"] == "INFO"


def test_unchanged_run_reports_no_self_loop_signature() -> None:
    report = parse_tlc_report(
        "3664 states generated, 919 distinct states found.\n"
        "The depth of the complete state graph search is 21.\n"
    )
    findings = compare_tlc_reports(report, report)
    assert findings[0]["level"] == "OK"


# ---------------------------------------------------------------------------
# Case generation refusal
# ---------------------------------------------------------------------------


def run_generation(tmp_path: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    tla, cfg, _ = write_small_model(tmp_path, TIGHT_BUDGETS)
    return subprocess.run(
        [
            sys.executable,
            str(SKILL_ROOT / "scripts" / "generate_cases_from_tlc_dump.py"),
            str(tla),
            str(cfg),
            "--out",
            # RC-02 (N-2): `generate cases` now refuses an --out that resolves
            # outside a `specs/` directory, because that is the tree the
            # `spec_tree` and `spec_tree_delete` ports declare and the metadir
            # `rmtree` is derived from it. The fixture writes where the
            # declaration says it may.
            str(tmp_path / "specs" / "generated"),
            *extra,
        ],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def test_case_generation_advises_above_the_threshold_but_does_not_refuse(tmp_path: Path) -> None:
    """MF-036: over threshold, generation PRINTS the warnings and proceeds.

    It never refuses -- complexity is advisory. TLC may be unavailable in this
    environment, so the property under test is the advisory decision (no
    refusal, no nonzero-for-complexity), not whether TLC then runs.
    """
    result = run_generation(tmp_path)
    assert "ADVISORY WARNINGS" in result.stderr
    assert "Proceeding with case generation" in result.stderr
    # The old refusal and its override flag are gone entirely.
    assert "REFUSING to generate cases" not in result.stderr
    assert "allow-over-budget" not in result.stderr


def test_case_generation_has_no_over_budget_override_flag(tmp_path: Path) -> None:
    """The override existed only to bypass the gate; there is no gate to bypass."""
    result = run_generation(tmp_path, "--allow-over-budget")
    # argparse rejects the removed flag: this is a usage error, not a bypass.
    assert result.returncode != 0
    assert "unrecognized arguments" in result.stderr or "allow-over-budget" in result.stderr


# ---------------------------------------------------------------------------
# CLI surface
# ---------------------------------------------------------------------------


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SKILL_ROOT / "scripts" / "tla_spec_dev.py"), *args],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def test_analyze_complexity_is_reachable_through_the_cli(tmp_path: Path) -> None:
    tla, cfg, manifest = write_small_model(tmp_path, GENEROUS_BUDGETS)
    result = run_cli("analyze", "complexity", str(tla), str(cfg), "--manifest", str(manifest))
    assert result.returncode == EXIT_PASS, result.stderr
    assert "Dimension table" in result.stdout
    assert "SUGGESTED MOVE" not in result.stdout


def test_analyze_parent_command_reports_the_next_step() -> None:
    result = run_cli("analyze")
    assert result.returncode == 2
    assert "analyze complexity" in result.stderr


def test_cfg_defaults_to_mc_cfg_beside_the_module(tmp_path: Path) -> None:
    tla, _, manifest = write_small_model(tmp_path, GENEROUS_BUDGETS)
    result = run_cli("analyze", "complexity", str(tla), "--manifest", str(manifest))
    assert result.returncode == EXIT_PASS, result.stderr


# ---------------------------------------------------------------------------
# EXTENDS resolution (MF-030)
# ---------------------------------------------------------------------------
#
# The analyzer used to read one .tla file and stop at EXTENDS, so a decomposed
# model was scored on only the declarations literally present in that file.
# Because missing variables only ever shrink the product bound, the error was
# never conservative: the gate failed toward PASS. These tests measure a
# decomposed model where the EXTENDED module contributes a BOUNDED variable, so
# the fix is proved by the bound MOVING -- not merely by the model parsing.

# A base module that carries the bound. `tick` is constrained by TypeInvariant
# (cardinality 4); the extending module inherits both `tick` and TypeInvariant
# through EXTENDS. This mirrors MF-023's Internal/External split, where the
# extending view adds an unconstrained channel variable and inherits the whole
# of the bounded constraint from the module it extends.
BASE_COUNTER_TLA = """---------------------------- MODULE Counter ----------------------------
EXTENDS Naturals

VARIABLES tick

CounterInit == tick = 0

Bump ==
  /\\ tick < 3
  /\\ tick' = tick + 1

TypeInvariant == tick \\in 0..3
=============================================================================
"""

# The extending view. `emitted` is an unconstrained channel variable, exactly
# like MF-023's `lastCommand`/`result`: it adds ZERO to the bound, so the bound
# a correct resolver reports comes ENTIRELY from the extended module.
CHANNEL_TLA = """---------------------------- MODULE Channel ----------------------------
EXTENDS Counter

VARIABLES emitted

ChannelInit ==
  /\\ CounterInit
  /\\ emitted = "none"

Emit ==
  /\\ Bump
  /\\ emitted' = "bumped"

Next == Emit

TypeInvariantWholeModel ==
  /\\ TypeInvariant
  /\\ emitted \\in {"none", "bumped"}

Spec == ChannelInit /\\ [][Next]_<< tick, emitted >>
=============================================================================
"""

CHANNEL_CFG = """SPECIFICATION Spec

INVARIANTS
  TypeInvariant
"""


def write_decomposed_model(tmp_path: Path) -> tuple[Path, Path]:
    (tmp_path / "Counter.tla").write_text(BASE_COUNTER_TLA, encoding="utf-8")
    channel = tmp_path / "Channel.tla"
    channel.write_text(CHANNEL_TLA, encoding="utf-8")
    cfg = tmp_path / "MC.cfg"
    cfg.write_text(CHANNEL_CFG, encoding="utf-8")
    return channel, cfg


def test_extends_is_followed_and_the_bound_reflects_all_variables(tmp_path: Path) -> None:
    r"""The MF-030 regression. Measures the EXTENDING module, `Channel`.

    PRE-FIX behavior (analyzer reads Channel.tla only):
      * variables == ['emitted']              -- the 1 declared in this file
      * TypeInvariant is absent (it lives in  -- so nothing is bounded
        the extended Counter)
      * bound == 1                            -- product of 0 bounded dimensions
      * `Bump` is not an action               -- it is defined in Counter

    POST-FIX behavior (EXTENDS Counter followed):
      * variables == ['tick', 'emitted']      -- unioned across the hierarchy
      * TypeInvariant inherited from Counter  -- bounds `tick` at cardinality 4
      * bound == 4                            -- entirely from the extended module
      * `Bump` is an action                   -- its declaration is included

    Every assertion below is one PRE-FIX would fail: the bound moves 1 -> 4, the
    extended variable and the extended action appear. That is what makes this a
    regression rather than a test that passes both before and after.
    """
    channel, cfg = write_decomposed_model(tmp_path)
    result = analyze(channel, cfg, None)

    # All variables from the whole hierarchy, not just this file's.
    assert set(result.variables) == {"tick", "emitted"}

    # The bound reflects the extended module's bounded variable. Pre-fix this
    # was 1 (the extending file carries no TypeInvariant of its own).
    assert result.bound == 4
    cardinalities = {d.variable: d.cardinality for d in result.dimensions}
    assert cardinalities["tick"] == 4
    # The channel variable stays honestly unbounded and adds nothing -- so the
    # whole of the bound provably came from across the EXTENDS edge.
    assert "emitted" in result.unbounded

    # The extended module's content is included: `Next == Emit`, and Emit calls
    # the extended `Bump`, so Emit's write set carries `tick` from across the
    # EXTENDS edge. (CD-06 updated this assertion: `Bump` itself is a called
    # operator, not a Next disjunct, so it is attributed INTO `Emit` rather
    # than listed as an action of its own.)
    by_name = {a.name: a for a in result.actions}
    assert list(by_name) == ["Emit"]
    assert by_name["Emit"].writes == {"tick", "emitted"}


def test_resolve_module_unions_a_three_level_hierarchy(tmp_path: Path) -> None:
    """Core <- Internal <- External, the shape SKILL.md mandates."""
    (tmp_path / "Root.tla").write_text(
        "---- MODULE Root ----\nEXTENDS Naturals\nVARIABLES a\n"
        "TypeInvariant == a \\in 0..1\n====\n",
        encoding="utf-8",
    )
    (tmp_path / "Mid.tla").write_text(
        "---- MODULE Mid ----\nEXTENDS Root\nVARIABLES b\n"
        "MidInv == b \\in 0..1\n====\n",
        encoding="utf-8",
    )
    (tmp_path / "Leaf.tla").write_text(
        "---- MODULE Leaf ----\nEXTENDS Mid\nVARIABLES c\n"
        "LeafInv == c \\in 0..1\n====\n",
        encoding="utf-8",
    )
    resolved = resolve_module(tmp_path / "Leaf.tla")
    assert resolved.root == "Leaf"
    assert resolved.modules == ["Root", "Mid", "Leaf"]
    assert set(resolved.variables) == {"a", "b", "c"}
    # TypeInvariant, defined only in Root, is reachable from the leaf's view.
    assert "TypeInvariant" in {d.name for d in resolved.defs}


def test_extends_of_standard_library_modules_needs_no_file(tmp_path: Path) -> None:
    """EXTENDS Naturals/FiniteSets/TLC must not demand a Naturals.tla."""
    tla = tmp_path / "Solo.tla"
    tla.write_text(
        "---- MODULE Solo ----\nEXTENDS Naturals, FiniteSets, TLC\n"
        "VARIABLES n\nTypeInvariant == n \\in 0..2\n====\n",
        encoding="utf-8",
    )
    resolved = resolve_module(tla)
    assert resolved.variables == ["n"]
    assert resolved.modules == ["Solo"]


# --- Fail-closed on constructs the resolver cannot model --------------------


def test_instance_fails_closed_rather_than_under_reporting(tmp_path: Path) -> None:
    (tmp_path / "Base.tla").write_text(
        "---- MODULE Base ----\nEXTENDS Naturals\nVARIABLES x\n"
        "TypeInvariant == x \\in 0..3\n====\n",
        encoding="utf-8",
    )
    tla = tmp_path / "UsesInstance.tla"
    tla.write_text(
        "---- MODULE UsesInstance ----\nEXTENDS Naturals\nVARIABLES y\n"
        "B == INSTANCE Base\nTypeInvariant == y \\in 0..3\n====\n",
        encoding="utf-8",
    )
    with pytest.raises(UnsupportedModuleConstructError, match="INSTANCE"):
        resolve_module(tla)


def test_local_fails_closed_rather_than_under_reporting(tmp_path: Path) -> None:
    tla = tmp_path / "UsesLocal.tla"
    tla.write_text(
        "---- MODULE UsesLocal ----\nEXTENDS Naturals\nVARIABLES w\n"
        "LOCAL Helper == 1\nTypeInvariant == w \\in 0..3\n====\n",
        encoding="utf-8",
    )
    with pytest.raises(UnsupportedModuleConstructError, match="LOCAL"):
        resolve_module(tla)


def test_missing_extended_module_fails_closed(tmp_path: Path) -> None:
    tla = tmp_path / "Orphan.tla"
    tla.write_text(
        "---- MODULE Orphan ----\nEXTENDS Naturals, Missing\nVARIABLES z\n"
        "TypeInvariant == z \\in 0..3\n====\n",
        encoding="utf-8",
    )
    with pytest.raises(UnresolvedExtendsError, match="Missing"):
        resolve_module(tla)


def test_gate_report_fails_closed_on_an_unresolvable_hierarchy(tmp_path: Path) -> None:
    """The gate must REFUSE, not score the fragment it can read."""
    tla = tmp_path / "Orphan.tla"
    tla.write_text(
        "---- MODULE Orphan ----\nEXTENDS Naturals, Missing\nVARIABLES z\n"
        "TypeInvariant == z \\in 0..3\n====\n",
        encoding="utf-8",
    )
    cfg = tmp_path / "MC.cfg"
    cfg.write_text("SPECIFICATION Spec\nINVARIANTS TypeInvariant\n", encoding="utf-8")
    passed, message = gate_report(tla, cfg, None)
    assert passed is False
    assert "could not be resolved" in message
    assert "Missing" in message


def test_cli_fails_closed_nonzero_on_an_unresolvable_hierarchy(tmp_path: Path) -> None:
    tla = tmp_path / "UsesInstance.tla"
    tla.write_text(
        "---- MODULE UsesInstance ----\nEXTENDS Naturals\nVARIABLES y\n"
        "B == INSTANCE Base\nTypeInvariant == y \\in 0..3\n====\n",
        encoding="utf-8",
    )
    cfg = tmp_path / "MC.cfg"
    cfg.write_text("SPECIFICATION Spec\nINVARIANTS TypeInvariant\n", encoding="utf-8")
    assert main([str(tla), str(cfg)]) == EXIT_BUDGET_EXCEEDED


# ---------------------------------------------------------------------------
# CD-06 (VAL-07 / VAL-12): the R/W matrix is attributed to the top-level
# actions -- the Next/ExternalNext disjuncts -- through called operators.
# Helpers are not actions.
# ---------------------------------------------------------------------------

# The VAL-07 shape (taskq): wrapper CLI actions prime `lastCli` only through
# the helper `MarkCli`, and `ListTasks` primes NOTHING directly. The primes
# heuristic dropped every such wrapper (9 CLI actions collapsed to 4 columns)
# and listed the helper as an action.
VAL07_TLA = """---- MODULE Taskq ----
EXTENDS Naturals, FiniteSets

CONSTANTS Names

VARIABLES tasks, lastCli

vars == << tasks, lastCli >>

Init ==
  /\\ tasks = {}
  /\\ lastCli = "none"

MarkCli(cmd) ==
  lastCli' = cmd

AddTask(t) ==
  /\\ t \\notin tasks
  /\\ tasks' = tasks \\cup {t}
  /\\ MarkCli("add")

ListTasks ==
  /\\ UNCHANGED tasks
  /\\ MarkCli("list")

DoneTask(t) ==
  /\\ t \\in tasks
  /\\ tasks' = tasks \\ {t}
  /\\ MarkCli("done")

Next ==
  \\/ \\E t \\in Names : AddTask(t)
  \\/ ListTasks
  \\/ \\E t \\in Names : DoneTask(t)

TypeInvariant ==
  /\\ tasks \\subseteq Names

Spec == Init /\\ [][Next]_vars
====
"""

VAL07_CFG = """SPECIFICATION Spec

CONSTANTS
  Names = {n1, n2}

INVARIANTS
  TypeInvariant
"""


def _write_val07_model(tmp_path: Path) -> tuple[Path, Path]:
    tla = tmp_path / "Taskq.tla"
    cfg = tmp_path / "MC.cfg"
    tla.write_text(VAL07_TLA, encoding="utf-8")
    cfg.write_text(VAL07_CFG, encoding="utf-8")
    return tla, cfg


def test_val07_helper_primed_wrappers_are_columns_and_the_helper_is_not(
    tmp_path: Path,
) -> None:
    """VAL-07: every Next disjunct gets a column; the helper gets none.

    Pre-fix this fails twice over: `ListTasks` (which primes a variable ONLY
    through `MarkCli`) vanished from the matrix, and `MarkCli` -- a helper, not
    an action -- was listed as a column.
    """
    tla, cfg = _write_val07_model(tmp_path)
    result = analyze(tla, cfg, None)
    names = [a.name for a in result.actions]
    assert names == ["AddTask", "ListTasks", "DoneTask"]
    assert "MarkCli" not in names
    by_name = {a.name: a for a in result.actions}
    # The wrapper's write through the helper is attributed to the wrapper.
    assert by_name["ListTasks"].writes == {"lastCli"}
    assert by_name["AddTask"].writes == {"tasks", "lastCli"}
    assert by_name["DoneTask"].writes == {"tasks", "lastCli"}
    # UNCHANGED tasks is not a touch for ListTasks.
    assert "tasks" not in by_name["ListTasks"].touched


def test_val07_dense_rows_action_count_and_fitness_facts_use_the_corrected_set(
    tmp_path: Path,
) -> None:
    """Dense rows and action_count are computed over the Next disjuncts.

    Pre-fix the action set was {MarkCli, AddTask, DoneTask}: `lastCli` showed
    touched by 1/3 (not dense) and the published action facts named a helper.
    Corrected: 3 actions (the disjuncts), `lastCli` touched by 3/3 and `tasks`
    by 2/3 -- both dense rows -- and the JSON facts the fitness rules consume
    list exactly the top-level actions.
    """
    from scripts.analyze_complexity import descriptor_payload

    tla, cfg = _write_val07_model(tmp_path)
    result = analyze(tla, cfg, None)
    assert len(result.actions) == 3
    assert result.dense_rows == {"lastCli": 3, "tasks": 2}
    payload = descriptor_payload(result)
    fact_actions = [a["name"] for a in payload["measured"]["actions"]]
    assert fact_actions == ["AddTask", "ListTasks", "DoneTask"]
    assert "disjuncts of the next-state relation Next" in payload["measured"][
        "action_attribution"
    ]


# The VAL-12 shape (distributed_history External): composed actions whose
# writes happen ENTIRELY through called operators or UNCHANGED got no column,
# while the helper doing the syntactic priming was listed as an action.
VAL12_TLA = """---- MODULE Composed ----
EXTENDS Naturals, Sequences

CONSTANTS Workers

VARIABLES queue, marker, log

vars == << queue, marker, log >>

InternalVars == << queue, log >>

Init ==
  /\\ queue = 0
  /\\ marker = "none"
  /\\ log = <<>>

Mark(name) ==
  marker' = name

Drain ==
  /\\ queue > 0
  /\\ queue' = 0
  /\\ log' = Append(log, queue)

RunWorker(w) ==
  /\\ w \\in Workers
  /\\ Drain
  /\\ Mark("run")

RunWorkerNoop(w) ==
  /\\ w \\in Workers
  /\\ queue = 0
  /\\ UNCHANGED InternalVars
  /\\ Mark("noop")

Next ==
  \\/ \\E w \\in Workers : RunWorker(w)
  \\/ \\E w \\in Workers : RunWorkerNoop(w)

TypeInvariant ==
  /\\ queue \\in 0..2

Spec == Init /\\ [][Next]_vars
====
"""

VAL12_CFG = """SPECIFICATION Spec

CONSTANTS
  Workers = {w1}

INVARIANTS
  TypeInvariant
"""


def test_val12_composed_actions_get_columns_and_helpers_do_not(tmp_path: Path) -> None:
    """VAL-12: writes only through called operators / UNCHANGED still earn columns.

    Pre-fix this fails in both directions: `RunWorker` and `RunWorkerNoop`
    (whose writes happen entirely inside `Drain`/`Mark` or under UNCHANGED)
    had NO column, while the helpers `Mark` and `Drain` were listed AS actions.
    """
    tla = tmp_path / "Composed.tla"
    cfg = tmp_path / "MC.cfg"
    tla.write_text(VAL12_TLA, encoding="utf-8")
    cfg.write_text(VAL12_CFG, encoding="utf-8")
    result = analyze(tla, cfg, None)
    names = [a.name for a in result.actions]
    assert names == ["RunWorker", "RunWorkerNoop"]
    assert "Mark" not in names
    assert "Drain" not in names
    by_name = {a.name: a for a in result.actions}
    assert by_name["RunWorker"].writes == {"queue", "log", "marker"}
    # The noop writes only through the helper; UNCHANGED InternalVars neither
    # counts as a touch nor drags the tuple definition in as phantom reads.
    assert by_name["RunWorkerNoop"].writes == {"marker"}
    assert "log" not in by_name["RunWorkerNoop"].touched
    # `queue = 0` is a genuine guard read.
    assert "queue" in by_name["RunWorkerNoop"].reads


def test_cd06_real_distributed_history_external_matrix_lists_the_next_disjuncts() -> None:
    """The acceptance surface: the shipped example's External view, corrected.

    The matrix columns are exactly the twelve ExternalNext disjuncts --
    RunFulfillmentWorker, RunFulfillmentWorkerNoop, and HiddenInternalProgress
    present; the helper MarkExternal absent (VAL-12's recorded defect).
    """
    tla = REPO_ROOT / "examples" / "distributed_history" / "specs" / "program_model" / "External.tla"
    cfg = REPO_ROOT / "examples" / "distributed_history" / "specs" / "program_model" / "External.cfg"
    if not tla.is_file():
        return
    result = analyze(tla, cfg, None)
    names = [a.name for a in result.actions]
    assert names == [
        "SubmitCreateAccount",
        "SubmitDuplicateCreateAccount",
        "SubmitAddCartItem",
        "SubmitDuplicateAddCartItem",
        "SubmitAddCartItemMissingAccount",
        "SubmitCheckout",
        "SubmitCheckoutMissingAccount",
        "SubmitCheckoutEmptyCart",
        "SubmitDuplicateCheckout",
        "RunFulfillmentWorker",
        "RunFulfillmentWorkerNoop",
        "HiddenInternalProgress",
    ]
    assert "MarkExternal" not in names
    by_name = {a.name: a for a in result.actions}
    # RunFulfillmentWorker's writes arrive entirely through ProjectAllOutbox
    # and MarkExternal; responses is UNCHANGED and stays untouched.
    assert by_name["RunFulfillmentWorker"].writes == {
        "outbox",
        "projections",
        "lastInternalAction",
        "lastServiceRoute",
        "lastExternalAction",
    }
    assert "responses" not in by_name["RunFulfillmentWorker"].touched
    # HiddenInternalProgress steps InternalNext and leaves every external
    # variable alone.
    assert "responses" not in by_name["HiddenInternalProgress"].touched
    assert "accounts" in by_name["HiddenInternalProgress"].writes


def test_cd06_string_literals_are_data_not_operator_calls(tmp_path: Path) -> None:
    """A string spelling an operator name must not expand that operator.

    `result' = Mk("Other")` names the follow-up command as DATA; expanding the
    `Other` definition into the caller would attribute Other's reads/writes to
    it (found live on this repository's own model: "RecordBudgets" as a string
    argument dragged RecordBudgets' spec_root read into ScaffoldProject).
    """
    tla = tmp_path / "Strings.tla"
    cfg = tmp_path / "MC.cfg"
    tla.write_text(
        """---- MODULE Strings ----
EXTENDS Naturals

VARIABLES phase, note

vars == << phase, note >>

Init == phase = 0 /\\ note = "none"

Mk(t) == note' = t

Other ==
  /\\ phase > 1
  /\\ phase' = phase + 1
  /\\ Mk("other")

First ==
  /\\ phase = 0
  /\\ phase' = 1
  /\\ Mk("Other")

Next ==
  \\/ First
  \\/ Other

TypeInvariant == phase \\in 0..3

Spec == Init /\\ [][Next]_vars
====
""",
        encoding="utf-8",
    )
    cfg.write_text("SPECIFICATION Spec\n\nINVARIANTS\n  TypeInvariant\n", encoding="utf-8")
    result = analyze(tla, cfg, None)
    by_name = {a.name: a for a in result.actions}
    # `First` writes phase directly and note through Mk. The "Other" STRING
    # must not import Other's guard read of phase>1... phase is read anyway
    # via its own guard; the discriminating fact is the write set.
    assert by_name["First"].writes == {"phase", "note"}


def test_cd06_next_found_through_specification_and_through_cfg_next(tmp_path: Path) -> None:
    tla, cfg = _write_val07_model(tmp_path)
    text = tla.read_text(encoding="utf-8")
    from scripts.analyze_complexity import parse_definitions as _parse

    from scripts.analyze_complexity import strip_comments

    defs = {d.name: d for d in _parse(strip_comments(text))}
    # SPECIFICATION Spec resolves through `[][Next]_vars`.
    assert find_next_relation("SPECIFICATION Spec\n", defs) == "Next"
    # An explicit NEXT entry wins directly.
    assert find_next_relation("INIT Init\nNEXT Next\n", defs) == "Next"
    # Nothing found -> None (caller falls back and says so).
    assert find_next_relation("INVARIANTS\n  TypeInvariant\n", defs) is None


def test_cd06_fallback_without_a_next_relation_is_stated_honestly(tmp_path: Path) -> None:
    """No NEXT/SPECIFICATION in the cfg: the primes heuristic is used AND named."""
    tla, cfg = _write_val07_model(tmp_path)
    cfg.write_text("INVARIANTS\n  TypeInvariant\n", encoding="utf-8")
    result = analyze(tla, cfg, None)
    assert "FALLBACK primes heuristic" in result.action_attribution
    # The old (wrong) attribution is what the fallback produces -- stated, not
    # hidden: the helper appears and the prime-less wrapper is missing.
    names = [a.name for a in result.actions]
    assert "MarkCli" in names
    assert "ListTasks" not in names


def test_cd06_split_top_level_disjuncts_respects_nesting() -> None:
    body = (
        "\n  \\/ \\E t \\in {a, b} : AddTask(t)"
        "\n  \\/ ListTasks"
        "\n  \\/ Choose(<<1, 2>>, {x \\in S : x > 0})"
    )
    parts = split_top_level_disjuncts(body)
    assert len(parts) == 3
    assert parts[1] == "ListTasks"
    # A `\/` inside parentheses is not a top-level boundary.
    nested = "A(x \\/ y) \\/ B"
    assert split_top_level_disjuncts(nested) == ["A(x \\/ y)", "B"]


def test_cd06_repeated_and_inline_disjuncts(tmp_path: Path) -> None:
    """One column per action even when quantified twice; inline disjuncts kept."""
    module = (
        "---- MODULE Dup ----\n"
        "VARIABLES x\n"
        "Op(v) == x' = v\n"
        "Next ==\n"
        "  \\/ \\E v \\in {1} : Op(v)\n"
        "  \\/ \\E v \\in {2} : Op(v)\n"
        "  \\/ x' = 0 /\\ x > 1\n"
        "====\n"
    )
    defs = {d.name: d for d in parse_definitions(module)}
    actions = extract_next_actions("Next", defs, ["x"])
    names = [a.name for a in actions]
    assert names == ["Op", "Next[3]"]
    inline = {a.name: a for a in actions}["Next[3]"]
    assert inline.writes == {"x"}
    assert inline.reads == {"x"}


# ---------------------------------------------------------------------------
# CD-07 (CD-02-DF-01): the no-manifest warning says what happened -- it never
# leaks the internal Path("does-not-exist") sentinel into user-facing output.
# ---------------------------------------------------------------------------


def test_no_manifest_warning_names_no_sentinel_path(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    tla, cfg, _ = write_small_model(tmp_path)
    analyze(tla, cfg, None)
    err = capsys.readouterr().err
    assert "does-not-exist" not in err
    assert "no manifest supplied" in err
    assert "documented default budgets" in err
