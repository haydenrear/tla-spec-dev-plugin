"""BS-15 (#148, #147 census step): the epic deferred ledger and its closure census.

Red on epic/bug-sweep (census.py does not exist there), green on the fix. Each
census category has its own case, and the vacuum -- an empty ledger and no
closures -- must not read as green.
"""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys

import pytest
import yaml


SCRIPT = Path(__file__).resolve().parents[1] / "census.py"
EPIC = "demo-epic"


def run(root: Path, *args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    base = {k: v for k, v in os.environ.items() if k not in {"SKILL_GATES", "SPEC_GATES"}}
    base.update(env or {})
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--repo-root", str(root), *args],
        capture_output=True, text=True, check=False, env=base,
    )


def write(path: Path, data: object) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    return path


def plan(root: Path, tickets=("T-1", "T-2"), *, per_ticket: bool = True, where: str | None = None) -> None:
    policy = {"mode": "batch", "budget": 5}
    if per_ticket:
        policy["per_ticket_backlog"] = "specs/results/deferred/{ticket}.yaml"
    path = root / (where or "specs/desired_program_model/ticket_plan.yaml")
    write(path, {"name": EPIC, "tickets": [{"id": t} for t in tickets], "deferment_policy": policy})


def ledger_path(root: Path) -> Path:
    return root / "specs" / "results" / EPIC / "deferred-ledger.yaml"


def ledger(root: Path, *rows: dict) -> None:
    write(ledger_path(root), {"version": 1, "epic": EPIC, "findings": list(rows)})


def row(fid: str, disposition: str = "pending", **extra) -> dict:
    return {"id": fid, "found_by": fid.split("-DF-")[0], "disposition": disposition, **extra}


def per_ticket(root: Path, ticket: str, *rows: dict) -> None:
    write(root / "specs" / "results" / "deferred" / f"{ticket}.yaml", {"findings": list(rows)})


def closure(root: Path, ticket: str, **kinds: list[str]) -> None:
    write(ledger_path(root).parent / "closures" / f"{ticket}.yaml", {"ticket": ticket, **kinds})


# --- the vacuum, and no ledger at all ----------------------------------------


def test_vacuum_empty_ledger_and_no_closures_is_not_green(tmp_path: Path) -> None:
    plan(tmp_path)
    ledger(tmp_path)
    result = run(tmp_path)
    assert result.returncode == 3, result.stdout + result.stderr
    assert "VACUUM" in result.stdout


def test_missing_ledger_is_its_own_red(tmp_path: Path) -> None:
    plan(tmp_path)
    result = run(tmp_path)
    assert result.returncode == 2
    assert "NO LEDGER" in result.stdout


def test_reconciled_epic_passes(tmp_path: Path) -> None:
    plan(tmp_path)
    ledger(tmp_path, row("T-1-DF-01", "fixed", closed_by="T-1"), row("T-1-DF-02"))
    per_ticket(tmp_path, "T-1", row("T-1-DF-01", "fixed"), row("T-1-DF-02", "pending"))
    closure(tmp_path, "T-1", closed=["T-1-DF-01"])
    result = run(tmp_path)
    assert result.returncode == 0, result.stdout
    assert "PASS" in result.stdout
    assert "closed=1 review_closed=0 also=0 closed_by_later_ticket=0" in result.stdout


# --- each failing category ---------------------------------------------------


def test_per_ticket_row_missing_from_the_ledger_fails(tmp_path: Path) -> None:
    plan(tmp_path)
    ledger(tmp_path, row("T-1-DF-01"))
    per_ticket(tmp_path, "T-2", row("T-2-DF-01"))
    result = run(tmp_path)
    assert result.returncode == 1
    assert "unabsorbed: T-2-DF-01" in result.stdout


def test_per_ticket_file_disagreeing_with_the_ledger_fails(tmp_path: Path) -> None:
    plan(tmp_path)
    ledger(tmp_path, row("T-1-DF-01", "fixed"))
    per_ticket(tmp_path, "T-1", row("T-1-DF-01", "pending"))
    result = run(tmp_path)
    assert result.returncode == 1
    assert "drift: T-1-DF-01" in result.stdout


def test_unreadable_disposition_is_drift(tmp_path: Path) -> None:
    plan(tmp_path)
    ledger(tmp_path, row("T-1-DF-01", "Filed only. Separate repository."))
    per_ticket(tmp_path, "T-1", row("T-1-DF-01", "Filed only. Separate repository."))
    result = run(tmp_path)
    assert result.returncode == 1
    assert "drift: T-1-DF-01" in result.stdout


@pytest.mark.parametrize("kind", ["closed", "review_closed", "also"])
def test_open_row_already_fixed_in_a_merged_closure_fails(tmp_path: Path, kind: str) -> None:
    plan(tmp_path)
    ledger(tmp_path, row("T-1-DF-01"))
    closure(tmp_path, "T-1", **{kind: ["T-1-DF-01"]})
    result = run(tmp_path)
    assert result.returncode == 1, result.stdout
    assert f"fixed_but_open: T-1-DF-01 is open but T-1 closed it ({kind})" in result.stdout
    assert f"{kind}=1" in result.stdout


def test_closed_by_a_later_ticket_is_counted_and_named(tmp_path: Path) -> None:
    plan(tmp_path)
    ledger(tmp_path, row("T-1-DF-01"), row("T-1-DF-02", "fixed"))
    closure(tmp_path, "T-2", closed=["T-1-DF-01"], also=["T-1-DF-02"])
    result = run(tmp_path)
    assert result.returncode == 1
    assert "closed_by_later_ticket=2" in result.stdout
    assert "(closed, found by T-1)" in result.stdout


def test_duplicate_naming_no_recorded_original_fails(tmp_path: Path) -> None:
    plan(tmp_path)
    ledger(tmp_path, row("T-2-DF-01", "duplicate", duplicate_of="T-1-DF-09"))
    result = run(tmp_path)
    assert result.returncode == 1
    assert "dangling_duplicate: T-2-DF-01 names original T-1-DF-09" in result.stdout


def test_closure_naming_an_unrecorded_id_fails(tmp_path: Path) -> None:
    plan(tmp_path)
    ledger(tmp_path, row("T-1-DF-01"))
    closure(tmp_path, "T-1", closed=["T-1-DF-77"])
    result = run(tmp_path)
    assert result.returncode == 1
    assert "closure_unknown_id" in result.stdout and "T-1-DF-77" in result.stdout


# --- forceable; never blocks ---------------------------------------------------


@pytest.mark.parametrize("how", ["flag", "env"])
def test_force_reports_and_exits_zero(tmp_path: Path, how: str) -> None:
    plan(tmp_path)
    ledger(tmp_path, row("T-1-DF-01"))
    closure(tmp_path, "T-1", closed=["T-1-DF-01"])
    args, env = (["--force"], None) if how == "flag" else ([], {"SKILL_GATES": "off"})
    result = run(tmp_path, *args, env=env)
    assert result.returncode == 0
    assert "fixed_but_open" in result.stdout and "FORCED" in result.stderr


# --- BS-12-DF-02: the census after workflow close -----------------------------


def test_census_reads_the_closed_snapshot_plan_after_workflow_close(tmp_path: Path) -> None:
    plan(tmp_path, where=f"specs/.history/{EPIC}/closed-snapshot/snapshots/desired_program_model/ticket_plan.yaml")
    ledger(tmp_path, row("T-1-DF-01", "fixed"))
    per_ticket(tmp_path, "T-1", row("T-1-DF-01", "pending"))
    result = run(tmp_path, "--epic", EPIC)
    assert "closed-snapshot" in result.stdout
    assert result.returncode == 1  # the per-ticket file was found through the snapshot's policy
    assert "drift: T-1-DF-01" in result.stdout


# --- recording: the id is given when the finding is recorded ------------------


def test_record_gives_ids_and_names_the_original_then_absorb_reconciles(tmp_path: Path) -> None:
    plan(tmp_path)
    assert run(tmp_path, "init").returncode == 0
    first = run(tmp_path, "record", "--ticket", "T-1", "--summary", "s", "--reproduction", "r")
    second = run(tmp_path, "record", "--ticket", "T-2", "--summary", "s", "--reproduction", "r",
                 "--duplicate-of", "T-1-DF-01")
    third = run(tmp_path, "record", "--ticket", "T-1", "--summary", "s2", "--reproduction", "r")
    assert "recorded T-1-DF-01" in first.stdout
    assert "recorded T-2-DF-01" in second.stdout and "duplicate of T-1-DF-01" in second.stdout
    assert "recorded T-1-DF-02" in third.stdout
    assert run(tmp_path).returncode == 1  # recorded, not yet absorbed
    assert "absorbed 3" in run(tmp_path, "absorb").stdout
    rows = yaml.safe_load(ledger_path(tmp_path).read_text())["findings"]
    assert [r["id"] for r in rows] == ["T-1-DF-01", "T-1-DF-02", "T-2-DF-01"]
    assert rows[2]["duplicate_of"] == "T-1-DF-01"
    result = run(tmp_path)
    assert result.returncode == 0, result.stdout


def test_record_without_per_ticket_backlog_writes_the_ledger(tmp_path: Path) -> None:
    plan(tmp_path, per_ticket=False)
    run(tmp_path, "init")
    result = run(tmp_path, "record", "--ticket", "T-1", "--summary", "s", "--reproduction", "r")
    assert "recorded T-1-DF-01" in result.stdout
    assert yaml.safe_load(ledger_path(tmp_path).read_text())["findings"][0]["id"] == "T-1-DF-01"
