"""SI-28 — the bootstrap CLI has a floor, and the substrate says so.

THE DEFECT THIS COVERS IS NOT AN EXIT CODE. SI-22 measured a completely
successful install of this plugin exiting 11, filed it high-severity, and
diagnosed installer-side work still to be done. The remedy had already been
written and merged (skill-manager PR #397, 2026-09-23); it had simply never
been released, and `v0.28.1` — cut six days earlier — is what brew installed.

The defect is that a CLI six days older than the fix it depended on was
INDISTINGUISHABLE from a current one at every surface an agent can see. The
`cli-version` notification that already existed could not see it: it asks
brew what the newest release is, and brew's own formula cache was equally
stale, so it agreed the old CLI was current.

So these tests are about a purely local comparison against a number the
plugin declares, and — because this epic has already shipped a vacuous check
(`find` on an absent directory reporting "0 symlinks, ok") — about proving
the comparison FIRES as well as that it is silent.
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from skt import check as check_mod  # noqa: E402


# Derived here INDEPENDENTLY of `check.plugin_root()`, which is the thing
# under test — this file sits at <root>/skills/skt/tests/, three levels down,
# where check.py sits at <root>/skills/skt/src/skt/, five.
PLUGIN_ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture(autouse=True)
def _no_inherited_override(monkeypatch):
    """The falsification harness sets this env var. A leaked one would make
    every test below read somebody else's manifest."""
    monkeypatch.delenv(check_mod.FLOOR_MANIFEST_ENV, raising=False)


# --------------------------------------------------------------------------
# ONE place, and the sweep that proves it is one
# --------------------------------------------------------------------------


def test_the_plugin_declares_a_floor_and_skt_can_read_it():
    root = check_mod.plugin_root()
    assert root is not None, (
        "skt could not resolve the plugin root from its own __file__; the "
        "floor is unreadable in exactly the bootstrap session it exists for"
    )
    assert root == PLUGIN_ROOT

    floor = check_mod.bootstrap_floor()
    assert floor["state"] == "declared", floor
    assert check_mod._parse_version(floor["minimum"]) is not None
    assert floor["upgrade"]
    assert Path(floor["manifest"]) == PLUGIN_ROOT / check_mod.FLOOR_MANIFEST


def test_exactly_one_file_in_the_plugin_declares_the_floor():
    """ONE source of truth, swept for rather than asserted about.

    A second declaration is the failure this ticket is a consequence of:
    two places to look, one of them stale, and nothing saying which won.
    """
    # PRUNED, not filtered. `rglob` + a post-hoc `any(part in skipped)` walks
    # every directory anyway, and this repository carries a `.history` tree of
    # ~200 MB: the first version of this test spent minutes in it before
    # reaching its first assertion.
    skipped = {".git", ".history", "__pycache__", "build", "node_modules",
               ".skill-manager", ".gradle", ".venv", ".idea", "dist"}
    scanned = 0
    declaring: list[str] = []
    for dirpath, dirnames, filenames in os.walk(PLUGIN_ROOT):
        dirnames[:] = [d for d in dirnames if d not in skipped]
        for name in filenames:
            if not name.endswith(".toml"):
                continue
            path = Path(dirpath) / name
            try:
                text = path.read_text()
            except (OSError, UnicodeDecodeError):
                continue
            scanned += 1
            if "[skill_manager]" in text and "minimum" in text:
                declaring.append(str(path.relative_to(PLUGIN_ROOT)))

    # NON-VACUITY. An empty sweep is not a passing sweep: if the glob matched
    # nothing the assertion below would hold for the wrong reason.
    assert scanned > 5, f"the sweep read only {scanned} toml file(s) — it found nothing to check"
    assert declaring == [check_mod.FLOOR_MANIFEST], declaring


# --------------------------------------------------------------------------
# FIRES on old — the arm a check is worthless without
# --------------------------------------------------------------------------


def test_it_fires_against_the_cli_that_cost_six_days():
    """0.28.1 against a 0.28.2 floor: the exact historical case."""
    state = {
        "state": "ok", "installed": "0.28.1", "latest": "0.28.1",
        "local_build": False, "outdated": False,
        "floor": {"state": "declared", "minimum": "0.28.2",
                  "manifest": "/p/bootstrap-floor.toml",
                  "reason": "PR #397 landed in 0.28.2",
                  "upgrade": "brew update && brew upgrade skill-manager"},
        "below_floor": True,
    }
    notes = check_mod._floor_notification(state)
    assert len(notes) == 1
    note = notes[0]
    assert note["kind"] == "cli-floor"
    # Installed version, the floor, and where the floor is declared.
    assert "0.28.1" in note["message"] and "0.28.2" in note["message"]
    assert "bootstrap-floor.toml" in note["message"]
    assert note["fix"] == "brew update && brew upgrade skill-manager"

    # And note what `cli-version` says about the SAME state, which is the
    # whole reason this notification had to be added rather than reused:
    # brew reported 0.28.1 as newest, so it says nothing at all.
    assert check_mod._cli_notifications(state) == []


def test_the_floor_survives_a_brew_that_cannot_answer(monkeypatch):
    """`unknown-latest` — no brew, or a brew that did not answer.

    `cli-version` is silent here by design and correctly so. The floor is
    not: it needs no remote, no cache and no formula, and an install on a
    box with no brew at all is exactly where a stale CLI goes unnoticed.
    """
    monkeypatch.setattr(
        check_mod, "_installed_cli_identity",
        lambda home, timeout: ("0.28.1", "", "skill-manager 0.28.1 @ abc"),
    )
    monkeypatch.setattr(check_mod, "_brew_latest", lambda timeout: (None, "no brew here"))
    monkeypatch.setattr(
        check_mod, "bootstrap_floor",
        lambda root=None: {"state": "declared", "minimum": "0.28.2",
                           "manifest": "/p/bootstrap-floor.toml", "reason": None,
                           "upgrade": "brew update && brew upgrade skill-manager"},
    )
    import time as _t

    state = check_mod._cli_state(Path("/nonexistent-home"), _t.monotonic() + 30)
    assert state["state"] == "unknown-latest"
    assert state["below_floor"] is True
    assert check_mod._cli_notifications(state) == []      # brew could not say
    assert len(check_mod._floor_notification(state)) == 1  # the floor still can


def test_a_local_build_below_the_floor_still_fires():
    """A DELIBERATE DEPARTURE from the `cli-version` rule beside it.

    `cli-version` suppresses local builds because a branch build's base
    version says nothing about which commits it carries, so "you are behind"
    can be false. For a floor the same doubt cuts the other way: the question
    is whether a required fix is PRESENT, the base version is the only
    evidence there is, and silence is how six days passed. It fires, and the
    message says so in its own words.
    """
    state = {
        "state": "ok", "installed": "0.28.1+g08a1c00d4503", "latest": "0.28.2",
        "local_build": True, "outdated": False,
        "floor": {"state": "declared", "minimum": "0.28.2",
                  "manifest": "/p/bootstrap-floor.toml", "reason": None,
                  "upgrade": "brew update && brew upgrade skill-manager"},
        "below_floor": True,
    }
    notes = check_mod._floor_notification(state)
    assert len(notes) == 1
    assert "local build" in notes[0]["message"]
    assert check_mod._cli_notifications(state) == []


def test_the_env_override_reads_another_manifest(tmp_path, monkeypatch):
    """The falsification harness. A floor above the installed CLI exercises
    the fires-on-old arm end to end WITHOUT downgrading anybody's brew."""
    manifest = tmp_path / "bootstrap-floor.toml"
    manifest.write_text(
        '[skill_manager]\nminimum = "99.0.0"\n'
        'reason = "a floor no release clears"\n'
        'upgrade = "brew update && brew upgrade skill-manager"\n'
    )
    monkeypatch.setenv(check_mod.FLOOR_MANIFEST_ENV, str(manifest))
    floor = check_mod.bootstrap_floor()
    assert floor["state"] == "declared"
    assert floor["minimum"] == "99.0.0"
    assert Path(floor["manifest"]) == manifest


# --------------------------------------------------------------------------
# SILENT on current, and on every uncertainty
# --------------------------------------------------------------------------


def test_it_is_silent_against_a_current_cli():
    for installed in ("0.28.2", "0.29.0", "1.0.0"):
        state = {
            "state": "ok", "installed": installed, "latest": installed,
            "local_build": False, "outdated": False,
            "floor": {"state": "declared", "minimum": "0.28.2",
                      "manifest": "/p/bootstrap-floor.toml", "reason": None,
                      "upgrade": "brew update && brew upgrade skill-manager"},
            "below_floor": False,
        }
        assert check_mod._floor_notification(state) == [], installed


def test_the_installed_cli_clears_the_declared_floor():
    """The live arm, run against whatever this machine actually has.

    Skipped rather than failed when no skill-manager answers: "I could not
    find out" is not a verdict, and a test that fails on a box with no CLI
    teaches people to ignore it.
    """
    floor = check_mod.bootstrap_floor()
    assert floor["state"] == "declared"
    try:
        proc = subprocess.run(["skill-manager", "--version"],
                              capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired):
        pytest.skip("no skill-manager on PATH")
    if proc.returncode != 0:
        pytest.skip("skill-manager did not answer --version")
    line = (proc.stdout or "").strip().splitlines()[0]
    installed = check_mod._parse_version(line.split()[-1])
    assert installed is not None, line
    assert installed >= check_mod._parse_version(floor["minimum"]), (
        f"the CLI on PATH ({line}) is BELOW the floor this plugin declares "
        f"({floor['minimum']}) — the warning should be firing"
    )


def test_it_is_silent_on_every_uncertainty():
    declared = {"state": "declared", "minimum": "0.28.2",
                "manifest": "/p/bootstrap-floor.toml", "reason": None,
                "upgrade": "brew upgrade skill-manager"}
    # No floor declared at all.
    assert check_mod._floor_notification(
        {"state": "ok", "installed": "0.1.0", "below_floor": False,
         "floor": {"state": "absent", "reason": "not present"}}) == []
    # A floor file that would not parse.
    assert check_mod._floor_notification(
        {"state": "ok", "installed": "0.1.0", "below_floor": False,
         "floor": {"state": "unreadable", "manifest": "/p/x.toml",
                   "reason": "no readable minimum"}}) == []
    # The version probe was refused / timed out / found no pin: no installed
    # version means no comparison, and no comparison means no warning.
    assert check_mod._floor_notification(
        {"state": "no-cli", "reason": "this home has no skill-manager CLI pin"}) == []
    assert check_mod._floor_notification(
        {"state": "error", "reason": check_mod.CLI_REFUSED_PREFIX + "home mismatch"}) == []
    # `below_floor` unset is not `below_floor` true.
    assert check_mod._floor_notification({"state": "ok", "installed": "0.1.0",
                                          "floor": declared}) == []


def test_an_unreadable_floor_file_degrades_rather_than_raising(tmp_path, monkeypatch):
    """`skt check` is wired into a SessionStart hook. A typo in the floor
    file must become a typed `unreadable`, never a traceback in a session."""
    for body in ("[skill_manager\nminimum = 1", "[skill_manager]\nminimum = 3",
                 "[skill_manager]\nminimum = \"not.a.version\"", "# empty\n"):
        manifest = tmp_path / "bootstrap-floor.toml"
        manifest.write_text(body)
        monkeypatch.setenv(check_mod.FLOOR_MANIFEST_ENV, str(manifest))
        floor = check_mod.bootstrap_floor()
        assert floor["state"] == "unreadable", (body, floor)
        assert floor.get("minimum") is None

    monkeypatch.setenv(check_mod.FLOOR_MANIFEST_ENV, str(tmp_path / "absent.toml"))
    assert check_mod.bootstrap_floor()["state"] == "absent"


def test_non_string_prose_fields_do_not_raise(tmp_path, monkeypatch):
    """`reason = 3` is valid TOML, and `(3 or "").strip()` is an
    AttributeError — in a function wired into a SessionStart hook."""
    manifest = tmp_path / "bootstrap-floor.toml"
    manifest.write_text('[skill_manager]\nminimum = "0.28.2"\n'
                        'reason = 3\nupgrade = ["not", "a", "string"]\n')
    monkeypatch.setenv(check_mod.FLOOR_MANIFEST_ENV, str(manifest))
    floor = check_mod.bootstrap_floor()
    assert floor["state"] == "declared"
    assert floor["reason"] is None
    # A usable remedy survives a garbage one: the warning is worthless
    # without a command beside it.
    assert floor["upgrade"] == "brew upgrade skill-manager"
    note = check_mod._floor_notification(
        {"state": "ok", "installed": "0.28.1", "local_build": False,
         "floor": floor, "below_floor": True})
    assert len(note) == 1 and note[0]["fix"] == "brew upgrade skill-manager"


# --------------------------------------------------------------------------
# It WARNS. It refuses nothing.
# --------------------------------------------------------------------------


def test_the_warning_names_the_floor_the_remedy_and_that_nothing_was_refused():
    report = {
        "home": "/tmp/h", "tier": "root", "checked_units": ["a"],
        "notifications": [{
            "kind": "cli-floor", "installed": "0.28.1", "minimum": "0.28.2",
            "manifest": "/p/bootstrap-floor.toml",
            "message": ("skill-manager 0.28.1 is installed here, and this plugin "
                        "requires 0.28.2 or newer (bootstrap-floor.toml)"),
            "fix": "brew update && brew upgrade skill-manager",
        }],
    }
    text = check_mod.render_text(report)
    assert "    upgrade with: brew update && brew upgrade skill-manager" in text
    assert "nothing was refused" in text
    assert "/p/bootstrap-floor.toml" in text


def test_the_session_start_hook_exits_zero_while_the_floor_is_firing(tmp_path):
    """`GOAL-no-new-gates`: the warning must reach the session WITHOUT the
    session-start hook failing. The hook translates skt's notify code (10)
    into printed context and exit 0 — this asserts the translation, because
    the notify code is the only way the warning gets printed at all.
    """
    hook = PLUGIN_ROOT / "hooks" / "skt-session-start.sh"
    assert hook.is_file()
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    skt = fake_bin / "skt"
    # A stand-in skt that behaves exactly as the real one does with one
    # cli-floor notification pending: prints, and exits 10.
    skt.write_text(
        "#!/usr/bin/env bash\n"
        'case "$1" in\n'
        '  status) echo "skt status: tier root"; exit 0 ;;\n'
        '  check)\n'
        '    for a in "$@"; do [ "$a" = "--json" ] && '
        '{ echo \'{"cache_state": "missing"}\'; exit 10; }; done\n'
        '    echo "skt check: 1 notification(s), tier root"\n'
        '    echo "  skill-manager 0.28.1 is installed here, and this plugin requires 0.28.2"\n'
        '    exit 10 ;;\n'
        'esac\nexit 0\n'
    )
    skt.chmod(0o755)
    home = tmp_path / "home"
    (home / "bin" / "cli").mkdir(parents=True)
    (home / "bin" / "cli" / "skt").symlink_to(skt)

    proc = subprocess.run(
        ["bash", str(hook)], capture_output=True, text=True, timeout=60,
        env={"PATH": f"{fake_bin}:/usr/bin:/bin", "SKILL_MANAGER_HOME": str(home),
             "HOME": str(tmp_path)},
    )
    assert proc.returncode == 0, (proc.returncode, proc.stderr)
    assert "0.28.2" in proc.stdout, proc.stdout
