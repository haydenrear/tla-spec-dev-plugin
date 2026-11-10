"""bug-sweep BS-06: the ticket lifecycle against REAL git worktrees.

One regression per covered issue, each red on the epic base and green here:

* #183 — a worktree created with `ticket new --path <dir elsewhere>` is found
  and closed, with the close-out gate run, by `skt ticket close <T>`.
* #184 — a `[worktree] provision` hook declared in skill-project.toml runs
  once per `ticket new`, and a failing one makes `new` exit non-zero, naming it.
* #171 — a worktree whose `target` links into another checkout gets its own
  target/ instead.

The real `scripts/wt`, `new-change.sh`, `close-change.sh` and `lib.sh` run.
Only the skill-manager CLI (the gate) and bootstrap-home.sh are stand-ins.
"""

import os
import stat
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from skt import publish as publish_mod  # noqa: E402
from skt import ticket as ticket_mod  # noqa: E402

from test_epic_mode import epic_repo  # noqa: E402

GIT = ["git", "-c", "user.email=t@t", "-c", "user.name=t"]


@pytest.fixture(autouse=True)
def isolate(tmp_path, monkeypatch):
    monkeypatch.delenv("SKILL_MANAGER_HOME", raising=False)
    for var in ("GIT_ISSUE_WORKFLOW_SCRIPTS", "WT_BIN", "GIW_WT_BIN", "SKILL_GATES", "WT_DIRTY_OK"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("SKT_ROOT_HOME", str(tmp_path / "fake-root" / ".skill-manager"))
    monkeypatch.setenv("WT_FETCH", "0")
    monkeypatch.setattr(publish_mod, "edited_units", lambda *_: [])


def _exe(path: Path, body: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("#!/usr/bin/env bash\n" + body)
    path.chmod(path.stat().st_mode | stat.S_IEXEC)
    return path


def _commit(repo: Path, msg: str) -> None:
    subprocess.run([*GIT, "-C", str(repo), "add", "-A"], check=True)
    subprocess.run([*GIT, "-C", str(repo), "commit", "-q", "-m", msg], check=True)


def gate_cli(tmp_path: Path) -> tuple[Path, Path]:
    """A skill-manager whose `home close-out` is clean and logs each call."""
    log = tmp_path / "gate.log"
    cli = _exe(
        tmp_path / "bin" / "skill-manager",
        f'echo "$*" >> "{log}"\n'
        'case "$*" in\n'
        '  *"close-out --help"*) echo "  --into HOME" ;;\n'
        '  *"close-out"*) echo \'{"units": [], "blockers": []}\' ;;\n'
        "esac\n",
    )
    return cli, log


# ---------------------------------------------------------------- #183


def test_183_close_finds_a_declared_path_worktree_outside_the_parent(tmp_path, monkeypatch, capsys):
    repo = epic_repo(tmp_path)
    elsewhere = tmp_path / "volume" / "x"          # NOT the repo's parent dir
    elsewhere.mkdir(parents=True)
    declared = elsewhere / "wt-T"
    monkeypatch.chdir(repo)
    assert ticket_mod.epic_new("T", "epic/slug", str(declared)) == 0
    assert (declared / ".skill-manager").is_dir(), "the gate must have a home to check"

    cli, log = gate_cli(tmp_path)
    monkeypatch.setenv("SKILL_MANAGER_CLI", str(cli))
    capsys.readouterr()
    rc = ticket_mod.run("close", "T", start=repo)
    out = capsys.readouterr().out
    assert rc == 0, out
    assert not declared.exists(), "the worktree must be removed"
    calls = log.read_text() if log.exists() else ""
    assert "home close-out --home" in calls, "the close-out gate must have run"
    assert str(declared.resolve()) in calls or "wt-T" in calls
    branches = subprocess.run(["git", "-C", str(repo), "branch", "--list", "feature/T"],
                              capture_output=True, text=True).stdout
    assert "feature/T" in branches, "the branch outlives the worktree"


# ---------------------------------------------------------------- #184


def _declare_hook(repo: Path, body: str) -> Path:
    counter = repo.parent / "hook-runs.log"
    (repo / "skill-project.toml").write_text(
        '[worktree]\nprovision = "scripts/provision_worktree.sh"\n'
    )
    _exe(repo / "scripts" / "provision_worktree.sh",
         f'echo "$PWD" >> "{counter}"\n' + body)
    _commit(repo, "declare a provision hook")
    return counter


def test_184_hook_runs_once_through_ticket_new(tmp_path, monkeypatch, capsys):
    repo = epic_repo(tmp_path)
    counter = _declare_hook(repo, "touch .provisioned\n")
    monkeypatch.chdir(repo)
    monkeypatch.setenv("INTEGRATION_SKIP_HOME", "1")
    rc = ticket_mod.run("new", "H1", base="main", start=repo)
    out = capsys.readouterr().out
    assert rc == 0, out
    wt = Path(out.split("worktree   ", 1)[1].splitlines()[0].strip())
    assert counter.read_text().splitlines() == [str(wt.resolve())], "exactly once, in the worktree"
    assert (wt / ".provisioned").is_file()


def test_184_failing_hook_fails_ticket_new_and_names_it(tmp_path, monkeypatch, capsys):
    repo = epic_repo(tmp_path)
    _declare_hook(repo, "echo 'helm dependency build failed' >&2\nexit 3\n")
    monkeypatch.chdir(repo)
    monkeypatch.setenv("INTEGRATION_SKIP_HOME", "1")
    rc = ticket_mod.run("new", "H2", base="main", start=repo)
    out = capsys.readouterr().out
    assert rc != 0, out
    assert "scripts/provision_worktree.sh" in out, "the failure must name the hook"


def test_184_hook_runs_once_and_fails_loudly_through_declared_path(tmp_path, monkeypatch, capsys):
    repo = epic_repo(tmp_path)
    counter = _declare_hook(repo, '[ -n "$FAIL" ] && exit 4\ntrue\n')
    monkeypatch.chdir(repo)
    ok = tmp_path / "wt-H3"
    assert ticket_mod.epic_new("H3", "HEAD", str(ok)) == 0
    assert counter.read_text().splitlines() == [str(ok.resolve())]

    monkeypatch.setenv("FAIL", "1")
    capsys.readouterr()
    rc = ticket_mod.epic_new("H4", "HEAD", str(tmp_path / "wt-H4"))
    out = capsys.readouterr().out
    assert rc != 0
    assert "scripts/provision_worktree.sh" in out and "exit 4" in out


# ---------------------------------------------------------------- #171


def _commit_shared_target(repo: Path) -> Path:
    """A tracked `target` symlink to the main checkout's absolute target/."""
    shared = repo.parent / "main-target"
    shared.mkdir()
    (shared / "test-binary").write_text("built by the main checkout")
    os.symlink(shared, repo / "target")
    _commit(repo, "share target/ (the meta-harness DEF-503 shape)")
    return shared


def _assert_unshared(wt: Path, shared: Path) -> None:
    link = wt / "target"
    assert link.is_dir() and not link.is_symlink(), \
        f"{link} must be the worktree's own directory, not a link to {shared}"
    assert (shared / "test-binary").read_text() == "built by the main checkout"


def test_171_ticket_new_replaces_a_target_link_into_another_checkout(tmp_path, monkeypatch, capsys):
    repo = epic_repo(tmp_path)
    shared = _commit_shared_target(repo)
    monkeypatch.chdir(repo)
    monkeypatch.setenv("INTEGRATION_SKIP_HOME", "1")
    rc = ticket_mod.run("new", "S1", base="main", start=repo)
    out = capsys.readouterr().out
    assert rc == 0, out
    wt = Path(out.split("worktree   ", 1)[1].splitlines()[0].strip())
    _assert_unshared(wt, shared)


def test_171_declared_path_replaces_a_target_link_into_another_checkout(tmp_path, monkeypatch):
    repo = epic_repo(tmp_path)
    shared = _commit_shared_target(repo)
    monkeypatch.chdir(repo)
    wt = tmp_path / "wt-S2"
    assert ticket_mod.epic_new("S2", "HEAD", str(wt)) == 0
    _assert_unshared(wt, shared)


def test_171_a_target_link_inside_the_worktree_is_left_alone(tmp_path, monkeypatch):
    repo = epic_repo(tmp_path)
    (repo / "build-out").mkdir()
    (repo / "build-out" / ".keep").write_text("")
    os.symlink("build-out", repo / "target")
    _commit(repo, "a relative, worktree-local target link")
    monkeypatch.chdir(repo)
    wt = tmp_path / "wt-S3"
    assert ticket_mod.epic_new("S3", "HEAD", str(wt)) == 0
    assert (wt / "target").is_symlink(), "a link that stays inside the worktree is not shared"
