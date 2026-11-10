"""BS-21 (#203): the workflow close refuses an explicit `--result` it cannot find.

Before this fix `close_tickets.py` resolved a missing `--result`, recorded it
honestly as `exists: false`, and then went on to write the immutable closed
snapshot and remove `current/` and `desired_program_model/`. The evidence the
operator named was gone from the close for good.

Relative-path policy (unchanged, now documented in `--help` and tested here):
a relative `--result` is tried against the CALLER's working directory first;
when that misses and the path does not begin with the spec-root directory name,
it falls back to `<repo-root>/<spec-root>/<path>`. It is never resolved against
`--repo-root` by itself, so a caller in the wrong directory gets a refusal that
names the repo-root candidate instead of a silently re-anchored path.

Symlink / foreign-path policy (unchanged, tested): a symlink is followed and its
target is what is copied; a dangling symlink is missing. An absolute path outside
the repository is accepted and recorded by its absolute path.

Every case drives the real script in a subprocess over an isolated converged
workflow fixture, so the caller's directory is a real variable.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills" / "spec-double-2" / "scripts" / "close_tickets.py"
WORKFLOW = "retirement-workflow"


def _repo(tmp_path: Path) -> Path:
    from test_ticket_retirement import successful_terminal_fixture

    repo = tmp_path / "repo"
    repo.mkdir()
    successful_terminal_fixture(repo)
    results = repo / "specs" / "results"
    results.mkdir(parents=True, exist_ok=True)
    (results / "tlc.json").write_text('{"verdict": "pass"}\n', encoding="utf-8")
    (results / "cases.json").write_text('{"cases": 3}\n', encoding="utf-8")
    return repo


def _close(cwd: Path, repo: Path, *args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    full_env = {k: v for k, v in os.environ.items() if k not in {"SKILL_GATES", "SPEC_GATES"}}
    full_env.update(env or {})
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--repo-root", str(repo), "--summary", "bs-21", *args],
        cwd=cwd, capture_output=True, text=True, check=False, env=full_env,
    )


def _tree_digest(root: Path) -> dict[str, str]:
    if not root.exists():
        return {}
    return {
        path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def _state(repo: Path) -> dict[str, dict[str, str]]:
    specs = repo / "specs"
    return {name: _tree_digest(specs / name) for name in ("current", "desired_program_model", ".history", "program_model")}


def _closed(repo: Path) -> Path:
    return repo / "specs" / ".history" / WORKFLOW / "closed-snapshot"


def _results(repo: Path) -> list[dict]:
    return json.loads((_closed(repo) / "manifest.json").read_text(encoding="utf-8"))["results"]


def _assert_refused_untouched(result: subprocess.CompletedProcess[str], repo: Path, before: dict) -> str:
    output = result.stdout + result.stderr
    assert result.returncode != 0, output
    assert _state(repo) == before, "a refused close must leave current, desired and history untouched"
    assert (repo / "specs" / "current").is_dir()
    assert (repo / "specs" / "desired_program_model").is_dir()
    assert not _closed(repo).exists()
    return output


def test_explicit_missing_result_refuses_before_snapshot_or_removal(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    before = _state(repo)

    result = _close(repo, repo, "--result", "specs/results/absent.json")

    output = _assert_refused_untouched(result, repo, before)
    assert str((repo / "specs" / "results" / "absent.json").resolve()) in output
    assert "--force" in output and "exists=false" in output


def test_wrong_caller_directory_with_repo_root_refuses_and_names_the_repo_candidate(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    elsewhere = tmp_path / "primary-checkout"
    elsewhere.mkdir()
    before = _state(repo)

    result = _close(elsewhere, repo, "--result", "specs/results/tlc.json")

    output = _assert_refused_untouched(result, repo, before)
    caller_relative = str((elsewhere / "specs" / "results" / "tlc.json").resolve())
    repo_candidate = str((repo / "specs" / "results" / "tlc.json").resolve())
    assert caller_relative in output, "the refusal prints the path it actually resolved"
    assert f"--result {repo_candidate}" in output, "the refusal offers the safe correction"

    # The printed correction works, and binds the real result exactly once.
    fixed = _close(elsewhere, repo, "--result", repo_candidate)
    assert fixed.returncode == 0, fixed.stdout + fixed.stderr
    records = _results(repo)
    assert len(records) == 1 and records[0]["exists"] is True


def test_valid_relative_result_is_caller_relative_and_copied_once(tmp_path: Path) -> None:
    repo = _repo(tmp_path)

    result = _close(repo, repo, "--result", "specs/results/tlc.json")

    assert result.returncode == 0, result.stdout + result.stderr
    records = _results(repo)
    assert [r["exists"] for r in records] == [True]
    copied = list((_closed(repo) / "results").iterdir())
    assert [p.name for p in copied] == ["tlc.json"]
    assert copied[0].read_text(encoding="utf-8") == '{"verdict": "pass"}\n'
    assert not (repo / "specs" / "current").exists()


def test_relative_result_falls_back_to_the_spec_root_unchanged(tmp_path: Path) -> None:
    """Existing semantics: a path not starting with `specs/` falls back to <repo>/<spec-root>."""
    repo = _repo(tmp_path)
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()

    result = _close(elsewhere, repo, "--result", "results/tlc.json")

    assert result.returncode == 0, result.stdout + result.stderr
    assert [r["exists"] for r in _results(repo)] == [True]


def test_valid_absolute_result_from_any_directory(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()

    result = _close(elsewhere, repo, "--result", str(repo / "specs" / "results" / "tlc.json"))

    assert result.returncode == 0, result.stdout + result.stderr
    assert [r["exists"] for r in _results(repo)] == [True]


def test_several_results_with_one_missing_refuses_and_names_only_the_missing_one(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    before = _state(repo)

    result = _close(
        repo, repo,
        "--result", "specs/results/tlc.json",
        "--result", "specs/results/gone.json",
        "--result", "specs/results/cases.json",
    )

    output = _assert_refused_untouched(result, repo, before)
    assert "gone.json" in output
    assert "tlc.json" not in output and "cases.json" not in output


def test_symlink_is_followed_dangling_symlink_is_missing_foreign_path_is_accepted(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    results = repo / "specs" / "results"
    (results / "linked.json").symlink_to(results / "tlc.json")
    (results / "dangling.json").symlink_to(results / "never-written.json")
    foreign = tmp_path / "outside" / "foreign.json"
    foreign.parent.mkdir()
    foreign.write_text('{"foreign": true}\n', encoding="utf-8")
    before = _state(repo)

    dangling = _close(repo, repo, "--result", "specs/results/dangling.json")
    output = _assert_refused_untouched(dangling, repo, before)
    assert "dangling.json" in output

    ok = _close(repo, repo, "--result", "specs/results/linked.json", "--result", str(foreign))
    assert ok.returncode == 0, ok.stdout + ok.stderr
    records = _results(repo)
    assert [r["exists"] for r in records] == [True, True]
    assert records[1]["source"] == str(foreign.resolve())
    copied = _closed(repo) / "results"
    assert (copied / "tlc.json").read_text(encoding="utf-8") == '{"verdict": "pass"}\n'
    assert (copied / "foreign.json").is_file() and not (copied / "foreign.json").is_symlink()


def test_omitted_result_still_closes_with_no_result_records(tmp_path: Path) -> None:
    repo = _repo(tmp_path)

    result = _close(repo, repo)

    assert result.returncode == 0, result.stdout + result.stderr
    assert _results(repo) == []
    assert not (repo / "specs" / "current").exists()


def test_dry_run_refuses_a_missing_result_too(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    before = _state(repo)

    result = _close(repo, repo, "--dry-run", "--result", "specs/results/absent.json")

    _assert_refused_untouched(result, repo, before)


def test_dry_run_then_actual_close_binds_the_result_exactly_once(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    before = _state(repo)

    dry = _close(repo, repo, "--dry-run", "--result", "specs/results/tlc.json")
    assert dry.returncode == 0, dry.stdout + dry.stderr
    assert _state(repo) == before

    real = _close(repo, repo, "--result", "specs/results/tlc.json")
    assert real.returncode == 0, real.stdout + real.stderr
    assert len(_results(repo)) == 1
    assert [p.name for p in (_closed(repo) / "results").iterdir()] == ["tlc.json"]


def test_force_closes_and_records_the_missing_result_honestly(tmp_path: Path) -> None:
    repo = _repo(tmp_path)

    result = _close(repo, repo, "--force", "--result", "specs/results/absent.json")

    assert result.returncode == 0, result.stdout + result.stderr
    assert "WARNING (forced)" in result.stderr
    records = _results(repo)
    assert [r["exists"] for r in records] == [False]
    assert "snapshot" not in records[0]


def test_skill_gates_off_is_the_same_force_path(tmp_path: Path) -> None:
    repo = _repo(tmp_path)

    result = _close(repo, repo, "--result", "specs/results/absent.json", env={"SKILL_GATES": "off"})

    assert result.returncode == 0, result.stdout + result.stderr
    assert [r["exists"] for r in _results(repo)] == [False]
