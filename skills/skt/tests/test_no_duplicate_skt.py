"""A home must not carry skt twice. Regression guard, 2026-09-24.

`tla-spec-dev` CONTAINS skt. A home that also installs skt standalone
(`skills/skt`) or as its own plugin (`plugins/skt`) holds two copies, and every
single-rung resolver this epic has repaired picks whichever it finds first --
which is how `sktSurface` came to test a different repository for as long as it
did (SI-25-DF-06).

The shape had a detector for the DECLARATION and none for the INSTALLATION:
`_migration` regex-matched `[plugins.skt]` in a manifest while probing only
`skills/<n>` on disk, so it fired on the advice and never on its outcome.
Measured 2026-09-24: `plugins/skt` present in 24 ticket worktree homes, absent
from all four live homes -- the migration stopped creating it and never removed
what it had already created.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from skt.status import RETIRED_UNITS, _migration  # noqa: E402


def _home(tmp_path: Path) -> Path:
    home = tmp_path / ".skill-manager"
    (home / "skills").mkdir(parents=True)
    (home / "plugins" / "tla-spec-dev" / "skills" / "skt").mkdir(parents=True)
    return home


def test_skt_is_a_retired_unit():
    """If skt ever leaves this tuple the two probes below stop meaning anything."""
    assert "skt" in RETIRED_UNITS


def test_a_home_carrying_only_the_contained_copy_is_clean(tmp_path):
    """The NON-VACUITY CONTROL. Without it the two probes below would pass on a
    detector that flagged every home unconditionally."""
    home = _home(tmp_path)
    assert _migration(home, tmp_path) is None


def test_skt_installed_as_its_own_plugin_is_reported(tmp_path):
    """The shape that had no detector: `plugins/skt` beside the carrier."""
    home = _home(tmp_path)
    (home / "plugins" / "skt").mkdir()
    block = _migration(home, tmp_path)
    assert block is not None, "a second copy of skt was not reported at all"
    assert "skt" in block["as_plugin"]


def test_skt_installed_standalone_is_still_reported(tmp_path):
    """The shape that always had one; kept so the fix does not trade one for the other."""
    home = _home(tmp_path)
    (home / "skills" / "skt").mkdir()
    block = _migration(home, tmp_path)
    assert block is not None
    assert "skt" in block["standalone"]
