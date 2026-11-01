"""MF-021 regression: ticket promotion must not silently destroy specs/current.

The original defect: ``promote_ticket_outputs`` called ``replace_tree``, which
``shutil.rmtree``'d ``specs/current`` before copying the ticket's ``desired/``
tree over it. Because ``open ticket`` deliberately seeds the ticket workspace
from a *filtered* view of ``specs/current`` (it excludes
``tests/test_current_ticket_workflow.py``), every promotion silently deleted
that file. It happened on MF-012 and again on MF-020, taking MF-012's budgets
retention test with it.

These tests pin the two halves of the resolution:

* a current-only path that the ticket was never given survives promotion; and
* a path the ticket *was* given and then deleted is still removed, so
  ``specs/current`` stays a whole-program working copy rather than an
  accumulating union of every file any ticket ever produced.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from scripts.spec_evolution import (  # noqa: E402
    load_ticket_seed_manifest,
    promote_ticket_outputs,
    tree_relative_files,
)

PROJECT_WORKFLOW_TEST = "tests/test_current_ticket_workflow.py"


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _build_workspace(tmp_path: Path, *, seed_manifest: dict | None) -> tuple[Path, Path]:
    """A project specs/ tree plus a ticket workspace seeded the way `open` seeds it."""
    specs_dir = tmp_path / "specs"
    current = specs_dir / "current"
    _write(current / "TlaSpecDevCli.tla", "---- MODULE TlaSpecDevCli ----\n====\n")
    _write(current / "spec_manifest.yaml", "status:\n  active_ticket: MF-021\n")
    # The current-only file the defect destroyed, twice.
    _write(current / PROJECT_WORKFLOW_TEST, "def test_budgets_retention():\n    assert True\n")
    # The current-only *directory* MF-020 lost.
    _write(current / "refinement-probe" / "probe.tla", "---- MODULE probe ----\n====\n")

    active_dir = specs_dir / "tickets" / "MF-021"
    desired = active_dir / "desired"
    # `open ticket` copies current/ into desired/ but skips the project workflow
    # test and never sees anything added to current/ after the ticket opened.
    _write(desired / "TlaSpecDevCli.tla", "---- MODULE TlaSpecDevCli ----\n\\* fixed\n====\n")
    _write(desired / "spec_manifest.yaml", "status:\n  active_ticket: MF-021\n")

    payload: dict = {"schema_version": "tla-spec-dev.ticket-workflow.v1", "ticket_id": "MF-021"}
    if seed_manifest is not None:
        payload["seed_manifest"] = seed_manifest
    _write(active_dir / "ticket.yaml", json.dumps(payload, indent=2) + "\n")
    return active_dir, specs_dir


def test_promotion_preserves_a_current_only_test_file(tmp_path: Path) -> None:
    """The exact loss observed on MF-012 and MF-020.

    Seed a file that lives only in specs/current, promote, assert it survives.
    Against the pre-fix ``replace_tree`` implementation this fails: the file is
    gone.
    """
    active_dir, specs_dir = _build_workspace(
        tmp_path,
        seed_manifest={
            "source": "current",
            "excluded": [PROJECT_WORKFLOW_TEST],
            "desired": ["TlaSpecDevCli.tla", "spec_manifest.yaml"],
        },
    )

    survivor = specs_dir / "current" / PROJECT_WORKFLOW_TEST
    probe = specs_dir / "current" / "refinement-probe" / "probe.tla"
    assert survivor.is_file()
    assert probe.is_file()

    promote_ticket_outputs(active_dir, specs_dir)

    assert survivor.is_file(), "promotion destroyed a file unique to specs/current"
    assert survivor.read_text(encoding="utf-8") == "def test_budgets_retention():\n    assert True\n"
    assert probe.is_file(), "promotion destroyed a directory unique to specs/current"

    # And the ticket's own work did land.
    assert "fixed" in (specs_dir / "current" / "TlaSpecDevCli.tla").read_text(encoding="utf-8")


def test_promotion_enumerates_preserved_paths(tmp_path: Path) -> None:
    """No path is preserved or removed silently; close output can list them."""
    active_dir, specs_dir = _build_workspace(
        tmp_path,
        seed_manifest={
            "source": "current",
            "excluded": [PROJECT_WORKFLOW_TEST],
            "desired": ["TlaSpecDevCli.tla", "spec_manifest.yaml"],
        },
    )
    record = promote_ticket_outputs(active_dir, specs_dir)
    current_record = next(item for item in record["merged"] if item["role"] == "current")

    assert current_record["seed_recorded"] is True
    assert set(current_record["preserved"]) == {
        PROJECT_WORKFLOW_TEST,
        "refinement-probe/probe.tla",
    }
    assert current_record["removed"] == []


def test_promotion_still_removes_a_path_the_ticket_deleted(tmp_path: Path) -> None:
    """specs/current stays a working copy, not an accumulating union.

    ``legacy.tla`` was seeded into the ticket workspace and the ticket dropped
    it. That is a recorded deletion decision, so promotion honours it.
    """
    active_dir, specs_dir = _build_workspace(
        tmp_path,
        seed_manifest={
            "source": "current",
            "excluded": [PROJECT_WORKFLOW_TEST],
            "desired": ["TlaSpecDevCli.tla", "spec_manifest.yaml", "legacy.tla"],
        },
    )
    _write(specs_dir / "current" / "legacy.tla", "---- MODULE legacy ----\n====\n")

    record = promote_ticket_outputs(active_dir, specs_dir)
    current_record = next(item for item in record["merged"] if item["role"] == "current")

    assert not (specs_dir / "current" / "legacy.tla").exists()
    assert current_record["removed"] == ["legacy.tla"]
    assert (specs_dir / "current" / PROJECT_WORKFLOW_TEST).is_file()


def test_promotion_without_a_seed_manifest_deletes_nothing(tmp_path: Path) -> None:
    """Tickets opened before the seed manifest existed get the safe default.

    Absent evidence of what the ticket was offered, no deletion intent is
    provable, so promotion preserves everything and says so.
    """
    active_dir, specs_dir = _build_workspace(tmp_path, seed_manifest=None)
    _write(specs_dir / "current" / "legacy.tla", "---- MODULE legacy ----\n====\n")

    assert load_ticket_seed_manifest(active_dir) is None

    record = promote_ticket_outputs(active_dir, specs_dir)
    current_record = next(item for item in record["merged"] if item["role"] == "current")

    assert current_record["seed_recorded"] is False
    assert current_record["removed"] == []
    assert (specs_dir / "current" / "legacy.tla").is_file()
    assert (specs_dir / "current" / PROJECT_WORKFLOW_TEST).is_file()


def test_open_ticket_records_the_seed_manifest(tmp_path: Path) -> None:
    """The two ends must agree: `open` records exactly what it seeded."""
    from scripts.new_ticket_workflow import workflow_tree_seed_paths

    source = tmp_path / "current"
    _write(source / "TlaSpecDevCli.tla", "x")
    _write(source / PROJECT_WORKFLOW_TEST, "y")
    _write(source / "tests" / "test_adapter.py", "z")
    _write(source / "__pycache__" / "junk.pyc", "ignored")

    seeded = workflow_tree_seed_paths(source, {PROJECT_WORKFLOW_TEST})

    assert seeded == ["TlaSpecDevCli.tla", "tests/test_adapter.py"]
    assert PROJECT_WORKFLOW_TEST not in seeded, (
        "the project workflow test is excluded from the workspace by design; "
        "promotion must therefore never claim authority to delete it"
    )


def test_tree_relative_files_skips_ignored_names(tmp_path: Path) -> None:
    _write(tmp_path / "a.tla", "a")
    _write(tmp_path / "__pycache__" / "b.pyc", "b")
    _write(tmp_path / "states" / "c.txt", "c")
    _write(tmp_path / "nested" / "d.py", "d")

    assert tree_relative_files(tmp_path) == {"a.tla", "nested/d.py"}


# --- three-way promotion (epic #234: CDC-ISF-040's close reverted two other tickets' work) ---

def _three_way_workspace(tmp_path: Path, *, seeded: str, ticket: str, project: str | None):
    import hashlib
    from scripts.spec_evolution import promote_current_tree  # noqa: E402
    src, dst = tmp_path / "desired", tmp_path / "current"
    _write(src / "Internal.tla", ticket)
    if project is not None:
        _write(dst / "Internal.tla", project)
    digests = {"Internal.tla": hashlib.sha256(seeded.encode()).hexdigest()}
    return src, dst, digests, promote_current_tree


def test_a_file_the_ticket_never_touched_keeps_what_another_ticket_promoted(tmp_path: Path) -> None:
    src, dst, digests, promote = _three_way_workspace(
        tmp_path, seeded="v1\n", ticket="v1\n", project="v2 from another ticket\n")
    record = promote(src, dst, {"Internal.tla"}, digests)
    assert (dst / "Internal.tla").read_text() == "v2 from another ticket\n"
    assert record["kept_current"] == ["Internal.tla"]


def test_a_file_only_the_ticket_changed_is_promoted(tmp_path: Path) -> None:
    src, dst, digests, promote = _three_way_workspace(
        tmp_path, seeded="v1\n", ticket="v1 edited by the ticket\n", project="v1\n")
    promote(src, dst, {"Internal.tla"}, digests)
    assert (dst / "Internal.tla").read_text() == "v1 edited by the ticket\n"


def test_a_file_both_sides_changed_is_refused_and_nothing_is_written(tmp_path: Path) -> None:
    import pytest
    from scripts.spec_evolution import PromotionConflict  # noqa: E402
    src, dst, digests, promote = _three_way_workspace(
        tmp_path, seeded="v1\n", ticket="ticket edit\n", project="other ticket's edit\n")
    with pytest.raises(PromotionConflict, match="Internal.tla"):
        promote(src, dst, {"Internal.tla"}, digests)
    assert (dst / "Internal.tla").read_text() == "other ticket's edit\n"


def test_without_recorded_digests_promotion_keeps_its_old_behaviour(tmp_path: Path) -> None:
    src, dst, _digests, promote = _three_way_workspace(
        tmp_path, seeded="v1\n", ticket="v1\n", project="v2\n")
    promote(src, dst, {"Internal.tla"}, None)
    assert (dst / "Internal.tla").read_text() == "v1\n"
