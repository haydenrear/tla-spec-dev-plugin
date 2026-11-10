import json
import os
import stat
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from skt import sync as sync_mod  # noqa: E402

from test_check import advance_upstream, make_unit_upstream, unit_record  # noqa: E402
from test_status import make_home, make_repo  # noqa: E402


@pytest.fixture(autouse=True)
def isolate_root_home(tmp_path, monkeypatch):
    monkeypatch.delenv("SKILL_MANAGER_HOME", raising=False)
    monkeypatch.setenv("SKT_ROOT_HOME", str(tmp_path / "fake-root" / ".skill-manager"))


def fake_cli(home: Path, body: str) -> None:
    """A stand-in home CLI whose sync behavior the test controls."""
    cli = home / "bin" / "cli" / "skill-manager"
    cli.parent.mkdir(parents=True, exist_ok=True)
    cli.write_text("#!/usr/bin/env bash\n" + body)
    cli.chmod(cli.stat().st_mode | stat.S_IEXEC)


def test_sync_success_verifies_against_remote_tip(tmp_path, capsys):
    repo = make_repo(tmp_path / "repo")
    bare, tip = make_unit_upstream(tmp_path, "alpha")
    home = make_home(repo, units={"alpha": unit_record(bare, tip)})
    new_tip = advance_upstream(bare, tmp_path)
    record = home / "installed" / "alpha.json"
    # the fake CLI "moves the store" by updating the installed record:
    fake_cli(
        home,
        f"python3 -c \"import json;p='{record}';d=json.load(open(p));"
        f"d['gitHash']='{new_tip}';json.dump(d,open(p,'w'))\"\n",
    )
    assert sync_mod.run("alpha", start=repo) == 0
    assert new_tip[:8] in capsys.readouterr().out


def test_sync_detects_silent_noop(tmp_path, capsys):
    repo = make_repo(tmp_path / "repo")
    bare, tip = make_unit_upstream(tmp_path, "alpha")
    home = make_home(repo, units={"alpha": unit_record(bare, tip)})
    advance_upstream(bare, tmp_path)
    fake_cli(home, "exit 0\n")  # exits green, moves nothing — the documented trap
    assert sync_mod.run("alpha", start=repo) == 11
    out = capsys.readouterr().out
    assert "silent-no-op trap" in out


def test_sync_unknown_unit(tmp_path, capsys):
    repo = make_repo(tmp_path / "repo")
    make_home(repo, units={})
    assert sync_mod.run("ghost", start=repo) == 1


def test_sync_propagates_cli_failure(tmp_path):
    repo = make_repo(tmp_path / "repo")
    bare, tip = make_unit_upstream(tmp_path, "alpha")
    home = make_home(repo, units={"alpha": unit_record(bare, tip)})
    fake_cli(home, "echo boom >&2; exit 7\n")
    assert sync_mod.run("alpha", start=repo) == 7


# --- skill-publisher-skill#15: the command that fixes staleness made it ------
#
# Measured live during ARTI-00: `skt sync debugging` reported
#   skt sync: debugging now at 91909afc (matches remote tip)
# and the very next `skt check` reported
#   debugging modified locally (ahead) — please sync with root ...
# with rev-list = 2. A bare `git fetch` took it to 0. So it is the sequence,
# not the state, that has to be tested: sync must LEAVE the remote-tracking
# ref correct, not merely arrive at the right commit.


def stale_advancing_cli(store: Path, bare: Path, record: Path, new_tip: str) -> str:
    """A CLI that advances the checkout the way the real one does.

    `git fetch <URL> <ref>` writes FETCH_HEAD and, because the URL is not
    a configured remote, updates no remote-tracking ref at all.
    """
    return (
        "set -e\n"
        f"git -C '{store}' fetch --no-tags --quiet '{bare}' main\n"
        f"git -C '{store}' reset --hard --quiet FETCH_HEAD\n"
        f"python3 -c \"import json;p='{record}';d=json.load(open(p));"
        f"d['gitHash']='{new_tip}';json.dump(d,open(p,'w'))\"\n"
    )


def rev_list_ahead(store: Path) -> int:
    out = subprocess.run(
        ["git", "-C", str(store), "rev-list", "--count", "@{upstream}..HEAD"],
        capture_output=True, text=True, check=True,
    )
    return int(out.stdout.strip())


def test_sync_then_check_does_not_claim_the_unit_is_ahead(tmp_path, monkeypatch, capsys):
    from skt import check as check_mod

    fake_root = tmp_path / "fake-root"
    repo = make_repo(fake_root / "anywhere")
    bare, tip = make_unit_upstream(tmp_path, "alpha")
    home = make_home(fake_root, units={"alpha": unit_record(bare, tip)})
    store = home / "skills" / "alpha"
    subprocess.run(["git", "clone", "-q", str(bare), str(store)], check=True)
    new_tip = advance_upstream(bare, tmp_path)
    fake_cli(home, stale_advancing_cli(store, bare, home / "installed" / "alpha.json", new_tip))
    monkeypatch.setenv("SKILL_MANAGER_HOME", str(home))

    assert sync_mod.run("alpha", start=repo) == 0
    assert f"now at {new_tip[:8]} (matches remote tip)" in capsys.readouterr().out

    # the sync half: the ref it was supposed to leave correct
    assert rev_list_ahead(store) == 0

    # and the check that immediately follows says nothing
    report = check_mod.collect(repo)
    assert all(n["kind"] != "sync-with-root" for n in report["notifications"]), report
    assert report["notifications"] == [], report

# --- skill-publisher-skill#14: the root tier has no pinned CLI ---------------
#
# `<home>/bin/cli/skill-manager` is written by `skill-manager home shims`. An
# operator root installed from brew that never ran it has no pin, so the hard
# refusal made `skt sync` unavailable at the one tier that publishes globally.
# The pin still wins where it exists, and the fallback is ROOT-only: below
# root, falling through to another CLI is the failure the pin exists to remove.


def prepend_path(monkeypatch, bindir: Path) -> None:
    """Put `bindir` FIRST on PATH, keeping the real one (git/bash/python3)."""
    monkeypatch.setenv("PATH", f"{bindir}{os.pathsep}{os.environ['PATH']}")


def path_cli(bindir: Path, body: str) -> Path:
    """A `skill-manager` on PATH — what a brew install leaves behind."""
    bindir.mkdir(parents=True, exist_ok=True)
    cli = bindir / "skill-manager"
    cli.write_text("#!/usr/bin/env bash\n" + body)
    cli.chmod(cli.stat().st_mode | stat.S_IEXEC)
    return cli


def moves_store(record: Path, to_hash: str) -> str:
    """A CLI body that does what a real sync does: advance the installed record."""
    return (
        f"python3 -c \"import json;p='{record}';d=json.load(open(p));"
        f"d['gitHash']='{to_hash}';json.dump(d,open(p,'w'))\"\n"
    )


def test_root_tier_falls_back_to_path_cli_and_says_so(tmp_path, monkeypatch, capsys):
    """Before #14 this printed `home CLI not found` and exited 1."""
    fake_root = tmp_path / "fake-root"
    repo = make_repo(fake_root / "anywhere")
    bare, tip = make_unit_upstream(tmp_path, "alpha")
    home = make_home(fake_root, units={"alpha": unit_record(bare, tip)})
    new_tip = advance_upstream(bare, tmp_path)
    cli = path_cli(tmp_path / "brew-bin", moves_store(home / "installed" / "alpha.json", new_tip))
    prepend_path(monkeypatch, cli.parent)
    assert not (home / "bin" / "cli" / "skill-manager").exists()

    assert sync_mod.run("alpha", start=repo) == 0
    out = capsys.readouterr().out
    assert f"skt sync: using PATH skill-manager at {cli}" in out
    assert "root tier; this home has no pinned CLI" in out
    assert new_tip[:8] in out


def test_home_pin_wins_over_path_and_is_named(tmp_path, monkeypatch, capsys):
    fake_root = tmp_path / "fake-root"
    repo = make_repo(fake_root / "anywhere")
    bare, tip = make_unit_upstream(tmp_path, "alpha")
    home = make_home(fake_root, units={"alpha": unit_record(bare, tip)})
    new_tip = advance_upstream(bare, tmp_path)
    fake_cli(home, moves_store(home / "installed" / "alpha.json", new_tip))
    # a PATH CLI that fails loudly if it is ever the one chosen
    other = path_cli(tmp_path / "brew-bin", "echo WRONG-CLI >&2; exit 9\n")
    prepend_path(monkeypatch, other.parent)

    assert sync_mod.run("alpha", start=repo) == 0
    pin = home / "bin" / "cli" / "skill-manager"
    assert f"skt sync: using this home's pinned CLI at {pin}" in capsys.readouterr().out


def test_root_tier_refuses_another_homes_pin_on_path(tmp_path, monkeypatch, capsys):
    """A foreign pin derives ITS home from its own location and would write it."""
    fake_root = tmp_path / "fake-root"
    repo = make_repo(fake_root / "anywhere")
    bare, tip = make_unit_upstream(tmp_path, "alpha")
    make_home(fake_root, units={"alpha": unit_record(bare, tip)})
    other_home = tmp_path / "some-project" / ".skill-manager"
    foreign = path_cli(other_home / "bin" / "cli", "exit 0\n")
    prepend_path(monkeypatch, foreign.parent)

    assert sync_mod.run("alpha", start=repo) == 1
    out = capsys.readouterr().out
    assert "is another home's pin" in out
    assert str(other_home) in out


def test_root_tier_with_no_cli_anywhere_names_both_remedies(tmp_path, monkeypatch, capsys):
    fake_root = tmp_path / "fake-root"
    repo = make_repo(fake_root / "anywhere")
    bare, tip = make_unit_upstream(tmp_path, "alpha")
    make_home(fake_root, units={"alpha": unit_record(bare, tip)})
    # a PATH with git/bash/python3 but deliberately no skill-manager
    monkeypatch.setenv("PATH", "/usr/bin:/bin")

    assert sync_mod.run("alpha", start=repo) == 1
    out = capsys.readouterr().out
    assert "no `skill-manager` on PATH" in out
    assert "home shims" in out


# --- BS-05 / #182: a project home with no pin uses the tier-above CLI --------
#
# Onboarding never writes a project home's `bin/cli/skill-manager`
# (skill-manager#376), so "no pin" is the NORMAL state of a project home, and
# the old refusal made every sync a hand-run `--home=` invocation. The CLI of
# the tier above now runs with `--home=<this home>`, and the output names it.


def recording_cli(bindir: Path, record: Path, to_hash: str, argv_log: Path) -> Path:
    """A CLI that logs its argv and its SKILL_MANAGER_HOME, then moves the record."""
    return path_cli(
        bindir,
        f'printf "%s\\n" "$*" >> \'{argv_log}\'\n'
        f'printf "HOME=%s\\n" "${{SKILL_MANAGER_HOME:-}}" >> \'{argv_log}\'\n'
        + moves_store(record, to_hash),
    )


def pin_shim(home: Path, real_cli: Path) -> Path:
    """A `bin/cli/skill-manager` shaped like the one `home shims` writes."""
    shim = home / "bin" / "cli" / "skill-manager"
    shim.parent.mkdir(parents=True, exist_ok=True)
    shim.write_text(
        "#!/usr/bin/env bash\n"
        "# skill-manager:cli-pin - generated by `skill-manager home shims`, do not edit.\n"
        "echo SHIM-WAS-EXECUTED-AGAINST-ITS-OWN-HOME >&2; exit 79\n"
        f'cli="${{SKILL_MANAGER_CLI:-{real_cli}}}"\n'
        'exec "$cli" "$@"\n'
    )
    shim.chmod(shim.stat().st_mode | stat.S_IEXEC)
    return shim


def test_project_home_without_a_pin_syncs_through_the_path_cli_and_names_it(
    tmp_path, monkeypatch, capsys
):
    """#182 acceptance. On the epic base this printed `home CLI not found` and exited 1."""
    repo = make_repo(tmp_path / "repo")
    bare, tip = make_unit_upstream(tmp_path, "alpha")
    home = make_home(repo, units={"alpha": unit_record(bare, tip)})
    new_tip = advance_upstream(bare, tmp_path)
    log = tmp_path / "argv.log"
    cli = recording_cli(tmp_path / "brew-bin", home / "installed" / "alpha.json", new_tip, log)
    prepend_path(monkeypatch, cli.parent)
    assert not (home / "bin" / "cli" / "skill-manager").exists()

    assert sync_mod.run("alpha", start=repo) == 0
    out = capsys.readouterr().out
    assert f"skt sync: using the tier-above CLI {cli} from PATH" in out
    assert f"--home={home}" in out
    assert "project-tier home has no pinned CLI" in out
    assert new_tip[:8] in out
    logged = log.read_text()
    assert f"sync alpha --git-latest --home={home}" in logged
    assert f"HOME={home}" in logged


def test_project_home_without_a_pin_prefers_the_root_homes_pinned_build(
    tmp_path, monkeypatch, capsys
):
    """The root pin names the build; its SHIM would refuse this home, its CLI does not."""
    repo = make_repo(tmp_path / "repo")
    bare, tip = make_unit_upstream(tmp_path, "alpha")
    home = make_home(repo, units={"alpha": unit_record(bare, tip)})
    new_tip = advance_upstream(bare, tmp_path)
    log = tmp_path / "argv.log"
    real = recording_cli(tmp_path / "pinned-build", home / "installed" / "alpha.json", new_tip, log)
    root_home = tmp_path / "fake-root" / ".skill-manager"
    shim = pin_shim(root_home, real)
    other = path_cli(tmp_path / "brew-bin", "echo WRONG-CLI >&2; exit 9\n")
    prepend_path(monkeypatch, other.parent)

    assert sync_mod.run("alpha", start=repo) == 0
    out = capsys.readouterr().out
    assert f"the tier-above CLI {real} from the root home (pinned by {shim})" in out
    assert f"sync alpha --git-latest --home={home}" in log.read_text()


def test_project_home_with_no_cli_anywhere_still_refuses_and_names_the_remedy(
    tmp_path, monkeypatch, capsys
):
    """The refusal survives only for the case where no CLI is reachable at all."""
    repo = make_repo(tmp_path / "repo")
    bare, tip = make_unit_upstream(tmp_path, "alpha")
    home = make_home(repo, units={"alpha": unit_record(bare, tip)})
    monkeypatch.setenv("PATH", "/usr/bin:/bin")

    assert sync_mod.run("alpha", start=repo) == 1
    out = capsys.readouterr().out
    assert str(home / "bin" / "cli" / "skill-manager") in out
    assert "no CLI is reachable from the tier above" in out
    assert f"home shims --home {home}" in out


# --- BS-05 / #181: a project home holds a pinned unit at the pin -------------
#
# `skt sync` used to wrap `sync --git-latest` at every tier, so in a project or
# worktree home it pulled the unit's TRUNK past the skill-project.toml pin —
# four unchosen plugin pin moves in commit-diff-context-parent #462. The pin is
# now what a project home syncs to; the trunk is `--trunk`, which says which
# pins and locks it leaves behind.


def write_pin(repo: Path, alias: str, source: str, revision: str) -> Path:
    manifest = repo / "skill-project.toml"
    manifest.write_text(
        '[project]\nname = "demo"\n\n'
        f'[skills.{alias}]\nsource = "{source}"\nrevision = "{revision}"\n'
    )
    return manifest


def pin_aware_cli(home: Path, store: Path, bare: Path, trunk: str, pin: str, log: Path) -> str:
    """A CLI where `sync --git-latest` goes to the TRUNK and `project resolve` to the PIN.

    Each verb moves the store's checkout AND the installed record, the way the
    real ones do, so HEAD is a literal git HEAD and not just a JSON field.
    """
    record = home / "installed" / "alpha.json"

    def move(to: str) -> str:
        return (
            f"  git -C '{store}' fetch --no-tags --quiet '{bare}' main\n"
            f"  git -C '{store}' reset --hard --quiet {to}\n"
            f"  python3 -c \"import json;p='{record}';d=json.load(open(p));"
            f"d['gitHash']='{to}';json.dump(d,open(p,'w'))\"\n"
        )

    return (
        "set -e\n"
        f'printf "%s\\n" "$*" >> \'{log}\'\n'
        'case "$1" in\n'
        f"sync)\n{move(trunk)}  ;;\n"
        f"project)\n{move(pin)}  ;;\n"
        "esac\n"
    )


def store_head(store: Path) -> str:
    return subprocess.run(
        ["git", "-C", str(store), "rev-parse", "HEAD"], capture_output=True, text=True, check=True
    ).stdout.strip()


def pinned_project(tmp_path):
    """Project home pinning alpha at commit A while the remote trunk is at B."""
    repo = make_repo(tmp_path / "repo")
    bare, commit_a = make_unit_upstream(tmp_path, "alpha")
    home = make_home(repo, units={"alpha": unit_record(bare, commit_a)})
    store = home / "skills" / "alpha"
    subprocess.run(["git", "clone", "-q", str(bare), str(store)], check=True)
    commit_b = advance_upstream(bare, tmp_path)
    manifest = write_pin(repo, "alpha", f"git+file://{bare}", commit_a)
    (home / "units.lock.toml").write_text(
        f'schema_version = 1\n\n[[units]]\nname = "alpha"\nresolved_sha = "{commit_a}"\n'
    )
    log = tmp_path / "argv.log"
    fake_cli(home, pin_aware_cli(home, store, bare, commit_b, commit_a, log))
    return repo, home, store, manifest, commit_a, commit_b, log


def installed_hash(home: Path) -> str:
    return json.loads((home / "installed" / "alpha.json").read_text())["gitHash"]


def test_project_home_sync_stays_at_the_pin_not_the_trunk(tmp_path, capsys):
    """#181 acceptance, half one. On the epic base HEAD moved to B."""
    repo, home, store, manifest, commit_a, commit_b, log = pinned_project(tmp_path)
    assert store_head(store) == commit_a

    assert sync_mod.run("alpha", start=repo) == 0
    out = capsys.readouterr().out
    assert store_head(store) == commit_a
    assert installed_hash(home) == commit_a
    assert f"the revision {manifest} pins" in out
    assert "skt sync alpha --trunk" in out
    assert not log.exists() or "--git-latest" not in log.read_text()


def test_project_home_sync_restores_a_drifted_unit_to_the_pin(tmp_path, capsys):
    """A unit already pulled past its pin is put BACK, through `project resolve`."""
    repo, home, store, manifest, commit_a, commit_b, log = pinned_project(tmp_path)
    record = home / "installed" / "alpha.json"
    data = json.loads(record.read_text())
    data["gitHash"] = commit_b
    record.write_text(json.dumps(data))

    assert sync_mod.run("alpha", start=repo) == 0
    out = capsys.readouterr().out
    assert store_head(store) == commit_a
    assert installed_hash(home) == commit_a
    assert f"project resolve --project-dir {repo}" in log.read_text()
    assert "--git-latest" not in log.read_text()
    assert f"now at {commit_a[:8]} (matches the skill-project.toml pin)" in out


def test_trunk_flag_moves_to_the_trunk_and_names_the_invalidated_pins(tmp_path, capsys):
    """#181 acceptance, half two. On the epic base `trunk=` did not exist."""
    repo, home, store, manifest, commit_a, commit_b, log = pinned_project(tmp_path)
    assert store_head(store) == commit_a

    assert sync_mod.run("alpha", start=repo, trunk=True) == 0
    out = capsys.readouterr().out
    assert store_head(store) == commit_b
    assert installed_hash(home) == commit_b
    assert f"--trunk moves alpha past the {commit_a[:8]} pin" in out
    assert f"invalidated: {manifest}  (alpha revision = {commit_a[:8]})" in out
    assert f"invalidated: {home / 'units.lock.toml'}" in out
    assert f"now at {commit_b[:8]} (matches remote tip)" in out


def test_trunk_flag_is_wired_into_the_cli(tmp_path):
    from skt import cli as cli_mod

    assert cli_mod.build_parser().parse_args(["sync", "alpha", "--trunk"]).trunk is True


# --- BS-05 / #178: `home sync --dry-run` and the destination lock ------------
#
# The reference said a dry run writes "nothing at all — no records, no lock
# file". skill-manager 0.28.2 creates no lock file when none exists, but when
# `<to>/.materialization/.home.lock` already exists it OPENS IT FOR WRITE to
# take the OS lock (HomeLock.acquireWithoutCreating -> acquire), so a session
# with no write permission on the parent home fails with
# `Operation not permitted`. The doc must state that requirement.

PROJECTS_MD = Path(__file__).resolve().parents[2] / "skill-manager" / "references" / "projects.md"


def _dry_run_bullet() -> str:
    text = PROJECTS_MD.read_text()
    start = text.index("- `--dry-run`", text.index("## Moving An Edit Up A Tier"))
    end = text.index("\n\n", start)
    return text[start:end]


def test_projects_md_dry_run_names_the_destination_lock_requirement():
    bullet = _dry_run_bullet()
    assert "no lock file." not in bullet, "the unqualified no-lock claim is the #178 mismatch"
    assert ".materialization/.home.lock" in bullet
    assert "write permission" in bullet
    assert "unit content" in bullet
