"""`skt sync <unit>` — bring a unit to the revision this home tracks, loudly.

What "the revision this home tracks" is depends on the tier (#181):

- a ROOT home tracks the unit's trunk, so this wraps
  `skill-manager sync <unit> --git-latest`;
- a PROJECT or WORKTREE home tracks the repository's `skill-project.toml`
  pin when it has one, so this holds the unit at that revision — through
  `skill-manager project resolve`, the same remedy `skt check` prints for
  pin drift — and never pulls past it. `--trunk` asks for the trunk
  anyway, and names the pin and lock files that move then invalidates.

A unit with no pin syncs to its trunk at every tier, as before.

Either way it closes the documented trap: sync over an unpushed commit
exits 0 and prints a full success report while the store stays on the old
gitHash. After the underlying command the installed record is re-read and
compared to the target (the remote tip, or the pin); a mismatch is
reported as a failure with the reason.

Which CLI runs is decided by `_cli` and always announced: the home's own
pin when it has one; otherwise — below root — the tier-above CLI run with
`--home=<this home>` (#182); and at ROOT a PATH `skill-manager`.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from . import check as check_mod
from . import context as ctx_mod
from . import homes
from . import relay as relay_mod


FETCH_TIMEOUT_SECONDS = 20


def _refresh_tracking_refs(store: Path | None) -> bool | None:
    """Move the store's `refs/remotes/*` up to the remote it just synced from.

    The underlying sync advances the CHECKOUT without necessarily moving
    the remote-tracking ref, so `@{upstream}..HEAD` is left non-empty
    even though every one of those commits is already published — and
    the very next `skt check` reads that ref and calls it unpushed work.
    Measured: `skt sync debugging` reported "now at 91909afc (matches
    remote tip)" and the check immediately after it said "debugging
    modified locally (ahead)" with rev-list = 2; a bare `git fetch` took
    it to 0. So the command that fixes staleness was manufacturing the
    false report, and this is where it stops.

    Bounded and advisory: None when there is nothing to fetch, True on
    success, False when the fetch failed — the sync itself already
    succeeded and must not be turned into a failure by a slow network.
    """
    if store is None or not (store / ".git").exists():
        return None
    proc = check_mod._run_git(
        ["git", "-C", str(store), "fetch", "--quiet", "--no-tags"],
        float(FETCH_TIMEOUT_SECONDS),
    )
    return proc is not None and proc.returncode == 0

def _pin(home: Path) -> Path:
    """Where a home keeps its own CLI pin, present or not."""
    return home / "bin" / "cli" / "skill-manager"


def _foreign_pin_owner(candidate: Path, home: Path) -> Path | None:
    """The home a `<home>/bin/cli/skill-manager` pin belongs to, if not `home`.

    A pin derives its home from its OWN location, so running another
    home's pin would silently write that home. `<home>/bin/cli` is on
    PATH inside every launched session, so this is reachable rather than
    theoretical.
    """
    try:
        parts = candidate.resolve().parts
    except OSError:
        return None
    if len(parts) < 4 or parts[-3:] != ("bin", "cli", "skill-manager"):
        return None
    owner = Path(*parts[:-3])
    try:
        return None if owner.resolve() == home.resolve() else owner
    except OSError:
        return owner


PIN_MARKER = "skill-manager:cli-pin"
_PIN_ASSIGNMENT = 'cli="${SKILL_MANAGER_CLI:-'


def _pinned_cli_of(shim: Path) -> Path | None:
    """The real CLI a `bin/cli/skill-manager` shim execs, or None.

    A shim binds the home it LIVES in and refuses (exit 79) a
    `SKILL_MANAGER_HOME` naming another one, so another home's shim
    cannot be pointed at this home for every verb (`project resolve` takes
    no `--home`). The build it pins can be: the shim writes it on one
    line, `cli="${SKILL_MANAGER_CLI:-<abs>}"`, whose shape
    bootstrap-home.sh already reads back the same way.
    """
    try:
        text = shim.read_text(errors="replace")
    except OSError:
        return None
    if PIN_MARKER not in text:
        return None
    for line in text.splitlines():
        line = line.strip()
        if line.startswith(_PIN_ASSIGNMENT) and line.endswith('}"'):
            target = Path(line[len(_PIN_ASSIGNMENT):-2])
            if target.is_file() and target != shim:
                return target
    return None


def _usable(candidate: Path) -> Path | None:
    """`candidate` as something that can serve ANY home: a shim's real CLI, or itself."""
    if not candidate.is_file():
        return None
    try:
        head = candidate.read_text(errors="replace")[:4096]
    except OSError:
        head = ""
    if PIN_MARKER in head:
        return _pinned_cli_of(candidate)
    return candidate


def _parent_checkout_home(root: Path) -> Path | None:
    """For a linked worktree, the home of the checkout it was made from."""
    if not ctx_mod.is_linked_worktree(root):
        return None
    common = ctx_mod._git("rev-parse", "--path-format=absolute", "--git-common-dir", cwd=root)
    if not common:
        return None
    return Path(common).parent / ".skill-manager"


def _tier_above_cli(home: Path, tier: str, root: Path) -> tuple[Path | None, str, str | None]:
    """#182: below root with no pin, use the CLI of the tier above — never refuse first.

    Onboarding never writes a project home's pin (skill-manager#376), so a
    project home with no `bin/cli/skill-manager` is the NORMAL state, and
    refusing there made every sync a hand-run `--home=` invocation. The
    tier above already names a correct build: the parent checkout's home
    (for a worktree), then the root home, then PATH. Whatever is chosen
    runs with `--home=<this home>`, and the caller announces it — a sync
    through someone else's CLI must never look like one through the pin.
    """
    pin = _pin(home)
    candidates: list[tuple[Path, str]] = []
    parent = _parent_checkout_home(root) if tier == "worktree" else None
    if parent is not None and parent.resolve() != home.resolve():
        candidates.append((_pin(parent), "the parent checkout's home"))
    candidates.append((_pin(homes.root_home()), "the root home"))
    found = shutil.which("skill-manager")
    if found:
        candidates.append((Path(found), "PATH"))
    for candidate, where in candidates:
        cli = _usable(candidate)
        if cli is None:
            continue
        via = f" (pinned by {candidate})" if cli != candidate else ""
        return (
            cli,
            f"the tier-above CLI {cli} from {where}{via}, with --home={home} "
            f"(this {tier}-tier home has no pinned CLI at {pin})",
            None,
        )
    return None, "", (
        f"skt sync: home CLI not found at {pin}, and no CLI is reachable from the tier above "
        f"(parent checkout home, root home {homes.root_home()}, or PATH)\n"
        f"fix:   install the CLI, or run `skill-manager home shims --home {home}` to pin one"
    )


def _cli(home: Path, tier: str, root: Path | None = None) -> tuple[Path | None, str, str | None]:
    """(cli, provenance, error) — the CLI this sync should run, and why.

    A home's own pin is always preferred: it names the exact build the
    home was materialized by, which is the reason the pin exists at all.
    But refusing outright when there is no pin makes `skt sync`
    unavailable at the ROOT tier of any home that never ran
    `skill-manager home shims` — the tier that most needs it, and the one
    where a brew/PATH `skill-manager` IS the operator's CLI. So the
    fallback is allowed at ROOT only. Below root, falling through to some
    other CLI is exactly the failure the pin exists to remove, and the
    tier above is where a correct pin already lives — so below root this
    uses THAT CLI with `--home` (#182) rather than refusing.

    The provenance string is returned rather than logged here so the
    caller always says which CLI ran — an unpinned sync must never look
    like a pinned one.
    """
    pin = _pin(home)
    if pin.is_file():
        return pin, f"this home's pinned CLI at {pin}", None
    if tier != "root":
        return _tier_above_cli(home, tier, root if root is not None else home.parent)
    found = shutil.which("skill-manager")
    if not found:
        return None, "", (
            f"skt sync: home CLI not found at {pin}, and no `skill-manager` on PATH\n"
            f"fix:   install the CLI, or run `skill-manager home shims` to pin one "
            f"into {home}"
        )
    candidate = Path(found)
    foreign = _foreign_pin_owner(candidate, home)
    if foreign is not None:
        return None, "", (
            f"skt sync: home CLI not found at {pin}, and the `skill-manager` on PATH "
            f"({candidate}) is another home's pin — running it would write {foreign}\n"
            f"fix:   run `skill-manager home shims` to pin a CLI into {home}"
        )
    return (
        candidate,
        f"PATH skill-manager at {candidate} (root tier; this home has no pinned CLI)",
        None,
    )


def _invalidated_by_trunk(home: Path, manifest: Path, pin: dict) -> list[str]:
    """The pin and lock files a trunk move leaves disagreeing with the home."""
    rows = [f"{manifest}  ({pin['alias']} revision = {pin['revision'][:8]})"]
    lock = home / "units.lock.toml"
    if lock.is_file():
        rows.append(f"{lock}  (resolved_sha follows the trunk, not the pin)")
    for project_lock in sorted((home / "projects").glob("*/project-lock.toml")):
        rows.append(f"{project_lock}  (resolved by `project resolve` at the pin)")
    return rows


def _run_cli(argv: list[str], home: Path, own_pin: bool) -> subprocess.CompletedProcess:
    from .publish import _cli_env  # livelock guard: strips SKILL_MANAGER_CLI

    env = _cli_env()
    if not own_pin:
        # A tier-above CLI defaults to whatever home the caller exported;
        # name this one explicitly so it cannot write any other.
        env["SKILL_MANAGER_HOME"] = str(home)
    return subprocess.run(argv, capture_output=True, text=True, env=env)


def _relay_failure(cli: Path, proc, home: Path, unit_name: str, argv: list[str]) -> int:
    from .publish import _refusal_fix

    relay_mod.emit(
        relay_mod.relay(
            relay_mod.label_for(cli),
            proc,
            reason=f"skt sync: the underlying command failed (exit {proc.returncode})",
            fix=f"{' '.join(argv)}   # run it yourself to see why",
            refusal_fix=_refusal_fix(home, f"skt sync {unit_name}"),
        )
    )
    return proc.returncode


def _hold_at_pin(unit, home: Path, tier: str, manifest: Path, pin: dict,
                 cli: Path, own_pin: bool) -> int:
    """#181: a project/worktree home syncs a pinned unit to the PIN, never past it."""
    name = unit.name
    want = pin["revision"]
    if check_mod._same_revision(unit.git_hash, want):
        print(
            f"skt sync: {name} is at {want[:8]}, the revision {manifest} pins — a {tier} "
            f"home tracks the repository's pin, not the unit's trunk; nothing to do.\n"
            f"skt sync: to move past the pin anyway: skt sync {name} --trunk"
        )
        return 0
    argv = [str(cli), "project", "resolve", "--project-dir", str(manifest.parent),
            "--skip-gateway"]
    print(
        f"skt sync: {name} is at {(unit.git_hash or '?')[:8]} but {manifest} pins "
        f"{want[:8]} — restoring the pin with `project resolve`, not pulling the trunk"
    )
    proc = _run_cli(argv, home, own_pin)
    if proc.returncode != 0:
        return _relay_failure(cli, proc, home, name, argv)
    after = {u.name: u for u in homes.read_units(home)}.get(name)
    if after and check_mod._same_revision(after.git_hash, want):
        print(f"skt sync: {name} now at {want[:8]} (matches the {manifest.name} pin)")
        return 0
    print(
        f"skt sync: WARNING — `project resolve` reported success but {name} is at "
        f"{((after.git_hash if after else None) or '?')[:8]} while {manifest} pins "
        f"{want[:8]}. Run `{' '.join(argv)}` yourself to see why."
    )
    return 11


def run(unit_name: str | None, *, start: str | Path = ".", trunk: bool = False) -> int:
    home = homes.find_home(start)
    if home is None:
        print("skt sync: no skill-manager home found")
        return 1
    if not unit_name:
        print("skt sync: name a unit (see `skt check` for which are stale)")
        return 1
    units = {u.name: u for u in homes.read_units(home)}
    unit = units.get(unit_name)
    if unit is None:
        print(f"skt sync: no installed unit named {unit_name!r}")
        return 1
    if not unit.change_managed:
        print(f"skt sync: {unit_name} has no git provenance; nothing to sync from")
        return 1
    root = ctx_mod.checkout_root(start)
    tier = ctx_mod.classify_tier(home, root)
    cli, provenance, error = _cli(home, tier, root)
    if cli is None:
        print(error)
        return 1
    own_pin = cli == _pin(home)
    print(f"skt sync: using {provenance}")

    manifest, pin_rows = (
        check_mod.manifest_pins(root) if tier != "root" else (None, [])
    )
    pin = check_mod._pin_for(unit, pin_rows) if pin_rows else None
    if pin is not None and manifest is not None and not trunk:
        return _hold_at_pin(unit, home, tier, manifest, pin, cli, own_pin)
    if pin is not None and manifest is not None:
        print(
            f"skt sync: --trunk moves {unit_name} past the {pin['revision'][:8]} pin; "
            f"these pins/locks will no longer describe this home:"
        )
        for row in _invalidated_by_trunk(home, manifest, pin):
            print(f"  invalidated: {row}")

    argv = [str(cli), "sync", unit_name, "--git-latest"]
    if not own_pin:
        argv.append(f"--home={home}")
    proc = _run_cli(argv, home, own_pin)
    if proc.returncode != 0:
        return _relay_failure(cli, proc, home, unit_name, argv)
    after = {u.name: u for u in homes.read_units(home)}.get(unit_name)
    store = check_mod._store_dir(home, unit)
    refreshed = _refresh_tracking_refs(store)
    tip = check_mod._remote_tip_safe(unit.origin, unit.git_ref)
    if after and tip and after.git_hash == tip:
        print(f"skt sync: {unit_name} now at {tip[:8]} (matches remote tip)")
        if refreshed is False:
            print(
                f"skt sync: WARNING — could not refresh the remote-tracking refs in "
                f"{store}, so `skt check` may report this unit as locally ahead. "
                f"By hand: git -C {store} fetch"
            )
        return 0
    if after and tip:
        print(
            f"skt sync: WARNING — sync reported success but the store is at "
            f"{(after.git_hash or '?')[:8]} while the remote tip is {tip[:8]}. "
            f"This is the silent-no-op trap: the usual cause is an unpushed commit "
            f"in the unit's source repo. Push there, then re-run skt sync {unit_name}."
        )
        return 11
    print(f"skt sync: {unit_name} synced; remote tip unverifiable (offline?)")
    return 0
