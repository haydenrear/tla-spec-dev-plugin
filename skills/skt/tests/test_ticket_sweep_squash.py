"""BS-25 (#225): squash-landed tickets, the index-base race, slow launchers.

Real git, as in test_ticket_sweep. The negative cases carry the weight: a
worktree whose work has not landed must never be removed, so every route
that admits a squash landing is paired with the branch that must stay
blocked.
"""

import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from skt import check as check_mod  # noqa: E402
from skt import sweep as sweep_mod  # noqa: E402
from skt import ticket as ticket_mod  # noqa: E402

from test_check import GIT  # noqa: E402
from test_epic_mode import epic_repo as bare_epic_repo, run_epic_new  # noqa: E402
from test_status import make_home, make_repo  # noqa: E402
from test_ticket_sweep import add_worktree, epic_repo, git, isolate  # noqa: E402,F401

PLAN = "specs/desired_program_model/ticket_plan.yaml"
PLAN_BODY = (
    "name: demo\ntickets:\n"
    "  - id: EP-1\n    github_issue: https://github.com/o/r/issues/201\n"
    "  - id: EP-2\n    github_issue: https://github.com/o/r/issues/202\n"
)


# ------------------------------------------------------------------ fixtures


def planned_repo(tmp_path) -> dict:
    repo = epic_repo(tmp_path)
    epic_wt = repo["root"].parent / "wt-epic-demo"
    git("worktree", "add", "-q", str(epic_wt), "epic/demo", cwd=repo["root"])
    plan = epic_wt / PLAN
    plan.parent.mkdir(parents=True)
    plan.write_text(PLAN_BODY)
    # Shared with the tickets, so a later epic commit can touch a line near theirs.
    (epic_wt / "shared.txt").write_text("".join(f"line {i}\n" for i in range(30)))
    git("add", "-A", cwd=epic_wt)
    git("commit", "-q", "-m", "plan", cwd=epic_wt)
    git("push", "-q", "origin", "epic/demo", cwd=epic_wt)
    return {**repo, "epic_wt": epic_wt}


def commit(path: Path, name: str, body: str, message: str = "work") -> None:
    target = path / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(body)
    git("add", "-A", cwd=path)
    git("commit", "-q", "-m", message, cwd=path)


def squash_into_epic(repo: dict, ticket: str) -> None:
    epic_wt = repo["epic_wt"]
    git("merge", "-q", "--squash", f"feature/{ticket}", cwd=epic_wt)
    git("commit", "-q", "-m", f"squash {ticket} (#1)", cwd=epic_wt)
    git("push", "-q", "origin", "epic/demo", cwd=epic_wt)


def ticket(repo: dict, name: str, *, body: str = "work\n", squash: bool = True) -> Path:
    path = add_worktree(repo, name, push=False)
    commit(path, f"{name}.txt", body)
    git("push", "-q", "-u", "origin", f"feature/{name}", cwd=path)
    if squash:
        squash_into_epic(repo, name)
    return path


def step_for(result, path: Path):
    return next(s for s in result.steps if s.path.resolve() == path.resolve())


def sweep_yes(repo: dict, **kwargs):
    return sweep_mod.sweep(start=repo["root"], yes=True, **kwargs)


# ------------------------------------------------------------ squash landings


def test_a_squashed_ticket_is_removed_and_says_how_it_landed(tmp_path):
    repo = planned_repo(tmp_path)
    path = ticket(repo, "201-alpha")
    result = sweep_yes(repo, epic="demo")
    step = step_for(result, path)
    assert step.action == "removed", step.reasons
    assert not path.exists()
    assert any("landed" in note for note in step.notes), step.notes


def test_a_multi_commit_ticket_later_edited_on_the_epic_lands_by_its_whole_change(tmp_path):
    """The path now differs on the epic, so only the whole-change match can admit it."""
    repo = planned_repo(tmp_path)
    path = add_worktree(repo, "201-alpha")
    commit(path, "a.txt", "one\n")
    commit(path, "a.txt", "one\ntwo\n")
    git("push", "-q", "-u", "origin", "feature/201-alpha", cwd=path)
    squash_into_epic(repo, "201-alpha")
    commit(repo["epic_wt"], "a.txt", "one\ntwo\nlater ticket\n")
    git("push", "-q", "origin", "epic/demo", cwd=repo["epic_wt"])

    status = sweep_mod.inspect(
        next(w for w in sweep_mod.list_worktrees(repo["root"]) if w.path.resolve() == path.resolve()), root=repo["root"], target="epic/demo"
    )
    assert status.clean, status.blockers
    assert "matches commit" in status.landed_by


def test_a_ticket_squashed_while_another_landed_nearby_is_still_found(tmp_path):
    repo = planned_repo(tmp_path)
    path = add_worktree(repo, "201-alpha")
    commit(path, "b.txt", "mine\n")
    git("push", "-q", "-u", "origin", "feature/201-alpha", cwd=path)
    commit(repo["epic_wt"], "c.txt", "someone else\n")
    squash_into_epic(repo, "201-alpha")
    result = sweep_yes(repo, epic="demo")
    assert step_for(result, path).action == "removed"


def test_a_squashed_ticket_whose_remote_branch_was_deleted_is_removed(tmp_path):
    """GitHub deletes the head branch on merge; `pushed` must not then block."""
    repo = planned_repo(tmp_path)
    path = ticket(repo, "201-alpha")
    git("push", "-q", "origin", "--delete", "feature/201-alpha", cwd=path)
    git("fetch", "-q", "--prune", "origin", cwd=repo["root"])
    result = sweep_yes(repo, epic="demo")
    step = step_for(result, path)
    assert step.action == "removed", step.reasons


# ---------------------------------------------------- what must stay blocked


def assert_blocked(result, path: Path, needle: str = "not contained") -> None:
    step = step_for(result, path)
    assert step.action == "skipped", (step.action, step.reasons)
    assert any(needle in reason for reason in step.reasons), step.reasons
    assert path.exists()


def test_a_commit_added_after_the_squash_stays_blocked(tmp_path):
    repo = planned_repo(tmp_path)
    path = ticket(repo, "201-alpha")
    commit(path, "extra.txt", "not landed\n", "after the squash")
    git("push", "-q", "origin", "feature/201-alpha", cwd=path)  # pushed, so only landing decides
    assert_blocked(sweep_yes(repo, epic="demo"), path)


def test_an_unpushed_commit_added_after_the_squash_stays_blocked(tmp_path):
    repo = planned_repo(tmp_path)
    path = ticket(repo, "201-alpha")
    commit(path, "extra.txt", "not landed\n", "after the squash")
    result = sweep_yes(repo, epic="demo")
    step = step_for(result, path)
    assert step.action == "skipped"
    assert any("not pushed" in r for r in step.reasons), step.reasons
    assert any("not contained" in r for r in step.reasons), step.reasons
    assert path.exists()


def test_an_edit_to_an_already_squashed_file_stays_blocked(tmp_path):
    """Same path as the landed change: the new content is what has not landed."""
    repo = planned_repo(tmp_path)
    path = ticket(repo, "201-alpha")
    commit(path, "201-alpha.txt", "work\nand more\n", "after the squash")
    git("push", "-q", "origin", "feature/201-alpha", cwd=path)
    assert_blocked(sweep_yes(repo, epic="demo"), path)


def test_different_content_under_the_same_branch_name_stays_blocked(tmp_path):
    repo = planned_repo(tmp_path)
    path = ticket(repo, "201-alpha", body="the ticket's content\n", squash=False)
    # The epic took something else for the same path, under a matching message.
    commit(repo["epic_wt"], "201-alpha.txt", "somebody else's content\n", "feature/201-alpha (#1)")
    git("push", "-q", "origin", "epic/demo", cwd=repo["epic_wt"])
    assert_blocked(sweep_yes(repo, epic="demo"), path)


def test_a_whitespace_only_difference_is_different_content(tmp_path):
    """`git patch-id` ignores whitespace; in Python, that is the whole change."""
    repo = planned_repo(tmp_path)
    path = ticket(repo, "201-alpha", body="if x:\n    y()\n", squash=False)
    commit(repo["epic_wt"], "201-alpha.txt", "if x:\ny()\n", "landed without the indent")
    # Moved on afterwards, so the path differs and only the fingerprint could admit it.
    commit(repo["epic_wt"], "201-alpha.txt", "if x:\ny()\nz()\n", "later")
    git("push", "-q", "origin", "epic/demo", cwd=repo["epic_wt"])
    assert_blocked(sweep_yes(repo, epic="demo"), path)


def test_a_binary_change_with_different_bytes_stays_blocked(tmp_path):
    repo = planned_repo(tmp_path)
    path = add_worktree(repo, "201-alpha")
    (path / "b.bin").write_bytes(b"\x00\x01ours")
    git("add", "-A", cwd=path)
    git("commit", "-q", "-m", "binary", cwd=path)
    git("push", "-q", "-u", "origin", "feature/201-alpha", cwd=path)
    (repo["epic_wt"] / "b.bin").write_bytes(b"\x00\x01theirs")
    git("add", "-A", cwd=repo["epic_wt"])
    git("commit", "-q", "-m", "binary", cwd=repo["epic_wt"])
    commit(repo["epic_wt"], "other.txt", "moved on\n", "later")
    git("push", "-q", "origin", "epic/demo", cwd=repo["epic_wt"])
    assert_blocked(sweep_yes(repo, epic="demo"), path)


def test_a_net_empty_branch_is_no_evidence_of_landing(tmp_path):
    repo = planned_repo(tmp_path)
    path = add_worktree(repo, "201-alpha")
    commit(path, "a.txt", "x\n")
    git("rm", "-q", "a.txt", cwd=path)
    git("commit", "-q", "-m", "undo", cwd=path)
    git("push", "-q", "-u", "origin", "feature/201-alpha", cwd=path)
    assert_blocked(sweep_yes(repo, epic="demo"), path)


def test_a_squash_only_on_an_unpushed_local_epic_keeps_the_pushed_gate(tmp_path):
    repo = planned_repo(tmp_path)
    path = add_worktree(repo, "201-alpha")
    commit(path, "a.txt", "x\n")
    # Never pushed; landed only on a local epic commit no remote has.
    git("merge", "-q", "--squash", "feature/201-alpha", cwd=repo["epic_wt"])
    git("commit", "-q", "-m", "local squash", cwd=repo["epic_wt"])
    result = sweep_yes(repo, epic="demo")
    assert_blocked(result, path, "not pushed")


def test_an_unmerged_ticket_stays_blocked(tmp_path):
    repo = planned_repo(tmp_path)
    path = ticket(repo, "201-alpha", squash=False)
    assert_blocked(sweep_yes(repo, epic="demo"), path)


# ----------------------------------------------- plan removed, epic deleted


def test_plan_removed_from_the_tip_still_declares_squashed_tickets(tmp_path):
    repo = planned_repo(tmp_path)
    path = ticket(repo, "201-alpha")
    git("rm", "-q", PLAN, cwd=repo["epic_wt"])
    git("commit", "-q", "-m", "finalize: remove the plan", cwd=repo["epic_wt"])
    git("push", "-q", "origin", "epic/demo", cwd=repo["epic_wt"])

    declared = sweep_mod.epic_declared_tickets(repo["root"], "epic/demo")
    assert declared is not None and declared.historical
    assert declared.declares("201-alpha")
    assert step_for(sweep_yes(repo, epic="demo"), path).action == "removed"


def test_a_historical_plan_does_not_admit_undeclared_worktrees(tmp_path):
    repo = planned_repo(tmp_path)
    other = add_worktree(repo, "300-unrelated", base="main")
    git("rm", "-q", PLAN, cwd=repo["epic_wt"])
    git("commit", "-q", "-m", "finalize", cwd=repo["epic_wt"])
    git("push", "-q", "origin", "epic/demo", cwd=repo["epic_wt"])
    assert step_for(sweep_yes(repo, epic="demo"), other).action == "excluded"
    assert other.exists()


def test_a_tip_plan_still_outranks_history(tmp_path):
    repo = planned_repo(tmp_path)
    declared = sweep_mod.epic_declared_tickets(repo["root"], "epic/demo")
    assert declared is not None and not declared.historical


def test_a_deleted_epic_branch_names_the_route_that_works(tmp_path):
    repo = planned_repo(tmp_path)
    path = ticket(repo, "201-alpha")
    root = repo["root"]
    git("merge", "-q", "--no-ff", "-m", "merge epic", "epic/demo", cwd=root)
    git("push", "-q", "origin", "main", cwd=root)
    git("worktree", "remove", "--force", str(repo["epic_wt"]), cwd=root)
    git("branch", "-qD", "epic/demo", cwd=root)
    git("push", "-q", "origin", "--delete", "epic/demo", cwd=root)
    git("fetch", "-q", "--prune", "origin", cwd=root)

    refused = sweep_mod.sweep(start=root, epic="demo", yes=True)
    assert refused.exit_code == sweep_mod.EXIT_FAILED
    assert "--target" in refused.plan.fix
    assert path.exists()

    # …and the route it names does retire the landed ticket.
    result = sweep_yes(repo, target="origin/main")
    assert step_for(result, path).action == "removed"


def test_target_route_keeps_an_unlanded_ticket_when_the_epic_is_gone(tmp_path):
    repo = planned_repo(tmp_path)
    landed = ticket(repo, "201-alpha")
    unlanded = ticket(repo, "202-beta", squash=False)
    root = repo["root"]
    git("merge", "-q", "--no-ff", "-m", "merge epic", "epic/demo", cwd=root)
    git("push", "-q", "origin", "main", cwd=root)
    result = sweep_yes(repo, target="origin/main")
    assert step_for(result, landed).action == "removed"
    assert_blocked(result, unlanded)


# ------------------------------------------------------- the index-base race


def _lose_the_create_race(monkeypatch, repo: Path, winner_oid: str | None = None) -> list:
    """Make another `skt ticket new` create the ref just before ours does."""
    real_run = subprocess.run
    raced: list[str] = []

    def racing_run(args, *a, **k):
        if list(args[:2]) == ["git", "update-ref"] and args[2].startswith("refs/index-bases/"):
            oid = winner_oid or args[3]
            real_run(["git", "-C", str(repo), "update-ref", args[2], oid], check=True)
            raced.append(args[2])
        return real_run(args, *a, **k)

    monkeypatch.setattr(subprocess, "run", racing_run)
    return raced


def test_ticket_new_survives_losing_the_retention_ref_race(tmp_path, monkeypatch, capsys):
    repo = bare_epic_repo(tmp_path)
    raced = _lose_the_create_race(monkeypatch, repo)
    declared = tmp_path / "wt-7-slug"
    rc = run_epic_new(repo, "7-slug", declared, base="epic/slug")
    assert raced, "the race was never exercised"
    assert rc == 0, capsys.readouterr().out
    assert declared.is_dir()


def test_ticket_new_refuses_when_the_race_winner_pinned_another_commit(tmp_path, monkeypatch, capsys):
    repo = bare_epic_repo(tmp_path)
    other = subprocess.run(
        [*GIT, "-C", str(repo), "commit-tree", "HEAD^{tree}", "-m", "other"],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    _lose_the_create_race(monkeypatch, repo, winner_oid=other)
    declared = tmp_path / "wt-8-slug"
    assert run_epic_new(repo, "8-slug", declared, base="epic/slug") == 1
    out = capsys.readouterr().out
    assert "retention ref" in out and other[:8] in out
    assert not declared.exists()


def test_ticket_new_inside_repo_refusal_no_longer_claims_close_cannot_find_it(
    tmp_path, monkeypatch, capsys
):
    repo = bare_epic_repo(tmp_path)
    rc = run_epic_new(repo, "9-slug", repo / "wt-9-slug", base="epic/slug")
    out = capsys.readouterr().out
    assert rc == 1
    assert "close searches" not in out and "cannot find" not in out
    assert "untracked" in out, "the refusal must name the problem that remains"
    assert "--path ../wt-9-slug" in out


# ---------------------------------------------------------- the slow launcher


def _slow_pin(home: Path, body: str) -> Path:
    pin = home / "bin" / "cli" / "skill-manager"
    pin.parent.mkdir(parents=True, exist_ok=True)
    pin.write_text(body)
    pin.chmod(0o755)
    return pin


JBANG_WRAPPER = '#!/usr/bin/env bash\nsleep 30\nexec jbang "$DIR/SkillManager.java" "$@"\n'


def _home_for_check(tmp_path) -> Path:
    return make_home(make_repo(tmp_path / "repo"), units={})


def _probe(monkeypatch, home: Path) -> dict:
    monkeypatch.setattr(check_mod, "CLI_VERSION_BUDGET_SECONDS", 0.3)
    return check_mod._cli_state(home, time.monotonic() + 30)


def test_check_reports_a_jbang_launcher_that_misses_its_budget_as_unmeasured(tmp_path, monkeypatch):
    home = _home_for_check(tmp_path)
    _slow_pin(home, JBANG_WRAPPER)
    started = time.monotonic()
    state = _probe(monkeypatch, home)
    assert time.monotonic() - started < 10, "the budget itself must not be raised"
    assert state["state"] == "slow-launcher", state
    assert "jbang" in state["reason"] and "not measured" in state["reason"]
    assert "re-writes the pin" not in state["fix"], "the pin is fine"


def test_check_follows_a_home_pin_to_its_jbang_wrapper(tmp_path, monkeypatch):
    home = _home_for_check(tmp_path)
    wrapper = tmp_path / "checkout" / "skill-manager"
    wrapper.parent.mkdir()
    wrapper.write_text(JBANG_WRAPPER)
    wrapper.chmod(0o755)
    _slow_pin(
        home,
        "#!/usr/bin/env bash\n# skill-manager:cli-pin\n"
        f'cli="${{SKILL_MANAGER_CLI:-{wrapper}}}"\nexec "$cli" "$@"\n',
    )
    assert _probe(monkeypatch, home)["state"] == "slow-launcher"


def test_check_build_line_names_the_slow_launcher(tmp_path, monkeypatch):
    home = _home_for_check(tmp_path)
    _slow_pin(home, JBANG_WRAPPER)
    state = _probe(monkeypatch, home)
    line = check_mod._build_line({"skt_version": "1", "cli": state})
    assert "slow-launcher" in line and "(timeout)" not in line


def test_check_still_calls_a_hung_ordinary_cli_a_timeout(tmp_path, monkeypatch):
    home = _home_for_check(tmp_path)
    _slow_pin(home, "#!/bin/sh\nsleep 30\n")
    state = _probe(monkeypatch, home)
    assert state["state"] == "timeout", state
