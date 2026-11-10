"""BS-15 (#148): `close ticket` marks the epic deferred-ledger rows its closure closes.

Red on epic/bug-sweep (close ticket has no ledger marking or --closure there),
green on the fix. Every case drives the real CLI over a scaffolded project in a
temp dir, then runs the closure census (git-epic-workflow scripts/census.py)
over the result.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import yaml

from conftest import write_ticket_ledger_input

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "skills" / "spec-double-2" / "scripts" / "tla_spec_dev.py"
CENSUS = ROOT / "skills" / "git-epic-workflow" / "scripts" / "census.py"
TICKET = "T-1"


def _env() -> dict[str, str]:
    return {k: v for k, v in os.environ.items() if k not in {"SKILL_GATES", "SPEC_GATES", "TLA_SPEC_DEV_GATES"}}


def _cli(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        [sys.executable, str(CLI), "--spec-root", "specs", *args],
        cwd=cwd, capture_output=True, text=True, check=False, env=_env(),
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return result


def _census(cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CENSUS), "--repo-root", str(cwd)],
        capture_output=True, text=True, check=False, env=_env(),
    )


def _git(cwd: Path, *args: str) -> None:
    subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@example.invalid", *args],
                   cwd=cwd, check=True, capture_output=True)


def _epic(tmp_path: Path) -> tuple[Path, Path]:
    """A one-ticket workflow, opened and marked done; returns (ticket dir, ledger path)."""
    _cli(tmp_path, "scaffold", "project", "--name", "Ledger", "--full")
    _cli(tmp_path, "scaffold", "workflow", TICKET, "ledger marking")
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-qm", "scaffold")
    ticket_dir = tmp_path / "specs" / "tickets" / TICKET
    _cli(tmp_path, "open", "ticket", TICKET)
    write_ticket_ledger_input(ticket_dir)
    plan_path = tmp_path / "specs" / "desired_program_model" / "ticket_plan.yaml"
    plan_path.write_text(plan_path.read_text(encoding="utf-8").replace("status: next", "status: done", 1),
                         encoding="utf-8")
    name = yaml.safe_load(plan_path.read_text(encoding="utf-8"))["name"]
    return ticket_dir, tmp_path / "specs" / "results" / name / "deferred-ledger.yaml"


def _write(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def _receipt(tmp_path: Path) -> dict:
    return json.loads(next((tmp_path / "specs" / ".history").rglob("manifest.json")).read_text(encoding="utf-8"))


def test_close_marks_closed_review_closed_and_also_rows_and_the_census_passes(tmp_path: Path) -> None:
    ticket_dir, ledger = _epic(tmp_path)
    _write(ledger, {"version": 1, "findings": [
        {"id": "T-0-DF-01", "found_by": "T-0", "disposition": "pending"},
        {"id": "T-0-DF-02", "found_by": "T-0", "disposition": "pending"},
        {"id": "T-0-DF-03", "found_by": "T-0", "disposition": "pending"},
        {"id": "T-0-DF-04", "found_by": "T-0", "disposition": "pending"},
    ]})
    _write(ticket_dir / "closure.yaml", {
        "closed": ["T-0-DF-01"], "review_closed": ["T-0-DF-02"], "also": ["T-0-DF-03"],
    })

    out = _cli(tmp_path, "close", "ticket", TICKET).stdout

    rows = {r["id"]: r for r in yaml.safe_load(ledger.read_text(encoding="utf-8"))["findings"]}
    assert [rows[f"T-0-DF-0{n}"].get("closed_as") for n in (1, 2, 3, 4)] == ["closed", "review_closed", "also", None]
    assert all(rows[f"T-0-DF-0{n}"]["closed_by"] == TICKET for n in (1, 2, 3))
    assert rows["T-0-DF-04"]["disposition"] == "pending"
    assert "deferred ledger: T-0-DF-02 closed by T-1 (review_closed)" in out
    assert (ledger.parent / "closures" / f"{TICKET}.yaml").is_file()
    assert len(_receipt(tmp_path)["deferred_ledger"]["marked"]) == 3

    census = _census(tmp_path)
    assert census.returncode == 0, census.stdout
    assert "closed=1 review_closed=1 also=1 closed_by_later_ticket=3" in census.stdout


def test_close_without_a_ledger_keeps_the_closure_and_never_blocks(tmp_path: Path) -> None:
    ticket_dir, ledger = _epic(tmp_path)
    _write(ticket_dir / "closure.yaml", {"closed": ["T-0-DF-01"]})

    _cli(tmp_path, "close", "ticket", TICKET)

    assert (ledger.parent / "closures" / f"{TICKET}.yaml").is_file()
    assert _receipt(tmp_path)["deferred_ledger"]["skipped"] == "no ledger"
    assert _census(tmp_path).returncode == 2  # the census names the missing ledger


def test_close_with_an_unrecorded_id_warns_and_the_census_fails(tmp_path: Path) -> None:
    ticket_dir, ledger = _epic(tmp_path)
    _write(ledger, {"version": 1, "findings": [{"id": "T-0-DF-01", "found_by": "T-0", "disposition": "pending"}]})
    closure = tmp_path / "elsewhere" / "closure.yaml"
    _write(closure, {"closed": ["T-0-DF-99"]})

    result = _cli(tmp_path, "close", "ticket", TICKET, "--closure", str(closure))

    assert "T-0-DF-99" in result.stderr
    assert _receipt(tmp_path)["deferred_ledger"]["unknown"] == ["T-0-DF-99"]
    census = _census(tmp_path)
    assert census.returncode == 1 and "closure_unknown_id" in census.stdout


def test_close_without_a_closure_leaves_the_ledger_alone(tmp_path: Path) -> None:
    _, ledger = _epic(tmp_path)
    _write(ledger, {"version": 1, "findings": [{"id": "T-0-DF-01", "found_by": "T-0", "disposition": "pending"}]})
    before = ledger.read_text(encoding="utf-8")

    _cli(tmp_path, "close", "ticket", TICKET)

    assert ledger.read_text(encoding="utf-8") == before
    assert _receipt(tmp_path)["deferred_ledger"]["performed"] is False


def test_close_marks_the_ledger_where_pyyaml_is_absent(tmp_path: Path) -> None:
    """The installed CLI runs on a bare python3 (specWorkflow's spec.workflow.close went red on an eager import)."""
    ticket_dir, ledger = _epic(tmp_path)
    _write(ledger, {"version": 1, "findings": [{"id": "T-0-DF-01", "found_by": "T-0", "disposition": "pending"}]})
    _write(ticket_dir / "closure.yaml", {"closed": ["T-0-DF-01"]})
    no_yaml = (
        "import runpy, sys; sys.modules['yaml'] = None; "
        f"sys.argv = [{str(CLI)!r}, '--spec-root', 'specs', 'close', 'ticket', {TICKET!r}]; "
        f"runpy.run_path({str(CLI)!r}, run_name='__main__')"
    )
    result = subprocess.run([sys.executable, "-c", no_yaml], cwd=tmp_path, capture_output=True, text=True,
                            check=False, env=_env())
    assert result.returncode == 0, result.stdout + result.stderr
    rows = yaml.safe_load(ledger.read_text(encoding="utf-8"))["findings"]
    assert rows[0]["closed_by"] == TICKET and rows[0]["closed_as"] == "closed"
    assert _census(tmp_path).returncode == 0
