"""The disposition requirement, pinned by its own demonstration.

`CA-05`. The rule is `references/consumption.md`; the instrument is
`scripts/disposition.py`. **This is not a gate on anyone's code** -- it reads
this repository's own findings ledger and nothing else. Seven epics of static
checking caught zero bugs and this epic adds no gate.

Every slice below is SELECTED FROM THE REAL LEDGER AT RUN TIME rather than
hardcoded, so nothing here is fitted to a known answer (`MF-020`). If the
backlog is ever fully disposed -- the outcome the whole programme wants -- the
refusal test skips and says so instead of failing.
"""
from __future__ import annotations

import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts import disposition as D  # noqa: E402

LEDGER = ROOT / D.LEDGER


def ledger_path() -> pathlib.Path:
    """The one address every read below goes through. See `rows`.

    BS-08: while an epic is OPEN, `desired_program_model/deferred_findings.yaml`
    exists and is that epic's fresh inbox -- `findings: []` on bug-sweep's
    branch -- so `resolve_ledger` returned it and `load` refused "0 of 0",
    erroring all eight tests on every epic branch. These tests are about the
    SEALED ledger (real slices, more than 200 rows), so an empty live inbox
    falls through to the archive exactly as an absent one does.
    """
    path = D.resolve_ledger(LEDGER, explicit=False)
    if path == LEDGER:
        rows, _faults = D.read_rows(path)
        if not rows:
            archives = D.archived_ledgers(ROOT)
            if archives:
                return archives[-1]
    return path


@pytest.fixture(scope="module")
def rows() -> list[dict]:
    """`CA-10-DF-06`. Resolve exactly as the script does, then load.

    This fixture used to call `D.load(LEDGER)` directly. `LEDGER` is inside
    `desired_program_model/`, which the workflow close REMOVES, so all eight
    tests below errored the moment the epic was actually closed -- `CA-09` gave
    the SCRIPT a read fallback and left the SUITE without one. Going through
    `resolve_ledger` means the demonstration reads the archived copy after a
    close for the same reason and by the same rule the instrument does, rather
    than being a second, more fragile opinion about where the ledger lives.
    """
    return D.load(ledger_path())


def test_the_real_ledger_loads_and_is_not_empty(rows):
    """`load` refuses a ledger with no findings rather than reporting 0 of 0.

    `CA-00-DF-01` destroyed this file once by writing `findings: []`; a checker
    that reported a clean 0-of-0 over the wreckage would have been worse than
    no checker.
    """
    assert len(rows) > 200
    assert all("id" in r for r in rows)


def test_every_row_carries_a_disposition_field(rows):
    """The FIELD has been on every row since before this ticket. What CA-05 adds
    is that `open` is no longer an acceptable value at close-out."""
    assert [r["id"] for r in rows if "disposition" not in r] == []


def test_it_refuses_a_real_slice_that_contains_an_undisposed_row(rows):
    """The `R1` half: a demonstrated refusal on a real input, not a fixture."""
    epics = sorted({D.epic_of(r) for r in rows})
    refused = [e for e in epics
               if any(D.violations(r) for r in rows if D.epic_of(r) == e)]
    if not refused:
        pytest.skip("every epic in the ledger is disposed -- the backlog is "
                    "clear and this demonstration has nothing left to refuse")
    for e in refused:
        sl = [r for r in rows if D.epic_of(r) == e]
        assert D.report(sl, e, False) == 1


def test_it_accepts_a_real_slice_whose_rows_are_all_disposed(rows):
    """The half that stops the rule being a constant.

    An instrument that refuses everything is the mirror of harvest class `D1` --
    a cell that is a floor rather than a measurement. At least one REAL slice of
    the sealed record must pass, or the rule carries no information.
    """
    epics = sorted({D.epic_of(r) for r in rows})
    passed = [e for e in epics
              if not any(D.violations(r) for r in rows if D.epic_of(r) == e)]
    assert passed, (
        "no epic in the ledger passes all three clauses -- the rule has become "
        "a constant and is no longer measuring anything"
    )
    for e in passed:
        sl = [r for r in rows if D.epic_of(r) == e]
        assert D.report(sl, e, False) == 0


def test_the_ticket_that_shipped_the_rule_obeys_it(rows):
    """`CA-05` disposed its own findings. A ticket that ships a requirement it
    does not meet is asking everyone else to go first."""
    mine = [r for r in rows if str(r["id"]).startswith("CA-05-")]
    assert mine, "CA-05 filed no findings -- which would itself be suspicious"
    assert [(r["id"], D.violations(r)) for r in mine if D.violations(r)] == []


# -- the three clauses, each shown to be able to fail ----------------------

def test_d1_refuses_open_and_refuses_a_word_outside_the_vocabulary():
    assert D.violations({"id": "X", "disposition": "open"})
    assert D.violations({"id": "X", "disposition": "handled"})
    assert D.violations({"id": "X"})


def test_d2_refuses_a_terminal_disposition_with_no_note():
    for word in sorted(D.TERMINAL):
        assert D.violations({"id": "X", "disposition": word})
        assert not D.violations({"id": "X", "disposition": word,
                                 "disposition_note": "what was done"})


def test_d3_refuses_a_deferral_that_names_no_successor():
    assert D.violations({"id": "X", "disposition": "carried"})
    assert not D.violations({"id": "X", "disposition": "carried",
                             "disposition_ticket": "#262"})


def test_whitespace_does_not_satisfy_a_clause():
    """`disposition_note: "   "` is not a record of what was done."""
    assert D.violations({"id": "X", "disposition": "wontfix", "disposition_note": "   "})
    assert D.violations({"id": "X", "disposition": "carried", "disposition_ticket": ""})


def test_the_vocabularies_do_not_overlap_and_exclude_open():
    assert not (D.TERMINAL & D.DEFERRAL)
    assert "open" not in D.TERMINAL | D.DEFERRAL


# -- the declared blind spot, demonstrated rather than asserted -----------

def test_self_routing_passes_d3_and_this_ticket_does_it(rows):
    """`CA-05-DF-03`, WIDENED after review. The dead case, kept executable.

    The first version of this test used `falsifiable-instruments` carrying rows
    to issues that closed the next day. The reviewer was right that that is the
    NORMAL signature of an epic closing, not a dead handoff. **The dead case is
    self-routing** -- an epic deferring a finding to its own ticket, which routes
    it precisely nowhere and passes D3 with full marks.

    **And this ticket does it.** All three of `CA-05`'s `carried` rows name
    `#262`, which is `CA-08`, *this epic's own evaluation ticket*. That is the
    right place for those findings to surface AND it is still self-routing, and
    the rule cannot tell the difference. Declared, rather than quietly re-pointed
    at an issue invented to look external.
    """
    same = {"id": "CA-05-DF-99", "disposition": "carried",
            "disposition_ticket": "https://github.com/haydenrear/tla-spec-dev/issues/262"}
    other = {"id": "CA-05-DF-98", "disposition": "carried",
             "disposition_ticket": "https://github.com/haydenrear/tla-spec-dev/issues/144"}
    assert D.violations(same) == D.violations(other) == [], (
        "D3 is satisfied identically by a successor inside the filing epic and "
        "one outside it -- that is the blindness, and it must stay visible"
    )

    mine = [r for r in rows if str(r["id"]).startswith("CA-05-")
            and r.get("disposition") == "carried"]
    assert mine, "CA-05 has no carried rows -- the example moved"
    assert all("262" in str(r.get("disposition_ticket")) for r in mine), (
        "CA-05's carried rows no longer point at CA-08; if they now name a "
        "successor outside this epic, update CA-05-DF-03 rather than this test"
    )


def test_a_successor_need_not_be_an_issue_or_resolve_to_anything():
    """Second face of `CA-05-DF-03`: `disposition_ticket` is any non-empty string.

    14 real rows name a bare ticket id (`PA-06`, `PA-01`) rather than a URL and
    pass. Nothing resolves the successor, so nothing distinguishes a live issue
    from a ticket that closed with the epic that named it.
    """
    assert D.violations({"id": "X", "disposition": "carried",
                         "disposition_ticket": "PA-06"}) == []
    assert D.violations({"id": "X", "disposition": "carried",
                         "disposition_ticket": "see the epic owner"}) == []


def test_a_deferral_needs_no_note_at_all(rows):
    """Third face of `CA-05-DF-03`: D2 binds terminal dispositions only.

    A `carried` row satisfies the rule with no `disposition_note` whatsoever,
    and real rows in the sealed ledger do exactly that.
    """
    assert D.violations({"id": "X", "disposition": "carried",
                         "disposition_ticket": "#1"}) == []
    noteless = [r["id"] for r in rows if r.get("disposition") == "carried"
                and not str(r.get("disposition_note") or "").strip()]
    assert noteless, "no noteless deferrals left -- retire this face of DF-03"


# -- the structural guard, on the real corruption that defeated the check --

def test_duplicate_keys_are_refused_structurally():
    """`CA-05-DF-06`. A clause verdict computed over silently-discarded input is
    not a verdict, so a duplicate key refuses BEFORE any clause is evaluated.

    This is the shape of the real fault: `#188` above the note, `#169` below it,
    and every YAML parser keeping the second without a word.
    """
    text = (
        "findings:\n"
        "  - id: X-01-DF-01\n"
        "    disposition: carried\n"
        '    disposition_ticket: "#188"\n'
        "    disposition_note: >-\n"
        "      carried to #188\n"
        '    disposition_ticket: "#169"\n'
    )
    assert [(r, k) for r, k, _ in D.duplicate_keys(text)] == [
        ("X-01-DF-01", "disposition_ticket")]


def test_the_real_ledger_has_no_duplicate_keys(rows):
    """Regression pin on the repair of `SM-05-DF-01`..`DF-07`.

    `load` already refuses on duplicates, so `rows` existing proves the file is
    clean; asserted explicitly so the reason is on the record rather than
    implicit in a fixture that happens to load.
    """
    assert D.duplicate_keys(ledger_path().read_text()) == []
    assert len(rows) > 200


# -- SI-04: the skill-change disposition, and the ONE reader of it ---------
#
# `improvement_ledger.py` reads the same backlog bytes this file's instrument
# reads. The tests below pin the two properties that keeps honest: that there
# is one parser rather than two, and that the new reader cannot refuse.

import subprocess  # noqa: E402

from scripts import improvement_ledger as L  # noqa: E402

LEDGER_SCRIPT = ROOT / "skills" / "spec-double-2" / "scripts" / "improvement_ledger.py"


def test_one_backlog_reader_not_two():
    """`SI-04`'s load-bearing constraint, asserted on identity of the source.

    The ledger could trivially have called `yaml.safe_load` itself. It does not,
    and this is what stops that regressing: both readers resolve to the same
    file on disk, so the duplicate-key guard `CA-05-DF-06` paid for cannot be
    true of one caller and false of the other.
    """
    assert L.D.__file__ == D.__file__
    assert L.D.read_rows is not None
    source = LEDGER_SCRIPT.read_text(encoding="utf-8")
    assert "safe_load" not in source, (
        "the ledger has grown its own YAML read -- that is the second reader "
        "SI-04 exists to prevent"
    )


def test_read_rows_reports_the_structural_fault_instead_of_raising(tmp_path):
    """The refactor that made one reader serve both callers.

    `load` refuses on a duplicate key; `read_rows` returns the same finding as
    text so an advisory caller can print it and carry on. Same detection, two
    responses, one implementation.
    """
    bad = tmp_path / "dup.yaml"
    bad.write_text(
        "findings:\n"
        "  - id: X-01-DF-01\n"
        "    disposition: carried\n"
        '    disposition_ticket: "#188"\n'
        '    disposition_ticket: "#169"\n',
        encoding="utf-8",
    )
    rows, faults = D.read_rows(bad)
    assert rows == []
    assert any("STRUCTURAL" in f and "disposition_ticket" in f for f in faults)

    with pytest.raises(SystemExit):
        D.load(bad)


def test_load_still_refuses_an_empty_ledger(tmp_path):
    empty = tmp_path / "empty.yaml"
    empty.write_text("findings: []\n", encoding="utf-8")
    rows, faults = D.read_rows(empty)
    assert rows == [] and faults
    with pytest.raises(SystemExit):
        D.load(empty)


# -- the grammar ----------------------------------------------------------


def test_every_verb_in_the_vocabulary_parses():
    assert L.parse_skill_change("none").verb == "none"
    assert L.parse_skill_change("applied(9f2c1ab)").args == ("9f2c1ab",)
    assert L.parse_skill_change("declined(not worth pinning)").verb == "declined"
    proposed = L.parse_skill_change("proposed(spec-double-2, #319)")
    assert proposed.verb == "proposed"
    assert proposed.unit == "spec-double-2"
    assert proposed.args == ("spec-double-2", "#319")


def test_absent_is_not_none():
    """`bug_attribution.md` §3. The distinction the whole field rests on.

    `none` is a claim that no skill change was needed. Absent is nobody having
    been asked. Collapsing them would report the entire pre-SI-04 record as
    having considered the question and answered no.
    """
    absent = L.parse_skill_change(None)
    assert absent.verb == "absent"
    assert not absent.recorded
    assert L.parse_skill_change("none").recorded
    assert absent != L.parse_skill_change("none")


def test_only_applied_and_declined_are_terminal():
    """D4 is satisfied by a change or a reasoned refusal -- not by a proposal."""
    assert L.parse_skill_change("applied(abc1234)").terminal
    assert L.parse_skill_change("declined(the path is being deleted)").terminal
    assert not L.parse_skill_change("proposed(spec-double-2, #319)").terminal
    assert not L.parse_skill_change("none").terminal
    assert not L.parse_skill_change(None).terminal


@pytest.mark.parametrize(
    "bad",
    ["applied", "proposed(spec-double-2)", "none(something)", "handled(x)",
     "applied()", "proposed(, #319)"],
)
def test_a_malformed_value_is_named_rather_than_silently_dropped(bad):
    """A value the reader cannot parse is reported, never treated as absent.

    Silently reading an unparseable field as "nothing recorded" is how a record
    that says something becomes a record that says nothing.
    """
    parsed = L.parse_skill_change(bad)
    assert parsed.verb == "malformed"
    assert parsed.raw == bad


# -- the reader, on the real record ---------------------------------------


def test_the_ledger_has_no_exit_path_at_all():
    """`GOAL-no-new-gates`, asserted structurally rather than promised.

    Not "it returns 0 on every branch we thought of" -- there is no branch that
    can return anything else, and this is what keeps it that way.
    """
    source = LEDGER_SCRIPT.read_text(encoding="utf-8")
    offenders = [line.strip() for line in source.splitlines()
                 if "sys.exit(" in line or "SystemExit" in line]
    assert offenders == [], f"the advisory reader grew a refusal path: {offenders}"


def test_the_ledger_exits_zero_on_this_repositorys_own_record():
    """R1: demonstrated on the real subject, not a fixture."""
    done = subprocess.run(
        [sys.executable, str(LEDGER_SCRIPT)],
        cwd=str(ROOT), capture_output=True, text=True,
    )
    assert done.returncode == 0, done.stderr
    assert "findings by disposition" in done.stdout
    assert "advisory" in done.stdout


def test_the_ledger_reads_all_four_record_files():
    """One reader, four files -- the unification SI-04 is for."""
    root = L.repo_root(str(ROOT))
    known = L.units_in(root)
    problems: list[str] = []
    records = L.read_skill_feedback(root / L.SKILL_FEEDBACK, known, problems)
    for backlog in L.BACKLOGS:
        records += L.read_backlog(root / backlog, known, problems)
    records += L.read_matrix(root / L.MATRIX, problems)

    sources = {r.source for r in records}
    assert len(sources) == 4, f"expected all four record files, got {sorted(sources)}"
    assert any(r.kind == "BIN" for r in records), "the matrix bins were not read"


def test_the_recorded_local_findings_are_visible_to_the_ledger():
    """The 13 stuck findings are the thing the goal is measured on.

    Asserted as "at least one", never as a count: the target is that this
    number reaches zero, and a test pinned to 13 would fail on success.
    """
    root = L.repo_root(str(ROOT))
    problems: list[str] = []
    records = L.read_skill_feedback(root / L.SKILL_FEEDBACK, L.units_in(root), problems)
    stuck = [r for r in records if r.stuck]
    if not stuck:
        pytest.skip("no recorded-local findings remain -- the goal is met and "
                    "this demonstration has nothing left to show")
    assert all(not r.skill_change.terminal for r in stuck), (
        "a finding can no longer be both `recorded-local` and consumed"
    )


def test_the_matrix_column_is_read_by_name_not_by_index():
    """Adding a column must not shift an existing reading by one.

    `CA-05-DF-06`'s class: a parser quietly reading a different value than the
    author wrote. The bins table gained a column in this ticket, and the
    disposition column must still be the disposition column.
    """
    root = L.repo_root(str(ROOT))
    records = L.read_matrix(root / L.MATRIX, [])
    dispositions = {r.disposition for r in records}
    assert dispositions <= {"modelable", "deferred", "record-only", "undecided"}, (
        f"the bins table's disposition column no longer parses: {dispositions}"
    )
    assert all(not r.skill_change.recorded for r in records), (
        "a bin now records a skill change -- update this test, it pinned the "
        "SI-04 baseline of seven absent cells"
    )
