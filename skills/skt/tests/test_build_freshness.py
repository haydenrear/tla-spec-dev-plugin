"""BS-20 (#202): a successful CLI build behind an unbuildable ancestor.

The shape of the defect, reproduced against the real `skill-manager` 0.28.2
in a finite fixture home (`specs/results/bug-sweep/BS-20/`): the unit's store
moves under its install record (a reviewed pin reconciled into the home), so
`unit-store:<u>` is positively stale, and every shim built from that unit is
stale *because of it* while its own fingerprint still matches. `build` cannot
produce a unit store, so the shim's rebuild no-ops and is still stale, and
the CLI exits 1 — exactly what it exits for a producer that failed. A second
unchanged build does the same thing again, forever.

The warning is correct and stays. What this file pins is that `skt build`
says WHICH of the two things happened: a distinct, actionable
`unresolved-ancestor` status (its own exit code, the root ancestor, and the
command that repairs it), and only when the evidence supports it. Anything
else — a locally moved input, an absent tree, a failed producer, a stale
ancestor `build` could have built, a survey it could not read — keeps the
CLI's exit 1.

Every test drives a REAL subprocess through a fake pin that answers `build`
and `artifacts stale` with two different documents, the way the real CLI
does.
"""

import json
import stat
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from skt import artifacts as art  # noqa: E402
from skt import build_cmd  # noqa: E402

from test_status import make_home  # noqa: E402


@pytest.fixture(autouse=True)
def isolate_root_home(tmp_path, monkeypatch):
    monkeypatch.delenv("SKILL_MANAGER_HOME", raising=False)
    monkeypatch.setenv("SKT_ROOT_HOME", str(tmp_path / "fake-root" / ".skill-manager"))


SHIM = "cli-shim:skill-script/fixtool"
TREE = "provisioned-tree:cache/skill-script-fixa-fixtool"
STORE = "unit-store:fixa"


def dispatching_cli(home: Path, *, build_doc: dict, build_exit: int,
                    stale_doc: dict | None, stale_exit: int = 0,
                    argv_log: Path | None = None) -> Path:
    """A pin that answers `build` and `artifacts stale` differently."""
    cli = home / "bin" / "cli" / "skill-manager"
    cli.parent.mkdir(parents=True, exist_ok=True)
    (cli.parent / ".build.json").write_text(json.dumps(build_doc))
    stale_text = json.dumps(stale_doc) if stale_doc is not None else ""
    (cli.parent / ".stale.json").write_text(stale_text)
    lines = ["#!/bin/sh"]
    if argv_log is not None:
        lines.append(f'printf "%s\\n" "$*" >> "{argv_log}"')
    lines += [
        'case "$1 $2" in',
        f'  "artifacts stale") cat "{cli.parent / ".stale.json"}"; '
        f'echo "boom" >&2; exit {stale_exit} ;;',
        f'  build*) cat "{cli.parent / ".build.json"}"; exit {build_exit} ;;',
        "esac",
        "exit 64",
    ]
    cli.write_text("\n".join(lines) + "\n")
    cli.chmod(cli.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
    return cli


def step(id_, kind, action, outcome, before, after, reason, materialization="materialized"):
    return {
        "id": id_, "kind": kind, "owner": "fixa", "action": action,
        "producer": "skill-script:fixtool (declared by fixa)" if kind == "cli-shim" else None,
        "reason": reason,
        "freshness_before": before, "materialization_before": materialization,
        "freshness_after": after, "materialization_after": materialization,
        "outcome": outcome, "verifiable": True,
    }


#: Verbatim shapes from the real 0.28.2 run (real-build-1.json).
STORE_STEP = step(STORE, "unit-store", "not-buildable", "skipped", "stale", "stale",
                  "a unit's store bytes come from its source, not from a local producer "
                  "— `skill-manager sync fixa`")
TREE_STEP = step(TREE, "provisioned-tree", "not-buildable", "skipped", "stale", "stale",
                 "no install records that it wrote this tree; the owner shown for it was "
                 "inferred from the shim that runs out of it")


def build_doc(shim_outcome="no-op", shim_after="stale", failed=0):
    shim = step(SHIM, "cli-shim", "rebuild", shim_outcome, "stale", shim_after,
                "stale — its declared inputs moved")
    stale_count = sum(1 for s in (STORE_STEP, TREE_STEP, shim) if s["freshness_after"] == "stale")
    return {
        "schema": 1, "home": "/h/.skill-manager", "dry_run": False,
        "summary": {"selected": 3, "rebuilt": int(shim_outcome == "built"),
                    "no_op": int(shim_outcome == "no-op"), "failed": failed,
                    "already_current": 0, "not_buildable": 2, "still_stale": stale_count},
        "steps": [STORE_STEP, TREE_STEP, shim],
    }


def stale_row(id_, kind, reason, because=(), materialization="materialized"):
    return {"id": id_, "kind": kind, "owner": "fixa", "freshness": "stale",
            "materialization": materialization, "reason": reason, "because": list(because)}


#: Verbatim shapes from the real 0.28.2 run (real-stale-before.json).
STORE_ROW = stale_row(STORE, "unit-store",
                      "what is recorded about it does not describe the bytes on disk "
                      "(records 03650e24487f…, store is at e8a5466c05b9…)")
TREE_ROW = stale_row(TREE, "provisioned-tree",
                     f"it is built from {STORE}, which is stale", because=[STORE])
SHIM_ROW = stale_row(SHIM, "cli-shim",
                     f"it is built from {STORE}, {TREE}, which are stale",
                     because=[STORE, TREE])


def stale_doc(*rows):
    return {"schema": 2, "home": "/h/.skill-manager",
            "summary": {"artifacts": len(rows), "stale": len(rows), "unverifiable": 0,
                        "current": 0, "stale_by_kind": {}},
            "stale": list(rows), "unverifiable": []}


def home_with(tmp_path, **kwargs) -> Path:
    home = make_home(tmp_path / "repo")
    dispatching_cli(home, **kwargs)
    return home


# --------------------------------------------- the reported defect, red → green


def test_successful_build_behind_unbuildable_ancestor_is_a_distinct_status(tmp_path, capsys):
    """The issue's first run: the CLI builds/no-ops, its ancestor is not
    buildable here, and the CLI exits 1 with everything still stale."""
    home = home_with(tmp_path, build_doc=build_doc(), build_exit=1,
                     stale_doc=stale_doc(STORE_ROW, TREE_ROW, SHIM_ROW))

    result = art.build((SHIM,), home=home)
    assert result.status == art.STATUS_UNRESOLVED_ANCESTOR
    assert result.exit_code == art.EXIT_UNRESOLVED_ANCESTOR != 1
    # The warning is preserved, not cleared: still stale, still not ok.
    assert result.still_stale == 3 and result.ok is False
    [blocked] = result.unresolved_ancestors
    assert blocked.id == SHIM
    assert blocked.roots == (STORE,)
    assert any("skill-manager sync fixa" in r for r in blocked.remedies)

    code = build_cmd.run([SHIM], start=home.parent)
    out = capsys.readouterr().out
    assert code == art.EXIT_UNRESOLVED_ANCESTOR
    assert "unresolved-ancestor" in out
    assert STORE in out and "skill-manager sync fixa" in out


def test_a_second_unchanged_build_reports_the_same_distinct_status(tmp_path, capsys):
    """The issue's repeated run: nothing changed, the build no-ops again.
    It must not be exit 1 with everything stale a second time."""
    home = home_with(tmp_path, build_doc=build_doc(), build_exit=1,
                     stale_doc=stale_doc(STORE_ROW, TREE_ROW, SHIM_ROW))
    first = build_cmd.run([SHIM], start=home.parent, as_json=True)
    first_doc = json.loads(capsys.readouterr().out)
    second = build_cmd.run([SHIM], start=home.parent, as_json=True)
    second_doc = json.loads(capsys.readouterr().out)
    assert first == second == art.EXIT_UNRESOLVED_ANCESTOR
    for doc in (first_doc, second_doc):
        assert doc["status"] == "unresolved-ancestor"
        assert doc["exit_code"] == art.EXIT_UNRESOLVED_ANCESTOR
        assert doc["summary"]["still_stale"] == 3
        assert doc["unresolved_ancestors"][0]["id"] == SHIM
        assert doc["unresolved_ancestors"][0]["roots"] == [STORE]


def test_a_genuinely_current_second_build_is_ok(tmp_path, capsys):
    """After the ancestor is repaired (`sync fixa` in the fixture), the
    second build has nothing stale: status ok, exit 0, no survey read."""
    log = tmp_path / "argv.log"
    empty = {"schema": 1, "home": "/h", "dry_run": False,
             "summary": {"selected": 0, "rebuilt": 0, "no_op": 0, "failed": 0,
                         "already_current": 0, "not_buildable": 0, "still_stale": 0},
             "steps": []}
    home = home_with(tmp_path, build_doc=empty, build_exit=0, stale_doc=None, argv_log=log)
    assert build_cmd.run([SHIM], start=home.parent) == 0
    result = art.build((SHIM,), home=home)
    assert result.status == art.STATUS_OK and result.exit_code == 0
    assert "artifacts stale" not in log.read_text()


# --------------------------------------------- what must stay plain exit 1


def test_a_locally_moved_input_stays_a_failure(tmp_path):
    """Changed input: the shim's own fingerprint moved. `because` still names
    the ancestor, but the local verdict decided it — not this status."""
    moved = stale_row(SHIM, "cli-shim",
                      "its declared inputs moved: recorded a3f21c8f, now 9b17e401",
                      because=[STORE, TREE])
    home = home_with(tmp_path, build_doc=build_doc(shim_outcome="built"), build_exit=1,
                     stale_doc=stale_doc(STORE_ROW, TREE_ROW, moved))
    result = art.build((SHIM,), home=home)
    assert result.exit_code == 1 and result.status == art.STATUS_STALE
    assert result.unresolved_ancestors == ()


def test_an_absent_tree_stays_a_failure(tmp_path):
    absent = stale_row(SHIM, "cli-shim",
                       f"it is built from {STORE}, which is stale; and its output "
                       "bin/cli/fixtool is not there",
                       because=[STORE], materialization="declared-only")
    home = home_with(tmp_path, build_doc=build_doc(), build_exit=1,
                     stale_doc=stale_doc(STORE_ROW, absent))
    result = art.build((SHIM,), home=home)
    assert result.exit_code == 1 and result.status == art.STATUS_STALE


def test_a_failed_producer_stays_a_failure_and_skips_the_survey(tmp_path):
    log = tmp_path / "argv.log"
    home = home_with(tmp_path, build_doc=build_doc(shim_outcome="failed", failed=1),
                     build_exit=1, stale_doc=stale_doc(STORE_ROW, TREE_ROW, SHIM_ROW),
                     argv_log=log)
    result = art.build((SHIM,), home=home)
    assert result.exit_code == 1 and result.status == art.STATUS_FAILED
    assert "artifacts stale" not in log.read_text()


def test_a_buildable_stale_root_is_not_an_unresolved_ancestor(tmp_path):
    """Missing owner / wrong owner relation: if the chain ends at something
    `build` HAS a producer for, the remedy is `skt build`, not this status."""
    other = "cli-shim:skill-script/other"
    other_row = stale_row(other, "cli-shim", "its declared inputs moved: recorded a, now b")
    shim = stale_row(SHIM, "cli-shim", f"it is built from {other}, which is stale",
                     because=[other])
    home = home_with(tmp_path, build_doc=build_doc(), build_exit=1,
                     stale_doc=stale_doc(other_row, shim))
    result = art.build((SHIM,), home=home)
    assert result.exit_code == 1 and result.status == art.STATUS_STALE


def test_an_ancestor_the_survey_does_not_name_is_not_assumed(tmp_path):
    """Missing owner: the cause names an ancestor with no stale row of its
    own. Nothing positive says it is the root, so fail closed."""
    shim = stale_row(SHIM, "cli-shim", f"it is built from {STORE}, which is stale",
                     because=[STORE])
    home = home_with(tmp_path, build_doc=build_doc(), build_exit=1,
                     stale_doc=stale_doc(shim))
    result = art.build((SHIM,), home=home)
    assert result.exit_code == 1 and result.status == art.STATUS_STALE


def test_an_unreadable_survey_keeps_the_cli_exit(tmp_path):
    home = home_with(tmp_path, build_doc=build_doc(), build_exit=1,
                     stale_doc=None, stale_exit=1)
    result = art.build((SHIM,), home=home)
    assert result.exit_code == 1 and result.status == art.STATUS_STALE
    assert result.unresolved_ancestors == ()


def test_a_dry_run_is_never_reclassified(tmp_path):
    doc = build_doc()
    doc["dry_run"] = True
    home = home_with(tmp_path, build_doc=doc, build_exit=0,
                     stale_doc=stale_doc(STORE_ROW, TREE_ROW, SHIM_ROW))
    result = art.build((SHIM,), home=home, dry_run=True)
    assert result.exit_code == 0 and result.unresolved_ancestors == ()
