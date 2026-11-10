"""BS-01 (#187): close stops writing records nobody reads, and refuses wrong ones.

One regression test per covered issue, each red on the epic base and green on
the fix. The ticket-close cases drive the real CLI over a scaffolded project in
a temp dir; the workflow-close cases that need a real converged workflow live in
`test_workflow_close_keeps_the_ledger.py`, which already builds one.

- #187  a close without `--feedback` writes no per-ticket feedback stub
- #172  a ledger input written for another workflow is refused BY NAME (forceable)
- #134  a ledger input the ledger would reject refuses the close (forceable)
- #177  `attribution.yaml` is planning, not model
- #72   the backlog files do not break the retired-ticket exact-snapshot check
- #143  SF-007/009 a TLC report reaches the ledger; SF-042b design notes are
        archived; SF-045 an empty summary is recorded as `missing`
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from conftest import write_ticket_ledger_input

ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = ROOT / "skills" / "spec-double-2"
sys.path.insert(0, str(ROOT))

from scripts.close_tickets import (  # noqa: E402
    PLANNING_FILES,
    close_ticket_workflow,
    promote_semantic_files,
    validate_equivalent,
)

TICKET = "BS-900"
WORKFLOW = "desired-ticket-workflow"
SPECS = "project_specs"


def run_cli(*args: str, cwd: Path, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    import os

    full_env = {k: v for k, v in os.environ.items() if k not in {"SKILL_GATES", "TLA_SPEC_DEV_GATES"}}
    full_env.update(env or {})
    return subprocess.run(
        [sys.executable, str(SKILL_ROOT / "scripts" / "tla_spec_dev.py"), *args],
        cwd=cwd, text=True, capture_output=True, check=False, env=full_env,
    )


def open_ticket(tmp_path: Path, *, fill_ledger: bool = True) -> Path:
    for args in (
        ("scaffold", "project", "--name", "CloseRecords", "--full"),
        ("scaffold", "workflow", TICKET, "Close records"),
        ("open", "ticket", TICKET),
    ):
        result = run_cli("--spec-root", SPECS, *args, cwd=tmp_path)
        assert result.returncode == 0, result.stderr
    ticket_dir = tmp_path / SPECS / "tickets" / TICKET
    if fill_ledger:
        write_ticket_ledger_input(ticket_dir)
    plan = tmp_path / SPECS / "desired_program_model" / "ticket_plan.yaml"
    plan.write_text(plan.read_text(encoding="utf-8").replace("status: next", "status: done", 1), encoding="utf-8")
    return ticket_dir


def close(tmp_path: Path, *extra: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return run_cli("--spec-root", SPECS, "close", "ticket", TICKET, *extra, cwd=tmp_path, env=env)


def entry(tmp_path: Path) -> Path:
    return tmp_path / SPECS / ".history" / WORKFLOW / f"ticket-000-{TICKET}"


def feedback_doc(tmp_path: Path) -> Path:
    return tmp_path / SPECS / "results" / "skill_feedback.md"


# -- #187 -------------------------------------------------------------------


def test_187_close_without_feedback_writes_no_stub(tmp_path: Path) -> None:
    open_ticket(tmp_path)
    result = close(tmp_path, "--summary", "no feedback asked for")
    assert result.returncode == 0, result.stderr
    doc = feedback_doc(tmp_path)
    assert not doc.exists() or f"Close-out ticket {TICKET}" not in doc.read_text(encoding="utf-8")
    manifest = json.loads((entry(tmp_path) / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["skill_feedback"] is None


def test_187_close_with_feedback_still_writes_the_entry(tmp_path: Path) -> None:
    open_ticket(tmp_path)
    result = close(tmp_path, "--summary", "feedback asked for", "--feedback")
    assert result.returncode == 0, result.stderr
    assert f"Close-out ticket {TICKET}" in feedback_doc(tmp_path).read_text(encoding="utf-8")


# -- #172 -------------------------------------------------------------------


def _name_input_workflow(ticket_dir: Path, workflow: str) -> None:
    path = ticket_dir / "results" / "complexity_ledger.yaml"
    path.write_text(f"workflow: {workflow}\n" + path.read_text(encoding="utf-8"), encoding="utf-8")


def test_172_foreign_ledger_input_refuses_the_close_by_name(tmp_path: Path) -> None:
    ticket_dir = open_ticket(tmp_path)
    _name_input_workflow(ticket_dir, "cdc-polyglot-relation-mvp-workflow")

    result = close(tmp_path, "--summary", "foreign input")

    assert result.returncode != 0
    assert "cdc-polyglot-relation-mvp-workflow" in result.stderr
    assert ticket_dir.exists(), "a refused close must write nothing"
    assert not (tmp_path / SPECS / "results" / "complexity_ledger.json").exists()


def test_172_force_records_a_foreign_input_with_a_warning(tmp_path: Path) -> None:
    ticket_dir = open_ticket(tmp_path)
    _name_input_workflow(ticket_dir, "another-workflow")

    result = close(tmp_path, "--summary", "forced", env={"SKILL_GATES": "off"})

    assert result.returncode == 0, result.stderr
    assert "another-workflow" in result.stderr


def test_172_input_naming_this_workflow_closes(tmp_path: Path) -> None:
    ticket_dir = open_ticket(tmp_path)
    _name_input_workflow(ticket_dir, WORKFLOW)
    assert close(tmp_path, "--summary", "own input").returncode == 0


# -- #134 -------------------------------------------------------------------


def test_134_rejected_ledger_input_refuses_the_close(tmp_path: Path) -> None:
    ticket_dir = open_ticket(tmp_path, fill_ledger=False)  # the scaffolded TODO template

    result = close(tmp_path, "--summary", "unfilled ledger")

    assert result.returncode != 0
    assert "rejected" in result.stderr
    assert ticket_dir.exists()


def test_134_force_records_the_rejection_and_closes(tmp_path: Path) -> None:
    open_ticket(tmp_path, fill_ledger=False)

    result = close(tmp_path, "--summary", "forced past the ledger", "--force")

    assert result.returncode == 0, result.stderr
    ledger = json.loads((tmp_path / SPECS / "results" / "complexity_ledger.json").read_text(encoding="utf-8"))
    assert ledger["entries"][-1]["verdict"] == "rejected"


def test_134_absent_ledger_input_never_blocks(tmp_path: Path) -> None:
    ticket_dir = open_ticket(tmp_path)
    (ticket_dir / "results" / "complexity_ledger.yaml").unlink()
    assert close(tmp_path, "--summary", "no input at all").returncode == 0


# -- #143 -------------------------------------------------------------------

TLC_OUTPUT = (
    "Model checking completed. No error has been found.\n"
    "5619356 states generated, 231621 distinct states found, 0 states left on queue.\n"
    "The depth of the complete state graph search is 25.\n"
)


def test_143_sf007_tlc_report_reaches_the_complexity_ledger(tmp_path: Path) -> None:
    open_ticket(tmp_path)
    report = tmp_path / "tlc-run.txt"
    report.write_text(TLC_OUTPUT, encoding="utf-8")

    result = close(tmp_path, "--summary", "with tlc", "--tlc-report", str(report))

    assert result.returncode == 0, result.stderr
    ledger = json.loads((tmp_path / SPECS / "results" / "complexity_ledger.json").read_text(encoding="utf-8"))
    metrics = ledger["entries"][-1]["metrics"]
    assert (metrics["generated_states"], metrics["distinct_states"], metrics["depth"]) == (5619356, 231621, 25)


def test_143_sf009_a_tlc_result_path_is_used_when_no_report_flag_is_given(tmp_path: Path) -> None:
    open_ticket(tmp_path)
    report = tmp_path / "tlc.txt"
    report.write_text(TLC_OUTPUT, encoding="utf-8")

    result = close(tmp_path, "--summary", "tlc as result", "--result", str(report))

    assert result.returncode == 0, result.stderr
    ledger = json.loads((tmp_path / SPECS / "results" / "complexity_ledger.json").read_text(encoding="utf-8"))
    assert ledger["entries"][-1]["metrics"]["distinct_states"] == 231621


def test_143_sf042b_design_notes_are_archived_not_deleted(tmp_path: Path) -> None:
    ticket_dir = open_ticket(tmp_path)
    notes = ticket_dir / "design" / "notes.md"
    notes.parent.mkdir(parents=True)
    notes.write_text("why the slice is shaped this way\n", encoding="utf-8")

    result = close(tmp_path, "--summary", "design kept")

    assert result.returncode == 0, result.stderr
    archived = entry(tmp_path) / "ticket" / "design" / "notes.md"
    assert archived.read_text(encoding="utf-8") == "why the slice is shaped this way\n"


def test_143_sf045_empty_summary_is_recorded_as_missing(tmp_path: Path) -> None:
    open_ticket(tmp_path)

    result = close(tmp_path)

    assert result.returncode == 0, result.stderr
    manifest = json.loads((entry(tmp_path) / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["summary"].startswith("missing:")
    assert "missing:" in (entry(tmp_path) / "summary.md").read_text(encoding="utf-8")


# -- #177 (1) ---------------------------------------------------------------


def _model(root: Path, name: str, *, attribution: bool = False) -> Path:
    d = root / name
    d.mkdir(parents=True)
    (d / "Core.tla").write_text("---- MODULE Core ----\n====\n", encoding="utf-8")
    if attribution:
        (d / "attribution.yaml").write_text("records:\n  - kind: CATCH\n", encoding="utf-8")
    return d


def test_177_attribution_record_is_planning_not_model(tmp_path: Path) -> None:
    assert "attribution.yaml" in PLANNING_FILES
    current = _model(tmp_path, "current")
    desired = _model(tmp_path, "desired_program_model", attribution=True)
    assert validate_equivalent(current, desired) == []

    program = _model(tmp_path, "program_model")
    promote_semantic_files(desired, program)
    assert not (program / "attribution.yaml").exists()


def test_177_semantically_equal_manifest_keeps_its_status_header(tmp_path: Path) -> None:
    src = _model(tmp_path, "desired_program_model")
    dst = _model(tmp_path, "program_model")
    (src / "spec_manifest.yaml").write_text("module: Core\nstatus:\n  workflow: ticket\n", encoding="utf-8")
    accepted = "module: Core\nstatus:\n  model_role: accepted\n  promoted_from: epic\n"
    (dst / "spec_manifest.yaml").write_text(accepted, encoding="utf-8")

    promote_semantic_files(src, dst)

    assert (dst / "spec_manifest.yaml").read_text(encoding="utf-8") == accepted


# -- #72 --------------------------------------------------------------------


def test_72_backlog_appended_after_the_terminal_close_does_not_block_retirement_accept_new(
    tmp_path: Path,
) -> None:
    from test_ticket_retirement import successful_terminal_fixture

    successful_terminal_fixture(tmp_path)
    desired = tmp_path / "specs" / "desired_program_model"
    (desired / "deferred_findings.yaml").write_text(
        "findings:\n  - id: BS-01-DF-01\n    summary: filed after the terminal close\n", encoding="utf-8"
    )
    (desired / "attribution.yaml").write_text("records: []\n", encoding="utf-8")

    removed = close_ticket_workflow(tmp_path, Path("specs"), dry_run=True, accept_new=True)

    assert removed[-1] == desired


def test_72_exact_snapshot_still_compares_the_model(tmp_path: Path) -> None:
    """Negative control: excluding the backlog is not excluding everything."""
    from test_ticket_retirement import successful_terminal_fixture

    successful_terminal_fixture(tmp_path)
    (tmp_path / "specs" / "desired_program_model" / "Program.tla").write_text(
        "---- MODULE Program ----\nX == 1\n====\n", encoding="utf-8"
    )
    with pytest.raises(SystemExit) as error:
        close_ticket_workflow(tmp_path, Path("specs"), dry_run=True, accept_new=True)
    assert "Program.tla" in str(error.value)


# -- workflow close (close_tickets.py) over a converged, fully-receipted fixture --


def _converged_workflow(tmp_path: Path) -> Path:
    from test_ticket_retirement import successful_terminal_fixture

    successful_terminal_fixture(tmp_path)
    return tmp_path / "specs"


def test_172_workflow_close_refuses_a_foreign_ledger_input_by_name(tmp_path: Path) -> None:
    specs = _converged_workflow(tmp_path)
    (specs / "results").mkdir(parents=True, exist_ok=True)
    (specs / "results" / "complexity_ledger_input.yaml").write_text(
        "workflow: cdc-polyglot-relation-mvp-workflow\nnarrative: another epic's close\n", encoding="utf-8"
    )

    with pytest.raises(SystemExit) as error:
        close_ticket_workflow(tmp_path, Path("specs"), dry_run=True, summary="foreign")

    assert "cdc-polyglot-relation-mvp-workflow" in str(error.value)
    # and the force path closes
    close_ticket_workflow(tmp_path, Path("specs"), dry_run=True, summary="foreign", force=True)


def test_173_dry_run_previews_the_rendered_summary(tmp_path: Path, capsys) -> None:
    _converged_workflow(tmp_path)

    close_ticket_workflow(tmp_path, Path("specs"), dry_run=True, summary="29 batches landed")

    out = capsys.readouterr().out
    assert "summary preview" in out
    assert "29 batches landed" in out
    assert "summary.md" in out and "skill_feedback.md" in out


def test_174_workflow_close_lists_unreviewed_ticket_feedback(tmp_path: Path, capsys) -> None:
    from scripts.skill_feedback import render_close_out_entry, render_template

    specs = _converged_workflow(tmp_path)
    (specs / "results").mkdir(parents=True, exist_ok=True)
    doc = render_template()
    for close_id in ("MS-001", "MS-002"):
        doc += render_close_out_entry(scope="ticket", scope_id=close_id, workflow="retirement-workflow", summary="s")
    reviewed = render_close_out_entry(scope="ticket", scope_id="MS-003", workflow="retirement-workflow", summary="s")
    doc += reviewed.replace("feedback_status: unreviewed", "feedback_status: none-found")
    doc += render_close_out_entry(scope="ticket", scope_id="OTHER-1", workflow="another-workflow", summary="s")
    (specs / "results" / "skill_feedback.md").write_text(doc, encoding="utf-8")

    close_ticket_workflow(tmp_path, Path("specs"), dry_run=True, summary="close")

    err = capsys.readouterr().err
    assert "2 ticket skill-feedback entries are still unreviewed" in err
    assert "MS-001" in err and "MS-002" in err
    assert "MS-003" not in err and "OTHER-1" not in err


def test_177_force_over_a_converged_tree_leaves_program_model_untouched(tmp_path: Path) -> None:
    specs = _converged_workflow(tmp_path)
    for name in ("current", "desired_program_model"):
        (specs / name / "spec_manifest.yaml").write_text(
            "module: Program\nstatus:\n  workflow: ticket\n", encoding="utf-8"
        )
    accepted = "module: Program\nstatus:\n  model_role: accepted\n  promoted_from: epic/x\n"
    (specs / "program_model" / "spec_manifest.yaml").write_text(accepted, encoding="utf-8")
    # A receipt gate (the #141 ordinal) is what forced --force; the trees converge.
    receipt = specs / ".history" / "retirement-workflow" / "ticket-001-FINAL-001" / "manifest.json"
    manifest = json.loads(receipt.read_text(encoding="utf-8"))
    manifest["ticket_index"] = 7
    receipt.write_text(json.dumps(manifest), encoding="utf-8")

    close_ticket_workflow(tmp_path, Path("specs"), dry_run=False, summary="forced", force=True)

    assert (specs / "program_model" / "spec_manifest.yaml").read_text(encoding="utf-8") == accepted
