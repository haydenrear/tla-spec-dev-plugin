"""BS-12 (#141, #138): open/close ticket follow the plan and carry desired.

One regression test per covered item, each red on the epic base and green on
the fix. Every case drives the real CLI over a scaffolded project in a temp dir.

- #141 SF-075  `close ticket` carries the delta it promoted into project
               current/ on into desired_program_model/, three ways, recorded in
               the receipt as `desired_carry`
- #138 DEF-516 `open ticket` seeds current/ when the ticket's plan entry runs
               `specs/tickets/<id>/current/...`
- #138 PLUGIN-mutation-close  `close ticket` refuses a ticket tree holding a
               `.tlc-mutation-*` path; --force passes and is recorded
(#141 SF-074 and SF-076 are in skills/git-epic-workflow/scripts/tests.)
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from conftest import write_ticket_ledger_input

ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = ROOT / "skills" / "spec-double-2"

TICKET = "T-1"
GUARD_LINE = "  /\\ a \\notin owners\n"
HEADER_LINE = "\\* INTERNAL VIEW: fine-grained program/component state.\n"


def _cli(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if k not in {"SKILL_GATES", "TLA_SPEC_DEV_GATES"}}
    return subprocess.run(
        [sys.executable, str(SKILL_ROOT / "scripts" / "tla_spec_dev.py"), "--spec-root", "specs", *args],
        cwd=cwd, capture_output=True, text=True, check=False, env=env,
    )


def _ok(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    result = _cli(cwd, *args)
    assert result.returncode == 0, result.stdout + result.stderr
    return result


def _git(cwd: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@example.invalid", *args],
        cwd=cwd, check=True, capture_output=True,
    )


def _replace(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    assert text.count(old) == 1, f"{old!r} not unique in {path}"
    path.write_text(text.replace(old, new), encoding="utf-8")


def _plan(tmp_path: Path) -> Path:
    return tmp_path / "specs" / "desired_program_model" / "ticket_plan.yaml"


def _project(tmp_path: Path, *, plan_edit=None) -> Path:
    _ok(tmp_path, "scaffold", "project", "--name", "Carry", "--full")
    _ok(tmp_path, "scaffold", "workflow", TICKET, "close carries desired")
    if plan_edit is not None:
        plan_edit(_plan(tmp_path))
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-qm", "scaffold")
    return tmp_path / "specs" / "tickets" / TICKET


def _open_done(tmp_path: Path) -> Path:
    ticket_dir = _project(tmp_path)
    _ok(tmp_path, "open", "ticket", TICKET)
    write_ticket_ledger_input(ticket_dir)
    plan = _plan(tmp_path)
    plan.write_text(plan.read_text(encoding="utf-8").replace("status: next", "status: done", 1), encoding="utf-8")
    return ticket_dir


def _manifest(tmp_path: Path) -> dict:
    return json.loads(next((tmp_path / "specs" / ".history").rglob("manifest.json")).read_text(encoding="utf-8"))


def _desired(tmp_path: Path) -> str:
    return (tmp_path / "specs" / "desired_program_model" / "Internal.tla").read_text(encoding="utf-8")


# --- #141 SF-075 -------------------------------------------------------------


def test_sf075_close_carries_the_delivered_model_into_desired(tmp_path: Path) -> None:
    ticket_dir = _open_done(tmp_path)
    _replace(ticket_dir / "desired" / "Internal.tla", GUARD_LINE, "  /\\ a \\notin owners \\* delivered guard\n")

    _ok(tmp_path, "close", "ticket", TICKET)

    assert "\\* delivered guard" in (tmp_path / "specs" / "current" / "Internal.tla").read_text(encoding="utf-8")
    assert "\\* delivered guard" in _desired(tmp_path)
    carry = _manifest(tmp_path)["desired_carry"]
    assert carry["performed"] is True
    assert "Internal.tla" in carry["followed"]
    assert carry["conflicts"] == []


def test_sf075_desired_intent_elsewhere_is_kept_and_merged(tmp_path: Path) -> None:
    """Desired declared a line the ticket did not deliver: the merge keeps it."""
    ticket_dir = _open_done(tmp_path)
    _replace(tmp_path / "specs" / "desired_program_model" / "Internal.tla", HEADER_LINE,
             HEADER_LINE + "\\* declared by the epic plan, not yet delivered\n")
    _replace(ticket_dir / "desired" / "Internal.tla", GUARD_LINE, "  /\\ a \\notin owners \\* delivered guard\n")

    _ok(tmp_path, "close", "ticket", TICKET)

    desired = _desired(tmp_path)
    assert "\\* delivered guard" in desired
    assert "declared by the epic plan, not yet delivered" in desired
    assert "<<<<<<<" not in desired
    assert "Internal.tla" in _manifest(tmp_path)["desired_carry"]["merged"]


def test_sf075_conflict_leaves_desired_and_never_blocks(tmp_path: Path) -> None:
    ticket_dir = _open_done(tmp_path)
    _replace(tmp_path / "specs" / "desired_program_model" / "Internal.tla", GUARD_LINE,
             "  /\\ a \\notin owners \\* desired's own guard\n")
    before = _desired(tmp_path)
    _replace(ticket_dir / "desired" / "Internal.tla", GUARD_LINE, "  /\\ a \\notin owners \\* delivered guard\n")

    result = _ok(tmp_path, "close", "ticket", TICKET)

    assert _desired(tmp_path) == before
    assert "desired carry left desired_program_model/Internal.tla" in result.stderr
    conflicts = _manifest(tmp_path)["desired_carry"]["conflicts"]
    assert [c["path"] for c in conflicts] == ["Internal.tla"]


def test_sf075_opt_out_is_recorded(tmp_path: Path) -> None:
    ticket_dir = _open_done(tmp_path)
    before = _desired(tmp_path)
    _replace(ticket_dir / "desired" / "Internal.tla", GUARD_LINE, "  /\\ a \\notin owners \\* delivered guard\n")

    _ok(tmp_path, "close", "ticket", TICKET, "--no-carry-desired")

    assert _desired(tmp_path) == before
    assert _manifest(tmp_path)["desired_carry"] == {"performed": False, "skipped": "--no-carry-desired"}


# --- #138 DEF-516 ------------------------------------------------------------


def test_def516_open_seeds_current_when_the_plan_runs_it(tmp_path: Path) -> None:
    def plan_runs_ticket_current(plan: Path) -> None:
        text = plan.read_text(encoding="utf-8")
        marker = f"- id: {TICKET}\n"
        assert marker in text, text
        plan.write_text(text.replace(
            marker,
            marker + f"    validation:\n      tlc: tlc specs/tickets/{TICKET}/current/Internal.tla\n", 1,
        ), encoding="utf-8")

    ticket_dir = _project(tmp_path, plan_edit=plan_runs_ticket_current)
    result = _ok(tmp_path, "open", "ticket", TICKET)

    assert (ticket_dir / "current" / "Internal.tla").is_file(), result.stdout
    assert "seeding current/" in result.stdout


def test_def516_default_open_stays_desired_only(tmp_path: Path) -> None:
    ticket_dir = _project(tmp_path)
    _ok(tmp_path, "open", "ticket", TICKET)
    assert (ticket_dir / "desired").is_dir()
    assert not (ticket_dir / "current").exists()


# --- #138 PLUGIN-mutation-close ----------------------------------------------


def _leave_mutation(ticket_dir: Path) -> None:
    mutation = ticket_dir / "desired" / ".tlc-mutation-1a2b3c"
    mutation.mkdir()
    (mutation / "Internal.tla").write_text("---- MODULE Internal ----\n\\* mutated\n====\n", encoding="utf-8")


def test_mutation_close_refuses_a_tree_with_mutation_paths(tmp_path: Path) -> None:
    ticket_dir = _open_done(tmp_path)
    _leave_mutation(ticket_dir)

    result = _cli(tmp_path, "close", "ticket", TICKET)

    assert result.returncode != 0
    assert ".tlc-mutation-1a2b3c" in result.stdout + result.stderr
    assert not (tmp_path / "specs" / ".history").exists()


def test_mutation_close_force_passes_and_is_recorded(tmp_path: Path) -> None:
    ticket_dir = _open_done(tmp_path)
    _leave_mutation(ticket_dir)

    _ok(tmp_path, "close", "ticket", TICKET, "--force")

    assert _manifest(tmp_path)["forced_mutation_paths"] == ["desired/.tlc-mutation-1a2b3c"]
