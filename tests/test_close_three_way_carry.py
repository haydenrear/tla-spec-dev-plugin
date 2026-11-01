"""`close ticket` carries a ticket over project current/ changes three ways.

Measured: commit-diff-context-parent #462, MS-015. Another ticket promoted into
project ``specs/current`` while MS-015 was open, and MS-015 had CHANGED lines of
the same model file. The close refused ("changed by the ticket AND in project
current/"), the epic agent's only workaround was to copy ``specs/current`` over
the ticket's model and re-record the seed digests, and that copy dropped
MS-015's TLA invariants while its spec test was promoted (tip ``tlaSpecStatic``
red, fixed by hand in f7a7682f). Three epics, 16 hand carries, 2 regressions.

Every test here drives the real close (``create_ticket_history_entry``) over a
real ``open ticket`` workspace in a real git repository, with the real
spec-unit run, and every one fails against the pre-carry close, which refused
any file both sides had changed with one undifferentiated message.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

from conftest import write_ticket_ledger_input

ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = ROOT / "skills" / "spec-double-2"

from scripts.spec_evolution import create_ticket_history_entry  # noqa: E402

TICKET = "T-1"
INVARIANT_LINE = "  /\\ owners \\subseteq Actors\n"
GUARD_LINE = "  /\\ a \\notin owners\n"
HEADER_LINE = "\\* INTERNAL VIEW: fine-grained program/component state.\n"


def _cli(cwd: Path, *args: str) -> None:
    result = subprocess.run(
        [sys.executable, str(SKILL_ROOT / "scripts" / "tla_spec_dev.py"), "--spec-root", "specs", *args],
        cwd=cwd, capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def _git(cwd: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@example.invalid", *args],
        cwd=cwd, check=True, capture_output=True,
    )


def _replace(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    assert text.count(old) == 1, f"{old!r} not unique in {path}"
    path.write_text(text.replace(old, new), encoding="utf-8")


def _project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, before_open=None) -> Path:
    """A scaffolded, committed project with ticket T-1 opened and marked done."""
    monkeypatch.chdir(tmp_path)
    _cli(tmp_path, "scaffold", "project", "--name", "Carry", "--full")
    _cli(tmp_path, "scaffold", "workflow", TICKET, "three-way carry")
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-qm", "scaffold")
    if before_open is not None:
        before_open(tmp_path)
    _cli(tmp_path, "open", "ticket", TICKET)
    ticket_dir = tmp_path / "specs" / "tickets" / TICKET
    write_ticket_ledger_input(ticket_dir)
    plan = tmp_path / "specs" / "desired_program_model" / "ticket_plan.yaml"
    plan.write_text(plan.read_text(encoding="utf-8").replace("status: next", "status: done", 1), encoding="utf-8")
    return ticket_dir


def _another_ticket_promotes(tmp_path: Path, old: str, new: str) -> None:
    """Project current/ moves under the open ticket, and the move is committed."""
    _replace(tmp_path / "specs" / "current" / "Internal.tla", old, new)
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-qm", "another ticket promoted")


def _close(tmp_path: Path):
    return create_ticket_history_entry(
        repo_root=tmp_path,
        spec_root=Path("specs"),
        ticket_ref=TICKET,
        summary="three-way carry fixture",
        result_paths=[],
        emit_feedback=False,
    )


def _snapshot(*roots: Path) -> dict[str, bytes]:
    found: dict[str, bytes] = {}
    for root in roots:
        for path in sorted(root.rglob("*")):
            if path.is_file() and "__pycache__" not in path.parts:
                found[str(path)] = path.read_bytes()
    return found


def _history_dir(tmp_path: Path) -> Path:
    return tmp_path / "specs" / ".history"


def test_clean_three_way_carries_both_sides(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The ticket changed a line current did not; current added a line elsewhere."""
    ticket_dir = _project(tmp_path, monkeypatch)
    _replace(ticket_dir / "desired" / "Internal.tla", GUARD_LINE, "  /\\ a \\notin owners \\* ticket guard\n")
    _another_ticket_promotes(tmp_path, HEADER_LINE, HEADER_LINE + "\\* added by another ticket\n")
    current_at_close = hashlib.sha256((tmp_path / "specs" / "current" / "Internal.tla").read_bytes()).hexdigest()

    _close(tmp_path)

    promoted = (tmp_path / "specs" / "current" / "Internal.tla").read_text(encoding="utf-8")
    assert "\\* ticket guard" in promoted
    assert "\\* added by another ticket" in promoted
    assert "<<<<<<<" not in promoted
    manifest_path = next(_history_dir(tmp_path).rglob("manifest.json"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    carry = manifest["three_way_carry"]
    assert carry["performed"] is True
    assert [entry["path"] for entry in carry["files"]] == ["Internal.tla"]
    assert carry["validation"]["returncode"] == 0
    archived = json.loads((manifest_path.parent / "ticket" / "ticket.yaml").read_text(encoding="utf-8"))
    # The digest was re-recorded as project current/ at carry time, and the
    # rebase is named in the ticket record (tla-spec-dev-plugin#139).
    assert archived["seed_manifest"]["desired_sha256"]["Internal.tla"] == current_at_close
    assert archived["seed_manifest"]["rebased"][0]["path"] == "Internal.tla"
    assert archived["seed_manifest"]["rebased"][0]["to_sha256"] == current_at_close


def test_ms015_shape_keeps_the_ticket_changed_lines(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The ticket CHANGED an invariant line and added one; current moved elsewhere.

    Not a pure extension of current (a line of current is gone from the ticket),
    so the old hand check refused it, and copying current over the ticket model
    dropped the ticket's invariants. The carry must keep them.
    """
    ticket_dir = _project(tmp_path, monkeypatch)
    _replace(
        ticket_dir / "desired" / "Internal.tla",
        INVARIANT_LINE,
        "  /\\ owners \\subseteq Actors /\\ Cardinality(owners) >= 0\n",
    )
    _replace(
        ticket_dir / "desired" / "Internal.tla",
        "InternalSpec ==",
        "\\* @invariant HeldLibrariesArriveInChunks\nHeldLibrariesArriveInChunks == outbox \\subseteq Records\n\nInternalSpec ==",
    )
    _another_ticket_promotes(tmp_path, HEADER_LINE, HEADER_LINE + "\\* ActivationIdsAreOnePerPublish lives elsewhere\n")

    _close(tmp_path)

    promoted = (tmp_path / "specs" / "current" / "Internal.tla").read_text(encoding="utf-8")
    assert "Cardinality(owners) >= 0" in promoted
    assert INVARIANT_LINE not in promoted
    assert "HeldLibrariesArriveInChunks ==" in promoted
    assert "ActivationIdsAreOnePerPublish lives elsewhere" in promoted


def test_a_real_conflict_refuses_naming_the_file_and_hunks(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    ticket_dir = _project(tmp_path, monkeypatch)
    _replace(ticket_dir / "desired" / "Internal.tla", GUARD_LINE, "  /\\ a \\notin owners \\* the ticket's guard\n")
    _another_ticket_promotes(tmp_path, GUARD_LINE, "  /\\ a \\notin owners \\* the other ticket's guard\n")
    before = _snapshot(ticket_dir, tmp_path / "specs" / "current")

    with pytest.raises(SystemExit) as refusal:
        _close(tmp_path)

    message = str(refusal.value)
    assert "Internal.tla: 1 conflicting hunk(s)" in message
    assert "hunk at merged line" in message
    assert "the ticket's guard" in message and "the other ticket's guard" in message
    assert _snapshot(ticket_dir, tmp_path / "specs" / "current") == before
    assert not _history_dir(tmp_path).exists()


def test_a_missing_seed_blob_refuses_by_name(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The ticket was opened from bytes no commit (nor the index) ever held."""

    def uncommitted_edit(root: Path) -> None:
        _replace(root / "specs" / "current" / "Internal.tla", HEADER_LINE, HEADER_LINE + "\\* never committed\n")

    ticket_dir = _project(tmp_path, monkeypatch, before_open=uncommitted_edit)
    _replace(ticket_dir / "desired" / "Internal.tla", GUARD_LINE, "  /\\ a \\notin owners \\* ticket guard\n")
    _another_ticket_promotes(tmp_path, "\\* never committed\n", "\\* committed instead\n")
    before = _snapshot(ticket_dir, tmp_path / "specs" / "current")

    with pytest.raises(SystemExit) as refusal:
        _close(tmp_path)

    message = str(refusal.value)
    assert "Internal.tla: seed blob not found" in message
    assert _snapshot(ticket_dir, tmp_path / "specs" / "current") == before
    assert not _history_dir(tmp_path).exists()


def test_spec_unit_failing_after_the_merge_refuses_and_restores(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A clean textual merge that breaks the ticket's own spec-unit test."""
    ticket_dir = _project(tmp_path, monkeypatch)
    _replace(ticket_dir / "desired" / "Internal.tla", GUARD_LINE, "  /\\ a \\notin owners \\* ticket guard\n")
    (ticket_dir / "desired" / "tests" / "test_carry_guard.py").write_text(
        "from pathlib import Path\n\n\n"
        "def test_the_ticket_model_has_no_project_addition():\n"
        "    model = (Path(__file__).resolve().parents[1] / 'Internal.tla').read_text()\n"
        "    assert 'ProjectAddition' not in model\n",
        encoding="utf-8",
    )
    _another_ticket_promotes(tmp_path, HEADER_LINE, HEADER_LINE + "\\* ProjectAddition\n")
    before = _snapshot(ticket_dir, tmp_path / "specs" / "current")

    with pytest.raises(SystemExit) as refusal:
        _close(tmp_path)

    message = str(refusal.value)
    assert "spec-unit" in message and "failed" in message
    assert "restored byte for byte" in message
    assert _snapshot(ticket_dir, tmp_path / "specs" / "current") == before
    assert not _history_dir(tmp_path).exists()
