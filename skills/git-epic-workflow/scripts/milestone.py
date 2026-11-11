#!/usr/bin/env python3
"""Run an epic milestone's test graphs under one lock and report per graph.

Issue #147 step 1 (BS-14). Replaces the hand-kept per-epic ``milestone.sh``
whose failures this script is shaped around:

* a 4.1 h deadlock: an ancestor process held the graph lock and the child
  waited on it forever. Here the lock records its owner's pid; a dead owner's
  lock is reclaimed and reported, and a live ANCESTOR owner is refused at once
  (exit 2) instead of waited on;
* ``./`` paths that ran nothing and read as green: a milestone with no graphs
  configured exits 2, never 0;
* a lost exec bit read as "default red": the runner is started with the
  current interpreter, never exec'd, and a runner that cannot start, or a run
  that leaves no ``outcome.json``, is ERRORED, not FAILED;
* graph lists hardcoded per epic: the sets come from the consuming repo's
  config.

Config (TOML, a ``[milestone]`` table; default ``<repo>/epic-workflow.toml``,
override with ``--config`` or ``MILESTONE_CONFIG``)::

    [milestone]
    default = ["cliWorkflow", "specWorkflow"]   # run first
    shared  = ["loadTest"]                      # run only after default is green
    runner  = "skills/test-graph/scripts/run.py"  # optional; relative to the repo
    test_graph_root = "test_graph"              # optional; passed as -R
    lock    = "build/milestone.lock"            # optional; relative to the repo

Each set runs as ONE ``run.py`` invocation. The runner's ``outcome.json`` (the
path on its last stdout line) is the only verdict read; a graph absent from it,
or a missing/unparseable ``outcome.json``, counts as errored.

Selection: no positional graphs runs ``default`` then ``shared``. Positional
graphs (each must be configured) restrict the run to those -- a targeted rerun.
A shared graph runs only when the default set is green: green in this
invocation when default graphs were selected, otherwise green in the last
recorded milestone (``<lock dir>/milestone-last.json``).

Exit codes: 0 every selected graph passed; 1 a graph failed or did not run
(including a shared graph skipped because default was not green); 3 a graph
errored and none failed; 2 the run was refused (lock held, ancestor re-entry,
no graphs configured, bad config).

Every gate yields to ``--force`` or ``SKILL_GATES=off``: a live lock is taken
over (an ancestor's is left in place and the run proceeds unlocked), shared
graphs run although default is not green, and an empty milestone exits 0 with
a warning.
"""
from __future__ import annotations

import argparse
import codecs
from contextlib import ExitStack
import hashlib
import json
import os
import selectors
import socket
import subprocess
import sys
import time
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from evidence import EvidenceError, atomic_document, binding_identity, file_digest, read_document

EXIT_PASSED, EXIT_FAILED, EXIT_REFUSED, EXIT_ERRORED = 0, 1, 2, 3
CONFIG_ENV = "MILESTONE_CONFIG"
DEFAULT_CONFIG = "epic-workflow.toml"
DEFAULT_LOCK = "build/milestone.lock"
LAST_RECORD = "milestone-last.json"
STATUSES = ("passed", "failed", "errored", "not_run")


class Refused(Exception):
    """A gate refused the run (exit 2)."""


def gates_off(force: bool) -> bool:
    return force or os.environ.get("SKILL_GATES", "").lower() == "off"


# --------------------------------------------------------------------------- config

def repo_root(start: Path) -> Path:
    try:
        out = subprocess.run(["git", "-C", str(start), "rev-parse", "--show-toplevel"],
                             capture_output=True, text=True, check=True).stdout.strip()
        return Path(out)
    except (OSError, subprocess.CalledProcessError):
        return start


def load_config(path: Path) -> dict:
    import tomllib  # Config parsing needs 3.11; lock helpers remain importable on 3.10.
    if not path.is_file():
        raise Refused(f"no milestone config at {path}: declare a [milestone] table "
                      f"(see references/human-review.md) or pass --config")
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        raise Refused(f"{path}: not valid TOML: {exc}") from exc
    table = data.get("milestone")
    if not isinstance(table, dict):
        raise Refused(f"{path}: no [milestone] table")
    cfg = {"default": [], "shared": []}
    for key in ("default", "shared"):
        value = table.get(key, [])
        if not isinstance(value, list) or not all(isinstance(g, str) and g for g in value):
            raise Refused(f"{path}: milestone.{key} must be a list of graph names")
        cfg[key] = list(dict.fromkeys(value))
    environment = table.get("environment", {})
    if not isinstance(environment, dict) or set(environment) - {"default", "shared"}:
        raise Refused(f"{path}: milestone.environment names default and shared sets")
    cfg["environment"] = {}
    for phase in ("default", "shared"):
        values = environment.get(phase, {})
        if not isinstance(values, dict) or len(values) > 256 or not all(
                isinstance(k, str) and k and "=" not in k and isinstance(v, str)
                for k, v in values.items()):
            raise Refused(f"{path}: phase environment must be a bounded string map")
        cfg["environment"][phase] = values
    cfg["identity"] = table.get("identity", {})
    if not isinstance(cfg["identity"], dict):
        raise Refused(f"{path}: milestone.identity must be a table")
    for key in ("runner", "test_graph_root", "lock"):
        if key in table and not isinstance(table[key], str):
            raise Refused(f"{path}: milestone.{key} must be a string")
        cfg[key] = table.get(key)
    return cfg


def resolve_runner(cfg: dict, root: Path, override: str | None) -> Path | None:
    if override or cfg.get("runner"):
        p = Path(override or cfg["runner"]).expanduser()
        return p if p.is_absolute() else root / p
    homes = [os.environ.get("SKILL_MANAGER_HOME"), str(root / ".skill-manager"),
             str(Path.home() / ".skill-manager")]
    for home in filter(None, homes):
        h = Path(home)
        candidates = [h / "skills/test-graph/scripts/run.py",
                      *sorted(h.glob("plugins/*/skills/test-graph/scripts/run.py"))]
        for c in candidates:
            if c.is_file():
                return c
    return None


# --------------------------------------------------------------------------- lock

def _ps(pid: int, field: str) -> str | None:
    try:
        out = subprocess.run(["ps", "-o", f"{field}=", "-p", str(pid)],
                             capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return None
    if out.returncode != 0:
        return None
    return out.stdout.strip() or None


def pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def process_start_epoch(pid: int) -> float | None:
    raw = _ps(pid, "lstart")
    if not raw:
        return None
    try:
        return time.mktime(time.strptime(" ".join(raw.split()), "%a %b %d %H:%M:%S %Y"))
    except ValueError:
        return None


def ancestors(pid: int | None = None) -> list[int]:
    """Pids of every ancestor of ``pid`` (default: this process), nearest first."""
    chain: list[int] = []
    current = os.getppid() if pid is None else pid
    seen: set[int] = set()
    while current and current > 1 and current not in seen:
        chain.append(current)
        seen.add(current)
        parent = _ps(current, "ppid")
        if parent is None or not parent.strip().isdigit():
            break
        current = int(parent)
    return chain


def owner_state(owner: dict) -> str:
    """``stale`` | ``ancestor`` | ``live`` for the lock owner recorded in a lock."""
    pid = owner.get("pid")
    if not isinstance(pid, int):
        return "stale"
    if owner.get("host") not in (None, socket.gethostname()):
        return "live"  # cannot check another host's pid; never reclaim it silently
    if not pid_alive(pid):
        return "stale"
    started = owner.get("started_epoch")
    actual = process_start_epoch(pid)
    if isinstance(started, (int, float)) and actual is not None and actual > started + 2:
        return "stale"  # the pid was reused by a process younger than the lock
    if pid in ancestors():
        return "ancestor"
    return "live"


class MilestoneLock:
    def __init__(self, path: Path, *, force: bool, log=print):
        self.path, self.force, self.log = path, force, log
        self.owned = False

    def _write(self) -> bool:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        try:
            fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
        except FileExistsError:
            return False
        me = {"pid": os.getpid(), "host": socket.gethostname(),
              "started_epoch": process_start_epoch(os.getpid()) or time.time(),
              "acquired_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
              "argv": sys.argv}
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(me, fh)
        self.owned = True
        return True

    def acquire(self) -> None:
        for _ in range(3):
            if self._write():
                return
            try:
                owner = json.loads(self.path.read_text(encoding="utf-8"))
                if not isinstance(owner, dict):
                    owner = {}
            except (OSError, ValueError):
                owner = {}
            state = owner_state(owner)
            desc = f"pid {owner.get('pid')} on {owner.get('host')} since {owner.get('acquired_at')}"
            if state == "stale":
                self.log(f"milestone: reclaimed stale lock {self.path} (owner {desc} is gone)")
                self.path.unlink(missing_ok=True)
                continue
            if state == "ancestor":
                if self.force:
                    self.log(f"milestone: lock held by ancestor {desc}; --force: running "
                             f"unlocked under it")
                    return
                raise Refused(f"lock {self.path} is held by an ANCESTOR of this process "
                              f"({desc}); waiting would deadlock. Run the graphs from the "
                              f"owner, or pass --force / SKILL_GATES=off to run unlocked")
            if self.force:
                self.log(f"milestone: --force: taking over lock {self.path} from live {desc}")
                self.path.unlink(missing_ok=True)
                continue
            raise Refused(f"lock {self.path} is held by live {desc}; wait for it, or pass "
                          f"--force / SKILL_GATES=off to take it over")
        raise Refused(f"could not acquire {self.path} after reclaiming it (contended)")

    def release(self) -> None:
        if not self.owned:
            return
        try:
            owner = json.loads(self.path.read_text(encoding="utf-8"))
            if owner.get("pid") == os.getpid():
                self.path.unlink()
        except (OSError, ValueError, AttributeError):
            pass
        self.owned = False


# --------------------------------------------------------------------------- running

def read_outcome(stdout: str, graphs: list[str]) -> tuple[dict[str, dict], str | None]:
    """Per-graph rows from the runner's outcome.json; absent => errored."""
    lines = [ln.strip() for ln in stdout.splitlines() if ln.strip()]
    path = Path(lines[-1]) if lines else None
    rows: dict[str, dict] = {}
    outcome = None
    reason = None
    if path is None or path.name != "outcome.json" or not path.is_file():
        reason = "no outcome.json (runner printed no outcome path)"
    else:
        try:
            outcome = read_document(path)
        except (OSError, ValueError) as exc:
            reason = f"outcome.json unreadable: {exc}"
    by_name = {}
    if isinstance(outcome, dict) and outcome.get("schema") == "test-graph.outcome.v1":
        for g in outcome.get("graphs") or []:
            if isinstance(g, dict) and g.get("graph"):
                by_name[g["graph"]] = g
    for name in graphs:
        g = by_name.get(name)
        if g is None:
            rows[name] = {"status": "errored",
                          "cause": reason or "graph missing from outcome.json",
                          "duration_seconds": None, "report_dir": None}
            continue
        status = g.get("status") if g.get("status") in STATUSES else "errored"
        cause = g.get("cause")
        if status == "passed":
            nodes = g.get("nodes")
            if not isinstance(nodes, list) or not nodes or not all(
                    isinstance(node, dict) and node.get("status") == "passed" for node in nodes):
                status, cause = "errored", "passed graph has no nonempty passed node observations"
        rows[name] = {"status": status, "cause": cause,
                      "duration_seconds": g.get("duration_seconds"),
                      "report_dir": g.get("report_dir")}
    return rows, str(path) if outcome is not None else None


def run_set(runner: Path | None, graphs: list[str], tg_root: str | None,
            log=print, environment: dict[str, str] | None = None, stdout_path: Path | None = None) -> tuple[dict[str, dict], str | None]:
    if runner is None or not runner.is_file():
        cause = f"runner not found ({runner})" if runner else "runner not found"
        return {g: {"status": "errored", "cause": cause, "duration_seconds": None,
                    "report_dir": None} for g in graphs}, None
    cmd = [sys.executable, str(runner), *graphs]
    if len(graphs) > 1:
        cmd.append("--continue")
    if tg_root:
        cmd += ["-R", tg_root]
    log("milestone: " + " ".join(cmd))
    sys.stdout.flush()
    try:
        env = os.environ.copy()
        env.update(environment or {})
        chunks = []
        # Persist bytes as they arrive, before decoding/teeing. Opening with an
        # exclusive 0600 descriptor avoids a permissions window or overwriting
        # earlier attempts. Interrupted attempts retain their emitted streams.
        with ExitStack() as stack:
            files = {}
            if stdout_path is not None:
                for name in ("stdout", "stderr"):
                    path = stdout_path if name == "stdout" else stdout_path.with_name(
                        stdout_path.name.removesuffix(".stdout.log") + ".stderr.log")
                    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                    files[name] = stack.enter_context(os.fdopen(descriptor, "wb", buffering=0))
            with subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env) as proc:
                try:
                    with selectors.DefaultSelector() as selector:
                        for name, pipe, live in (("stdout", proc.stdout, sys.stdout),
                                                 ("stderr", proc.stderr, sys.stderr)):
                            selector.register(pipe, selectors.EVENT_READ,
                                              (name, live, codecs.getincrementaldecoder("utf-8")("replace")))
                        while selector.get_map():
                            for key, _ in selector.select():
                                name, live, decoder = key.data
                                raw = os.read(key.fileobj.fileno(), 65536)
                                if raw:
                                    if name in files:
                                        files[name].write(raw)
                                    if name == "stdout":
                                        chunks.append(raw)
                                    live.write(decoder.decode(raw))
                                    live.flush()
                                else:
                                    live.write(decoder.decode(b"", final=True))
                                    live.flush()
                                    selector.unregister(key.fileobj)
                except BaseException:
                    proc.terminate()
                    try:
                        proc.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        proc.kill()
                        proc.wait()
                    raise
        return read_outcome(b"".join(chunks).decode("utf-8", "replace"), graphs)
    except OSError as exc:
        return {g: {"status": "errored", "cause": f"runner failed to start: {exc}",
                    "duration_seconds": None, "report_dir": None} for g in graphs}, None



def exit_code(rows: dict[str, dict]) -> int:
    statuses = [r["status"] for r in rows.values()]
    if "failed" in statuses:
        return EXIT_FAILED
    if "errored" in statuses:
        return EXIT_ERRORED
    if "not_run" in statuses:
        return EXIT_FAILED
    return EXIT_PASSED


def format_table(rows: dict[str, dict], sets: dict[str, str]) -> str:
    out = ["| graph | set | status | cause | seconds |", "| --- | --- | --- | --- | --- |"]
    for name, r in rows.items():
        secs = "" if r.get("duration_seconds") is None else f"{r['duration_seconds']}"
        out.append(f"| {r.get('graph', name)} | {sets.get(name, '?')} | {r['status'].upper()} | "
                   f"{r.get('cause') or ''} | {secs} |")
    return "\n".join(out)


def milestone(argv: list[str] | None = None, *, cwd: Path | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0],
                                     formatter_class=argparse.RawDescriptionHelpFormatter,
                                     epilog=__doc__.split("\n\n", 1)[1])
    parser.add_argument("graphs", nargs="*", help="targeted rerun: only these configured graphs")
    parser.add_argument("--config", help=f"milestone config (default <repo>/{DEFAULT_CONFIG}, "
                                         f"or ${CONFIG_ENV})")
    parser.add_argument("--runner", help="test-graph run.py to invoke (overrides config)")
    parser.add_argument("--set", choices=("default", "shared"), help="select only this configured phase")
    parser.add_argument("--force", action="store_true",
                        help="override every gate (same as SKILL_GATES=off)")
    args = parser.parse_args(argv)
    force = gates_off(args.force)
    root = repo_root(cwd or Path.cwd())

    try:
        cfg_path = Path(args.config or os.environ.get(CONFIG_ENV) or root / DEFAULT_CONFIG)
        cfg_path = cfg_path if cfg_path.is_absolute() else (cwd or Path.cwd()) / cfg_path
        cfg = load_config(cfg_path)
        configured = cfg["default"] + cfg["shared"]
        unknown = [g for g in args.graphs if g not in configured]
        if unknown:
            raise Refused(f"graph(s) not in the milestone config {cfg_path}: {unknown}")
        if not configured:
            if force:
                print(f"milestone: WARNING no graphs configured in {cfg_path}; nothing run "
                      f"(--force)")
                return EXIT_PASSED
            raise Refused(f"no graphs configured in {cfg_path}: a milestone that runs "
                          f"nothing is not green")
    except Refused as exc:
        print(f"milestone: refused: {exc}", file=sys.stderr)
        return EXIT_REFUSED

    selected = args.graphs or configured
    phases = {
        phase: [g for g in cfg[phase] if g in selected and args.set in (None, phase)]
        for phase in ("default", "shared")
    }
    if not any(phases.values()):
        print("milestone: refused: selected phase contains no graphs", file=sys.stderr)
        return EXIT_REFUSED
    lock_path = Path(cfg.get("lock") or DEFAULT_LOCK)
    lock_path = lock_path if lock_path.is_absolute() else root / lock_path
    last_path = lock_path.parent / LAST_RECORD
    runner = resolve_runner(cfg, root, args.runner)
    tg_root = cfg.get("test_graph_root")
    if tg_root and not Path(tg_root).is_absolute():
        tg_root = str(root / tg_root)
    lock = MilestoneLock(lock_path, force=force)
    try:
        lock.acquire()
    except Refused as exc:
        print(f"milestone: refused: {exc}", file=sys.stderr)
        return EXIT_REFUSED
    try:
        return execute_milestone(cfg, cfg_path, root, runner, tg_root, phases,
                                 lock_path, last_path, force)
    except (EvidenceError, OSError, subprocess.SubprocessError) as exc:
        print(f"milestone: refused: {exc}", file=sys.stderr)
        return EXIT_REFUSED
    finally:
        lock.release()


def prior_execution(entry, key, identity):
    """A cache hint is admissible only through its immutable terminal authority."""
    if not isinstance(entry, dict) or entry.get("status") != "passed":
        return None
    authority = entry.get("authority")
    if not isinstance(authority, dict):
        return None
    try:
        path = Path(authority["path"])
        if file_digest(path) != authority["sha256"]:
            return None
        terminal = read_document(path)
        if terminal["identity"] != identity or terminal.get("force") or terminal.get("sourceChangedDuringRun"):
            return None
        row = terminal["executions"][key]
        if row.get("status") != "passed":
            return None
        outcome = row["outcome"]
        outcome_path = Path(outcome["path"])
        if file_digest(outcome_path) != outcome["sha256"]:
            return None
        observed, _ = read_outcome(str(outcome_path), [row["graph"]])
        if observed[row["graph"]]["status"] != "passed":
            return None
        return {**row, "authority": dict(authority)}
    except (OSError, ValueError, KeyError, TypeError):
        return None


def execute_milestone(cfg, config_path, root, runner, tg_root, phases,
                      lock_path, last_path, force):
    # Missing runners remain infrastructure errors, including when Git is absent.
    if runner is None or not runner.is_file():
        rows = {g: {"status": "errored", "cause": "runner not found",
                    "duration_seconds": None} for names in phases.values() for g in names}
        print(format_table(rows, {g: p for p, names in phases.items() for g in names}))
        return EXIT_ERRORED
    identity = binding_identity(root, config_path, runner, Path(tg_root) if tg_root else None, cfg)
    invocation = lock_path.parent / "milestone-runs" / (time.strftime("%Y%m%dT%H%M%S", time.gmtime()) + "-" + uuid.uuid4().hex)
    invocation.mkdir(parents=True, mode=0o700)
    try:
        previous = read_document(last_path)
    except (OSError, ValueError):
        previous = {}
    atomic_document(invocation / "prior-record.json", previous, exclusive=True)
    candidates = previous.get("executions", {}) if isinstance(previous, dict) and previous.get("identity") == identity else {}
    available = {}
    for key, hint in candidates.items():
        sealed = prior_execution(hint, key, identity)
        if sealed is not None:
            available[key] = sealed
    rows, sets = {}, {}
    for phase, names in phases.items():
        for graph in names:
            key = f"{phase}:{graph}"
            available.pop(key, None)
    # Invalidate selected prior greens before launching. An interrupted attempt
    # cannot leave yesterday's successful result as the current authority.
    atomic_document(last_path, {"identity": identity, "executions": available,
                                "activeInvocation": str(invocation)})
    atomic_document(invocation / "start.json", {"identity": identity, "phases": phases,
                                               "force": force}, exclusive=True)
    drifted = False
    for phase in ("default", "shared"):
        names = phases[phase]
        if not names:
            continue
        default_green = all(available.get(f"default:{g}", {}).get("status") == "passed"
                            for g in cfg["default"])
        if phase == "shared" and (not default_green or drifted) and not force:
            got = {g: {"status": "not_run", "cause": "skipped: default set not green for current source identity",
                       "duration_seconds": None, "report_dir": None} for g in names}
            outcome = None
        else:
            got, outcome = run_set(runner, names, tg_root,
                                   environment=cfg["environment"][phase],
                                   stdout_path=invocation / f"{phase}.stdout.log")
        current = binding_identity(root, config_path, runner, Path(tg_root) if tg_root else None, cfg)
        if current != identity:
            drifted = True
            available.clear()
            for row in got.values():
                if row["status"] != "not_run":
                    row["reported_status"] = row["status"]
                    row["status"] = "errored"
                    row["cause"] = "source/input/tool/configuration identity changed during the run"
        proof = {"path": outcome, "sha256": file_digest(Path(outcome))} if outcome else None
        for graph, row in got.items():
            key = f"{phase}:{graph}"
            streams = {}
            for name in ("stdout", "stderr"):
                path = invocation / f"{phase}.{name}.log"
                if path.is_file():
                    streams[name] = {"path": str(path), "sizeBytes": path.stat().st_size,
                                     "sha256": file_digest(path)}
            row.update(graph=graph, phase=phase, outcome=proof, streams=streams)
            rows[key], sets[key] = row, phase
            available[key] = row
        atomic_document(last_path, {"identity": identity, "executions": available,
                                    "activeInvocation": str(invocation)})
    code = exit_code(rows)
    result_path = invocation / "result.json"
    terminal = {"schema": "epic.milestone.result.v1", "identity": identity,
                "executions": rows, "exitCode": code, "force": force,
                "sourceChangedDuringRun": drifted}
    atomic_document(result_path, terminal, exclusive=True)
    authority = {"path": str(result_path), "sha256": file_digest(result_path)}
    for key in rows:
        available[key] = {**rows[key], "authority": authority}
    # Keep the legacy graph-name projection for older readers; phase-qualified
    # executions and their terminal authorities decide all new admissions.
    graph_rows = {row["graph"]: row for row in available.values()}
    atomic_document(last_path, {"schema": "epic.milestone.cache.v2", "identity": identity,
                                "executions": available, "graphs": graph_rows,
                                "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())})
    print(format_table(rows, sets))
    print(f"milestone: record {result_path}")
    print(f"milestone: exit {code} ({ {0: 'passed', 1: 'failed', 3: 'errored'}[code] })")
    return code


if __name__ == "__main__":
    sys.exit(milestone())
