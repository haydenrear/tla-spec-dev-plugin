"""Workflow close must not take the cumulative findings ledger with it.

THE SUBJECT IS THIS REPOSITORY, NOT A FIXTURE. Every test here copies the real
`specs/current`, `specs/desired_program_model`, `specs/program_model`, the real
`specs/.history/cut-the-apparatus-epic` receipts and the real
`specs/results/*` inputs into a throwaway directory and runs the real
`close_tickets.close_ticket_workflow` over them. A hand-built two-file spec tree
would not have reproduced either defect: both are about what the shipped close
does to the 267-row ledger this project actually carries.

WHAT WAS MEASURED BEFORE THE FIX (a real close, run and observed, not read off
the source):

  - The close DOES archive the ledger. `snapshot_models` copies all three model
    directories into `<entry>/snapshots/`, `copy_ignore` does NOT filter
    `deferred_findings.yaml` (it is not in `IGNORED_COPY_NAMES`), and the file
    landed complete -- all 267 rows -- at
    `closed-snapshot/snapshots/desired_program_model/deferred_findings.yaml`.
    The reports that the archive step was missing, and that `copy_ignore` was
    eating the file, were both WRONG.

  - The five closed-snapshots already in `specs/.history` lack the ledger
    because they PREDATE it living at that path, not because a close dropped it.
    The current ledger file was added at `e6d1351` (2026-08-05 13:25); the
    newest of the five, `hexagonal-prompting-epic`, was written 2026-08-05
    11:29.

  - What was actually broken is the READ. `scripts/disposition.py` addresses the
    ledger only at its live path, the close removes the directory containing it,
    and so `disposition.py --epic cut-the-apparatus` died with a bare
    `FileNotFoundError` traceback the moment the epic it reports on was closed.
    The record survived; nothing could reach it.

So the fix is an ADDRESS and a FALLBACK, never an exemption: the close still
removes `desired_program_model/`. `spec_evolution.snapshot_findings_ledger`
writes the ledger at the top of the history entry and names it in the manifest
under `findings_ledger`; `disposition.resolve_ledger` reads that archive when
the live path is gone, and says which copy it read.

The third test covers `SF-305` in `scripts/complexity_ledger.py`: a substring
test for the template sentinel over free prose, which blanked any narrative
merely QUOTING the word `TODO` and then refused the close for a narrative that
was `absent`.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

REPO = Path(__file__).resolve().parents[1]
SKILL_ROOT = REPO / "skills" / "spec-double-2"
sys.path.insert(0, str(REPO))

from scripts.close_tickets import close_ticket_workflow  # noqa: E402

WORKFLOW = "cut-the-apparatus-epic"
EPIC = "cut-the-apparatus"
LEDGER_NAME = "deferred_findings.yaml"
LIVE_LEDGER = Path("specs") / "desired_program_model" / LEDGER_NAME
DISPOSITION = SKILL_ROOT / "scripts" / "disposition.py"

#: `ticket-<index>-<TICKET-ID>[-<qualifier>]`.
#:
#: The epic history carries TWO successful receipts for CA-05 --
#: `ticket-004-CA-05` and, appended later, `ticket-004-CA-05-reconciled`, the
#: close retaken at the epic tip once CA-05's promotion predecessor had merged.
#: The workflow close refuses a ticket with two successful receipts, so the
#: subject keeps the LAST receipt per ticket id: the reconciled one, which is
#: the authoritative close. (Verified by running the close both ways -- either
#: single receipt satisfies it.) That duplicate is a pre-existing condition of
#: this record, is a genuine blocker for closing this epic for real, and is not
#: what these tests are about.
RECEIPT = re.compile(r"^ticket-\d+-([A-Za-z]+-\d+)(?:-.+)?$")


def _findings(path: Path) -> list[dict]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))["findings"]


def build_subject(dest: Path) -> Path:
    """Copy this repository's real spec workflow into `dest` and return it."""
    live_ledger = REPO / LIVE_LEDGER
    history = REPO / "specs" / ".history" / WORKFLOW
    if not live_ledger.exists() or not history.is_dir():
        pytest.skip(
            f"no open workflow to close: {LIVE_LEDGER} or specs/.history/{WORKFLOW} is absent "
            "(the epic these tests use as their subject has itself been closed)"
        )

    (dest / "specs" / ".history" / WORKFLOW).mkdir(parents=True)
    (dest / "specs" / "results").mkdir(parents=True)
    for name in ("current", "desired_program_model", "program_model"):
        shutil.copytree(REPO / "specs" / name, dest / "specs" / name)
    receipts: dict[str, Path] = {}
    for entry in sorted(history.iterdir()):
        if entry.is_dir() and (match := RECEIPT.match(entry.name)):
            receipts[match.group(1)] = entry  # sorted, so the last receipt wins
    for entry in receipts.values():
        shutil.copytree(entry, dest / "specs" / ".history" / WORKFLOW / entry.name)
    for result in sorted((REPO / "specs" / "results").iterdir()):
        if result.is_file():  # the close reads the ledger inputs; the raw sweep
            shutil.copy2(result, dest / "specs" / "results" / result.name)  # dirs are megabytes
    return dest


def close(root: Path) -> None:
    close_ticket_workflow(root, Path("specs"), dry_run=False, summary="R1 close over the real workflow")


def entry_dir(root: Path) -> Path:
    return root / "specs" / ".history" / WORKFLOW / "closed-snapshot"


def run_disposition(root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(DISPOSITION), "--epic", EPIC],
        cwd=root, capture_output=True, text=True,
    )


def test_the_close_archives_the_cumulative_ledger_where_a_reader_can_find_it(tmp_path: Path) -> None:
    root = build_subject(tmp_path / "subject")
    before = _findings(root / LIVE_LEDGER)
    # Not a per-epic backlog: one file, every epic's findings. Losing it is not
    # losing an epic's notes, it is losing the project's whole findings record.
    assert len({str(row["id"]).split("-")[0] for row in before}) > 1

    close(root)

    # The live path is REMOVED, as the close intends. This is not an exemption.
    assert not (root / "specs" / "desired_program_model").exists()

    archived = entry_dir(root) / LEDGER_NAME
    assert archived.exists(), (
        f"workflow close removed {LIVE_LEDGER} and left no ledger at {archived}; "
        f"present in the entry: {sorted(p.name for p in entry_dir(root).iterdir())}"
    )
    assert _findings(archived) == before

    manifest = json.loads((entry_dir(root) / "manifest.json").read_text(encoding="utf-8"))
    record = manifest["findings_ledger"]
    assert record["exists"] is True
    assert Path(record["snapshot"]).name == LEDGER_NAME
    assert LEDGER_NAME in (entry_dir(root) / "summary.md").read_text(encoding="utf-8")


def test_disposition_still_answers_after_the_workflow_it_reports_on_is_closed(tmp_path: Path) -> None:
    root = build_subject(tmp_path / "subject")
    before = run_disposition(root)
    assert before.returncode in {0, 1}, before.stderr

    close(root)

    after = run_disposition(root)
    assert "FileNotFoundError" not in after.stderr, (
        "disposition.py addresses the ledger only where the close just deleted it:\n" + after.stderr
    )
    assert after.returncode == before.returncode
    # Same verdict over the same rows -- the archive is the ledger, not a digest.
    assert after.stdout == before.stdout
    assert "archived ledger" in after.stderr  # and it says which copy it read


def test_a_narrative_that_quotes_the_template_sentinel_is_not_blanked(tmp_path: Path) -> None:
    """SF-305. Worst exactly where the ledger is most useful: writing about itself."""
    root = build_subject(tmp_path / "subject")
    ledger_input = root / "specs" / "results" / "complexity_ledger_input.yaml"
    document = yaml.safe_load(ledger_input.read_text(encoding="utf-8"))
    narrative = (
        "The scaffolded ledger template ships narrative: \"TODO\", and until SF-305 was "
        "fixed this very sentence could not be recorded: a substring test blanked any "
        "narrative quoting that word, and Gate 7 then refused the close as though no "
        "narrative had been written at all."
    )
    document["narrative"] = narrative
    ledger_input.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")

    close(root)  # before the fix: SystemExit, "REJECTED -- no `narrative:` recorded"

    written = json.loads((root / "specs" / "results" / "complexity_ledger.json").read_text(encoding="utf-8"))
    assert written["entries"][-1]["narrative"] == narrative


def test_an_unfilled_template_narrative_refuses_the_close_unless_forced(
    tmp_path: Path, capsys
) -> None:
    """#134 (BS-01): a rejected input refuses the close by name; --force records
    the rejection and closes. It used to proceed with one warning line, so the
    check had no teeth."""
    root = build_subject(tmp_path / "subject")
    ledger_input = root / "specs" / "results" / "complexity_ledger_input.yaml"
    document = yaml.safe_load(ledger_input.read_text(encoding="utf-8"))
    document["narrative"] = "TODO"
    ledger_input.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")

    with pytest.raises(SystemExit) as refused:
        close(root)
    assert "complexity ledger input is rejected" in str(refused.value)
    assert not entry_dir(root).exists()

    close_ticket_workflow(root, Path("specs"), dry_run=False, summary="forced", force=True)

    assert "complexity ledger input rejected" in capsys.readouterr().err
    assert entry_dir(root).is_dir()


def test_a_transition_diff_that_quotes_the_template_sentinel_is_not_blanked(tmp_path: Path) -> None:
    """SF-305's class, not SF-305's two instances.

    The first repair converted `narrative` and `justification` -- the two fields
    the finding named -- and left the identical substring test on
    `refinement.detail` and `transition_diff`, which are free prose too. That is
    a recogniser fitted to the reported instance (`MF-020`).

    `transition_diff` is the worse of the two, because it is load-bearing: with
    TLC red flags present the close is REFUSED when it is empty, so prose that
    mentions the sentinel is discarded and the close then fails naming the
    absence it caused.
    """
    root = build_subject(tmp_path / "subject")
    ledger_input = root / "specs" / "results" / "complexity_ledger_input.yaml"
    document = yaml.safe_load(ledger_input.read_text(encoding="utf-8"))
    diff = (
        'The template ships transition_diff: "TODO"; this entry explains which '
        "transitions moved and why, and before the class repair the substring "
        "test blanked it for quoting the word."
    )
    document["transition_diff"] = diff
    ledger_input.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")

    close(root)

    written = json.loads((root / "specs" / "results" / "complexity_ledger.json").read_text(encoding="utf-8"))
    assert written["entries"][-1]["transition_diff"] == diff


def test_an_unfilled_template_transition_diff_is_still_treated_as_absent(tmp_path: Path) -> None:
    """The property the substring test was protecting, kept under equality."""
    import sys

    # A PLAIN IMPORT. spec_from_file_location without registering the module in
    # sys.modules makes @dataclass die on sys.modules[cls.__module__].__dict__ --
    # the same trap the eval verifier hit, met a second time in one session.
    scripts = Path(__file__).resolve().parents[1] / "skills" / "spec-double-2" / "scripts"
    sys.path.insert(0, str(scripts))
    try:
        import complexity_ledger as module
    finally:
        sys.path.remove(str(scripts))
    assert module.is_unfilled_template_prose("TODO") is True
    assert module.is_unfilled_template_prose("TODO ".strip()) is True
    assert module.is_unfilled_template_prose('mentions "TODO" in passing') is False
