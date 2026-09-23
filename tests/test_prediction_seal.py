"""A prediction is only a prediction if the sealer has not already measured it.

PA-06-DF-03: `PREDICTIONS-PA.md`'s **N05** predicted that ordering stays at zero
on every generated corpus. A kill table that PRE-DATES the seal -- and is an
ancestor of the very commit that sealed the file -- records
`M09-negative-control-ledger-order / corpus-whole = KILLED`, and
`examples/validation/ab/eval/controls.toml` had already RETIRED M09 as a negative
control, saying in the retirement text that it dies under exactly those corpora.
N05 was scored FAIL. Nobody had to run anything to know it would be.

The demonstrated failing input (R1) is therefore the real record: the checker
must report N05, and must report nothing once N05's own section is removed, so
the red is attributable to the row rather than to the file.

R2 note: the checker's job is to be ABLE to say "not sealable". These tests
assert both directions -- it goes red on N05 and green on a prediction whose
subject nothing has measured -- because a seal check that always passes is worse
than no seal check.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
VALIDATION = REPO_ROOT / "examples" / "validation"
for _p in (str(REPO_ROOT), str(VALIDATION)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import check_prediction_seal as seal  # noqa: E402

PREDICTIONS_PA = VALIDATION / "PREDICTIONS-PA.md"
PA03_TABLE = (
    REPO_ROOT / "specs" / ".history" / "hexagonal-prompting-epic" / "ticket-002-HP-03"
    / "results" / "kill-table-hp01.json"
)


# ---------------------------------------------------------------------------
# R1 -- the demonstrated failing input, from the record
# ---------------------------------------------------------------------------


def test_the_demonstration_passes() -> None:
    failures = seal.demonstrate(verbose=False)
    assert failures == [], failures


def test_n05_is_reported_against_the_real_record() -> None:
    rows = seal.check(PREDICTIONS_PA, seal.default_records(), verbose=False)
    already = [r for r in rows if r.kind == "ALREADY MEASURED"]
    assert [r.prediction for r in already] == ["N05"], (
        f"expected exactly the row PA-06-DF-03 was filed about; got "
        f"{[(r.kind, r.prediction) for r in rows]}"
    )
    detail = already[0].detail
    assert "M09-negative-control-ledger-order / corpus-whole = KILLED" in detail
    assert "RETIRED as a negative control" in detail


def test_the_demonstration_is_runnable_from_the_command_line() -> None:
    proc = subprocess.run(
        [sys.executable, str(VALIDATION / "check_prediction_seal.py"), "--demonstrate"],
        capture_output=True, text=True, check=False, cwd=str(REPO_ROOT),
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "R1 holds for this instrument" in proc.stdout


def test_the_cli_exits_nonzero_on_the_sealed_file() -> None:
    proc = subprocess.run(
        [sys.executable, str(VALIDATION / "check_prediction_seal.py"), str(PREDICTIONS_PA)],
        capture_output=True, text=True, check=False, cwd=str(REPO_ROOT),
    )
    assert proc.returncode == 1
    assert "NOT SEALABLE AS WRITTEN" in proc.stdout


# ---------------------------------------------------------------------------
# the other direction -- it must be able to report clean, and to be told
# ---------------------------------------------------------------------------


def _write(tmp_path: Path, body: str) -> Path:
    path = tmp_path / "PREDICTIONS-X.md"
    path.write_text("# predictions\n\n" + body, encoding="utf-8")
    return path


def test_a_prediction_about_an_unmeasured_subject_is_clean(tmp_path: Path) -> None:
    path = _write(tmp_path, (
        "### N99 — a mutant nobody has run\n"
        "**Instrument:** M99 under `corpus-whole`.\n"
        "**Direction:** FLAT at zero.\n"
    ))
    rows = seal.check(path, [PA03_TABLE], verbose=False)
    assert [r.kind for r in rows] == [], rows


def test_a_declared_retest_is_reported_as_one_not_as_a_defect(tmp_path: Path) -> None:
    """PA-06-DF-03's suggested_fix: "or, if it is sealed deliberately as a
    re-test, say so in the row"."""

    path = _write(tmp_path, (
        "### N98 — ordering, re-tested on purpose\n"
        "**Instrument:** M09 under `corpus-whole`.\n"
        "**Direction:** FLAT at zero.\n"
        "**Already measured:** HP-03 killed it; re-sealed to test the new corpus.\n"
    ))
    rows = seal.check(path, [PA03_TABLE], verbose=False)
    kinds = {r.kind for r in rows}
    assert "ALREADY MEASURED" not in kinds
    assert "RE-TEST" in kinds
    assert "re-sealed to test the new corpus" in next(
        r.detail for r in rows if r.kind == "RE-TEST"
    )


def test_an_undeclared_repeat_of_the_same_row_is_reported(tmp_path: Path) -> None:
    """The same row WITHOUT the declaration must go red -- otherwise the escape
    hatch is not an escape hatch, it is the default."""

    path = _write(tmp_path, (
        "### N98 — ordering\n"
        "**Instrument:** M09 under `corpus-whole`.\n"
        "**Direction:** FLAT at zero.\n"
    ))
    rows = seal.check(path, [PA03_TABLE], verbose=False)
    assert any(r.kind == "ALREADY MEASURED" for r in rows), rows


def test_a_prediction_that_something_DIES_is_not_checked(tmp_path: Path) -> None:
    """P04 predicts both positive controls die everywhere. A kill in the record
    agrees with it; reading its commentary as a no-kill direction was a real
    misparse in this checker's first draft."""

    path = _write(tmp_path, (
        "### P04 — both positive controls die everywhere\n"
        "**Instrument:** M09 under `corpus-whole`, every arm.\n"
        "**Direction:** killed, 100%.\n"
        "If either survives, every number in its tree is void.\n"
    ))
    rows = seal.check(path, [PA03_TABLE], verbose=False)
    assert rows == [], rows


def test_a_kill_measured_AFTER_the_seal_is_not_a_sealing_defect(tmp_path: Path) -> None:
    """An ordinary falsification is what a predictions file is FOR."""

    path = _write(tmp_path, (
        "### N97 — ordering\n"
        "**Instrument:** M09 under `corpus-whole`.\n"
        "**Direction:** FLAT at zero.\n"
    ))
    # An uncommitted file has no sealing commit, so no record can pre-date it.
    rows = seal.check(path, [PA03_TABLE], seal.DEFAULT_CONTROLS.with_name("absent.toml"),
                      verbose=False)
    assert {r.kind for r in rows} == {"LATER"}, rows


def test_a_subject_that_cannot_be_looked_up_is_UNPARSED_not_clean(tmp_path: Path) -> None:
    """Silence and a pass are different claims."""

    path = _write(tmp_path, (
        "### N96 — something vague\n"
        "**Instrument:** the judges' scorecard.\n"
        "**Direction:** FLAT at zero.\n"
    ))
    rows = seal.check(path, [PA03_TABLE], verbose=False)
    assert [r.kind for r in rows] == ["UNPARSED"], rows
    assert "silence here is not a pass" in rows[0].detail


# ---------------------------------------------------------------------------
# the parsing rules, which are where the false positives live
# ---------------------------------------------------------------------------


def test_subjects_come_from_the_instrument_field_not_the_prose(tmp_path: Path) -> None:
    """N05's prose names `suite` in order to EXCLUDE it: "the hand-written suite
    DOES kill M09". A checker reading the whole section would report the row for
    the one thing it got right."""

    path = _write(tmp_path, (
        "### N95 — ordering\n"
        "**Instrument:** M09 under `corpus-neg`.\n"
        "**Direction:** FLAT at zero for every corpus instrument.\n"
        "Stated up front: the hand-written `suite` DOES kill M09.\n"
    ))
    rows = seal.check(path, [PA03_TABLE], seal.DEFAULT_CONTROLS.with_name("absent.toml"),
                      verbose=False)
    assert rows == [], (
        f"`suite` was read as a subject even though only `corpus-neg` was named as the "
        f"instrument: {rows}"
    )


def test_a_prediction_id_that_collides_with_a_mutant_id_is_not_a_subject() -> None:
    """This project's prediction ids (`N05`) and its mutant ids
    (`N01-negative-control-...`) share a namespace. A collision is dropped from
    the subjects rather than silently resolved either way."""

    preds = seal.parse_predictions(PREDICTIONS_PA.read_text(encoding="utf-8"))
    seal.attach_subjects(preds, {"corpus-whole", "suite"})
    ids = {p.id for p in preds}
    assert "N05" in ids and "N01" in ids
    for pred in preds:
        assert not (pred.mutants & ids), (
            f"{pred.id} claims another prediction's id as a mutant: {pred.mutants & ids}"
        )


def test_a_family_prefix_reaches_its_columns() -> None:
    """N05 names `corpus-slice`; the records carry `corpus-slice-led` and
    `corpus-slice-res`. Exact matching alone would miss the row."""

    preds = {p.id: p for p in seal.parse_predictions(
        PREDICTIONS_PA.read_text(encoding="utf-8"))}
    seal.attach_subjects(list(preds.values()),
                         {"corpus-slice-led", "corpus-slice-res", "corpus-whole"})
    assert {"corpus-slice-led", "corpus-slice-res", "corpus-whole"} <= preds["N05"].instruments


#: Trees under the repo root that are not the repo's source: build output and
#: the per-checkout agent homes `wt new` creates.
NOT_THIS_REPO = {"build", ".skill-manager", ".claude", ".codex", ".gemini"}


def test_the_checker_gates_nothing_in_the_toolchain() -> None:
    """No new gates. Nothing invokes this; its exit code is for the human
    sealing the file."""

    consumers = []
    for tree in ("skills/spec-double-2/scripts", "skills/spec-double-2/skill-scripts",
                 "skills/spec-double-2/spec_double_compiler", "skills/spec-double-2/templates",
                 "test_graph"):
        root = REPO_ROOT / tree
        if not root.exists():
            continue
        for path in root.rglob("*.py"):
            # Not this repository: per-checkout agent homes and `test_graph`
            # build output both carry whole COPIES of the plugin -- including a
            # copy of this very file, whose text names the checker. Scanning
            # them reported 72 "consumers" of a checker nothing consumes
            # (SI-27), the same shape as HP-01-DF-01. Pruned by name because
            # these trees are gitignored, so a plain clone has none and the
            # walk looks correct until a ticket agent runs the graphs first.
            if NOT_THIS_REPO.intersection(path.parts):
                continue
            if "check_prediction_seal" in path.read_text(encoding="utf-8", errors="ignore"):
                consumers.append(str(path.relative_to(REPO_ROOT)))
    assert consumers == [], consumers
