"""The plugin declares which skill-manager CLI it needs, in ONE place (SI-28).

`skills/skt/tests/test_cli_floor.py` asserts that the READER behaves — that
`skt check` fires against an older CLI and is silent against a current one.
This file asserts the other half, the one that lives at the plugin level: that
the DECLARATION is present, parseable, singular, and reachable from the layout
skt actually resolves it through.

The two halves are deliberately separate. skt is a contained skill with its own
repository (`haydenrear/skt`) and can be installed standalone, where there is no
plugin and no floor; the floor is a fact about THIS BUNDLE, so this bundle's own
suite is where its absence has to fail.

Why it needs a test at all. The defect SI-28 exists for is not an exit code — it
is that a skill-manager six days older than the fix this plugin depended on was
indistinguishable from a current one at every surface an agent can see. A floor
file that got renamed, emptied, or quietly duplicated would restore exactly that
condition while every other check stayed green, because nothing would be
comparing anything and silence is what "all clear" looks like here.

Nothing below refuses anything: they are pytest assertions in the repository
suite, with no `sys.exit` and no process exit of their own, and nothing here can
block a promotion (GOAL-no-new-gates).
"""

from __future__ import annotations

import os
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FLOOR = ROOT / "bootstrap-floor.toml"

# Directories whose contents are not this plugin's source. `.history` alone is
# ~200 MB of editor snapshots, and walking it turned the sweep below from a
# third of a second into minutes.
PRUNED = {".git", ".history", "__pycache__", "build", "node_modules",
          ".skill-manager", ".gradle", ".venv", ".idea", "dist", ".pytest_cache"}


def _floor_table() -> dict:
    return tomllib.loads(FLOOR.read_text())["skill_manager"]


def test_the_floor_is_declared_and_parses():
    assert FLOOR.is_file(), f"{FLOOR} is the plugin's ONE declaration of its skill-manager floor"
    table = _floor_table()
    minimum = table["minimum"]
    parts = minimum.split(".")
    assert 2 <= len(parts) <= 4 and all(p.isdigit() for p in parts), minimum
    # The warning has to be actionable without further reading, so the file
    # owns the remedy too.
    assert table.get("upgrade", "").strip(), "the floor must name an upgrade command"
    assert table.get("reason", "").strip(), "the floor must say what breaks below it"


def test_exactly_one_file_declares_a_floor():
    """ONE source of truth, swept for rather than asserted about.

    Two declarations — one of them stale, nothing saying which wins — is the
    shape of the problem this ticket is a consequence of.
    """
    scanned = 0
    declaring: list[str] = []
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in PRUNED]
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
                declaring.append(str(path.relative_to(ROOT)))

    # NON-VACUITY. An empty sweep is not a passing sweep — with `scanned == 0`
    # the assertion below would hold because nothing was read, which is the
    # failure mode this epic has already shipped once.
    assert scanned > 5, f"the sweep read only {scanned} toml file(s); it found nothing to check"
    assert declaring == ["bootstrap-floor.toml"], declaring


def test_the_floor_sits_where_skt_resolves_it_from():
    """skt reaches the floor from its OWN `__file__`, five parents up.

    That is the only route available in the situation the floor exists for — a
    bootstrap session with no home established yet, so no `SKILL_MANAGER_HOME`,
    no cwd it can trust and no installed record to read. The layout is
    identical in a development checkout and in an installed home
    (`<home>/plugins/tla-spec-dev/skills/skt/src/skt/check.py`), which is what
    makes the derivation safe — and what this asserts, so that moving either
    file fails here rather than silently returning None at bootstrap.
    """
    check_py = ROOT / "skills" / "skt" / "src" / "skt" / "check.py"
    assert check_py.is_file(), check_py
    assert check_py.resolve().parents[4] == ROOT.resolve()
    # `.claude-plugin/plugin.json` is skt's predicate for "this is a plugin
    # root" (it is what skill-manager itself detects a plugin by), so its
    # absence would make the floor unreadable while the file was still there.
    assert (ROOT / ".claude-plugin" / "plugin.json").is_file()


def test_the_floor_is_at_or_above_the_release_that_carries_the_fix():
    """0.28.2 is the release carrying skill-manager PR #397.

    SI-22 measured a successful install of this plugin exiting 11 on
    MarkdownImportValidator violations against eval fixtures; #397 is the fix,
    it merged 2026-09-23, and 0.28.1 — cut 2026-09-17 — predates it. A floor
    below 0.28.2 would be a floor that admits the exact CLI this ticket exists
    because of.
    """
    minimum = tuple(int(p) for p in _floor_table()["minimum"].split("."))
    assert minimum >= (0, 28, 2), minimum
