"""skt regress: run the test graphs of one commit with a small-model agent.

The split this exists for: a big model writes a large batch of change and
never runs the graphs itself; a cheap model, driven through meta-harness,
runs them in a worktree of the pushed commit, retries what is
retryable, and reports. Running and re-running graphs is most of what
validation costs and none of it needs the big model.

Five rules shape the file:

* THE VERDICT IS NOT THE AGENT'S. It is read here from the
  ``summary.json`` each graph run wrote, and only from runs that started
  after this invocation did. A small model that says "all green" changes
  nothing.
* FIX RIGHTS NEED AN ISOLATION STATEMENT. An agent that edits and reruns
  until green will rerun many times and will poke at whatever the graph
  touches. ``--fix`` is refused without ``--isolated``: one sentence from
  the caller saying what these graphs touch and why nobody else is on it.
* A FIX IS SMALL OR IT IS AN ESCALATION. The size of what the agent
  changed is measured here from git, against a budget, and a run over it
  is ``escalated`` whatever the graphs say. The agent is told to stop and
  hand back anything bigger; the measurement is for when it does not.
* EVERY RED GETS AN ATTRIBUTION ROW. A failure the agent fixed and then
  ran green leaves no trace in the final reports, so the row is the only
  record it happened. Missing rows are listed, not guessed.
* THE WORKTREE HAS A BRANCH AND NO HOME. ``regress/<id>`` carries the
  agent's fix commits back; there is no skill-manager home to publish.
  State lives in the git common dir (``<common>/skt-regress/<id>/``),
  outside the tree under test.

Stdlib-only, like the rest of skt.
"""

from __future__ import annotations

import json
import os
import re
import shlex
import shutil
import signal
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

DEFAULT_MODEL = "CLAUDE_haiku"
DEFAULT_TIMEOUT = 4 * 60 * 60
DEFAULT_STALL_TIMEOUT = 15 * 60  # seconds without a trace event before the episode is stopped
GRAPH_WAIT = 100                 # seconds one call of graph.sh blocks: under a default command timeout
# Tools that hand control to a scheduler. Nothing wakes a session driven through meta-harness.
WAIT_TOOLS = ("ScheduleWakeup", "CronCreate", "Monitor", "PushNotification")
STATE_DIRNAME = "skt-regress"
REPORTS = Path("build") / "validation-reports"

EXIT_GREEN = 0
EXIT_RED = 1
EXIT_USAGE = 2
EXIT_INCOMPLETE = 3  # the run did not decide every requested graph
EXIT_ESCALATED = 4   # a fix bigger than the agent may make is needed

DEFAULT_MAX_FIX_LINES = 60
DEFAULT_MAX_FIX_FILES = 4
DEFAULT_MAX_RUNS = 5
# Effects a graph may declare that stay on this machine. Anything else is
# something the isolation statement has to answer for.
LOCAL_EFFECTS = ("fs:tmp", "net:local", "process:")
ATTRIBUTION_FIELDS = ("graph", "node", "origin", "area", "effect", "observed", "fix")

ORIGINS = ("product", "instrument", "environment", "unknown")


class RegressError(RuntimeError):
    def __init__(self, reason: str, fix: str | None = None, code: int = EXIT_USAGE):
        super().__init__(reason)
        self.reason, self.fix, self.code = reason, fix, code


# --------------------------------------------------------------- git / paths

def _git(args: list[str], cwd: str | Path = ".") -> str:
    proc = subprocess.run(["git", *args], cwd=str(cwd), capture_output=True, text=True)
    if proc.returncode != 0:
        raise RegressError(f"git {' '.join(args)}: {proc.stderr.strip() or proc.stdout.strip()}")
    return proc.stdout.strip()


def common_dir(start: str | Path = ".") -> Path:
    return Path(_git(["rev-parse", "--path-format=absolute", "--git-common-dir"], start))


def state_root(start: str | Path = ".") -> Path:
    return common_dir(start) / STATE_DIRNAME


def _main_worktree(start: str | Path = ".") -> Path:
    # The first `worktree list` entry is the main working tree, from any worktree.
    first = _git(["worktree", "list", "--porcelain"], start).splitlines()[0]
    return Path(first.split(" ", 1)[1])


def _valid_id(run_id: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}", run_id):
        raise RegressError(f"invalid id {run_id!r}: letters, digits, '.', '_' and '-' only")
    return run_id


def load_run(run_id: str, start: str | Path = ".") -> dict:
    path = state_root(start) / _valid_id(run_id) / "run.json"
    if not path.is_file():
        raise RegressError(
            f"no regression worktree with id {run_id!r}",
            fix="skt regress list   # or: skt regress new <ref>",
        )
    return json.loads(path.read_text())


def _save_run(run: dict) -> None:
    Path(run["state"], "run.json").write_text(json.dumps(run, indent=2) + "\n")


# ------------------------------------------------------------------- new

def new(ref: str, run_id: str | None = None, path: str | None = None,
        test_graph_root: str | None = None, start: str | Path = ".") -> dict:
    sha = _git(["rev-parse", "--verify", f"{ref}^{{commit}}"], start)
    run_id = _valid_id(run_id or sha[:10])
    state = state_root(start) / run_id
    if (state / "run.json").exists():
        raise RegressError(
            f"regression worktree {run_id!r} already exists",
            fix=f"skt regress run {run_id} <graph>...   # or: skt regress close {run_id}",
        )
    main = _main_worktree(start)
    worktree = Path(path).resolve() if path else main.parent / f"{main.name}-regress-{run_id}"
    if worktree.exists():
        raise RegressError(f"{worktree} already exists", fix="pass --path <dir> or another --id")
    branch = f"regress/{run_id}"
    _git(["worktree", "add", "-b", branch, str(worktree), sha], start)
    state.mkdir(parents=True, exist_ok=True)
    run = {
        "id": run_id,
        "ref": ref,
        "sha": sha,
        "branch": branch,
        "worktree": str(worktree),
        "state": str(state),
        "test_graph_root": str((worktree / (test_graph_root or "test_graph")).resolve()),
        "created": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "attempts": [],
    }
    _save_run(run)
    return run


def adopt(worktree_dir: str, run_id: str | None = None, test_graph_root: str | None = None,
          start: str | Path = ".") -> dict:
    """Run in a worktree that already exists and is already set up.

    A fresh worktree has only what git tracks. A repository whose graphs need
    more than that (a skill home, an index, installed tools) is tested where
    that setup already is: the ticket's or the epic's own worktree.
    """
    worktree = Path(worktree_dir).resolve()
    if not worktree.is_dir():
        raise RegressError(f"{worktree} is not a directory")
    try:
        theirs = Path(_git(["rev-parse", "--path-format=absolute", "--git-common-dir"], worktree)).resolve()
        top = Path(_git(["rev-parse", "--show-toplevel"], worktree)).resolve()
    except subprocess.CalledProcessError:
        raise RegressError(f"{worktree} is not a git worktree") from None
    if theirs != common_dir(start).resolve() or top != worktree:
        raise RegressError(f"{worktree} is not the top of a worktree of this repository",
                           fix="name the worktree's top directory (`git worktree list`)")
    sha = _git(["rev-parse", "HEAD"], worktree)
    run_id = _valid_id(run_id or sha[:10])
    state = state_root(start) / run_id
    if (state / "run.json").exists():
        raise RegressError(f"regression run {run_id!r} already exists",
                           fix=f"skt regress run {run_id} <graph>...   # or: skt regress close {run_id}")
    branch = _git(["rev-parse", "--abbrev-ref", "HEAD"], worktree)
    run = {
        "id": run_id,
        "ref": branch,
        "sha": sha,
        "branch": None if branch == "HEAD" else branch,
        "worktree": str(worktree),
        "adopted": True,
        "state": str(state),
        "test_graph_root": str((worktree / (test_graph_root or "test_graph")).resolve()),
        "created": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "attempts": [],
    }
    left = tree_changes(run)
    if left["uncommitted"]:
        what = ", ".join(left["untracked"][:5]) or "modified tracked files"
        raise RegressError(
            f"{worktree} holds uncommitted work ({what}); the agent's changes could not be told from it",
            fix="commit or stash it, then adopt again",
        )
    state.mkdir(parents=True, exist_ok=True)
    _save_run(run)
    return run


# --------------------------------------------------------------- resolution

def find_runner(run: dict, explicit: str | None = None, start: str | Path = ".") -> Path:
    """The test-graph skill's ``run.py``.

    Preferred order: the flag, the environment, the copy inside the tree
    under test (a repository that ships the skill is tested with its own
    runner), then the homes this session can see.
    """
    candidates: list[Path] = []
    for value in (explicit, os.environ.get("SKT_REGRESS_RUNNER")):
        if value:
            candidates.append(Path(value).expanduser())
    candidates.append(Path(run["worktree"]) / "skills" / "test-graph" / "scripts" / "run.py")
    homes: list[Path] = []
    if os.environ.get("SKILL_MANAGER_HOME"):
        homes.append(Path(os.environ["SKILL_MANAGER_HOME"]))
    homes += [_main_worktree(start) / ".skill-manager", Path.home() / ".skill-manager"]
    for home in homes:
        candidates.append(home / "plugins" / "tla-spec-dev" / "skills" / "test-graph" / "scripts" / "run.py")
        candidates.append(home / "skills" / "test-graph" / "scripts" / "run.py")
    for candidate in candidates:
        if candidate.is_file():
            return candidate.resolve()
    raise RegressError(
        "cannot find the test-graph runner (skills/test-graph/scripts/run.py)",
        fix="pass --runner <path/to/run.py> or set SKT_REGRESS_RUNNER",
    )


def find_meta_harness(explicit: str | None = None) -> str:
    for value in (explicit, os.environ.get("META_HARNESS_BIN")):
        if value:
            path = Path(value).expanduser()
            if not path.is_file():
                raise RegressError(f"meta-harness binary not found at {path}")
            return str(path.resolve())
    found = shutil.which("meta-harness")
    if found:
        return found
    raise RegressError(
        "meta-harness is not on PATH",
        fix="pass --meta-harness <binary> or set META_HARNESS_BIN "
            "(cargo build -p meta-harness in the meta-harness checkout)",
    )


def discover_graphs(runner: Path, tg_root: str) -> dict[str, list[str]]:
    """Registered graphs and the node sources of each, from ``discover.py``."""
    discover = runner.with_name("discover.py")
    if not discover.is_file():
        return {}
    proc = subprocess.run(
        [sys.executable, str(discover), "--test-graph-root", tg_root],
        capture_output=True, text=True, cwd=tg_root,
    )
    if proc.returncode != 0:
        # Older copies take no root flag and read the current directory's project.
        proc = subprocess.run([sys.executable, str(discover)], capture_output=True, text=True,
                              cwd=str(Path(tg_root).parent))
    graphs: dict[str, list[str]] = {}
    current = None
    for line in proc.stdout.splitlines():
        head = re.match(r"graph:\s*(\S+)", line)
        if head:
            current = graphs.setdefault(head.group(1), [])
        elif current is not None and line.strip().startswith("- "):
            current.append(line.strip()[2:])
    return graphs


def declared_effects(sources: list[str]) -> list[str]:
    """Side effects the nodes of these graphs declare, read from their sources.

    A reading aid for whoever writes the isolation statement, not a proof:
    a node can do more than it declares.
    """
    found: set[str] = set()
    for source in sources:
        try:
            text = Path(source).read_text(errors="replace")
        except OSError:
            continue
        for start in (m.end() for m in re.finditer(r"side_effects\(", text)):
            depth, end = 1, start
            while end < len(text) and depth:
                depth += {"(": 1, ")": -1}.get(text[end], 0)
                end += 1
            call = text[start:end - 1]
            found.update(f"environment:{m}" for m in
                         re.findall(r"SideEffect\.environment\(\s*[\"'](\w+)[\"']", call))
            bare = re.sub(r"SideEffect\.\w+\([^)]*\)", "", call)
            found.update(re.findall(r"[\"']([A-Za-z][\w:.-]*)[\"']", bare))
        if re.search(r"environment_?[rR]epository", text):
            found.add("environment:repository")
    return sorted(found)


def beyond_local(effects: list[str]) -> list[str]:
    return [e for e in effects if not e.startswith(LOCAL_EFFECTS)]


# ------------------------------------------------------------------- brief

GRAPH_SCRIPT = r"""#!/usr/bin/env bash
# usage: graph.sh <graph>   |   graph.sh --resume <runId>
# Starts the run detached, waits at most @WAIT@ seconds, and says whether it
# finished. Called again with the same arguments it rejoins the same run.
set -u
[ $# -ge 1 ] || { echo "usage: graph.sh <graph> | graph.sh --resume <runId>" >&2; exit 2; }
dir=@DIR@
mkdir -p "$dir"
key=$(printf '%s' "$*" | tr -c 'A-Za-z0-9._-' '_')
pidf="$dir/$key.pid"; rcf="$dir/$key.rc"; log="$dir/$key.log"
if [ ! -f "$pidf" ]; then
  rm -f "$rcf"
  RUNNER=@RUNNER@ TG=@TG@ LOG="$log" RCF="$rcf" nohup bash -c \
    'python3 "$RUNNER" "$@" --test-graph-root "$TG" > "$LOG" 2>&1; echo $? > "$RCF.tmp"; mv "$RCF.tmp" "$RCF"' \
    graph "$@" < /dev/null > /dev/null 2>&1 &
  echo $! > "$pidf"
  echo "STARTED $*"
fi
end=$((SECONDS + @WAIT@))
while [ ! -f "$rcf" ] && [ $SECONDS -lt $end ]; do sleep 2; done
if [ -f "$rcf" ]; then
  rm -f "$pidf"
  echo "FINISHED $*  (runner exit $(cat "$rcf"))  full log: $log"
  tail -n 30 "$log"
else
  echo "STILL RUNNING $*  -- run this exact command again to keep waiting. Do nothing else meanwhile."
fi
"""


def write_graph_script(attempt_dir: Path, runner: Path, tg_root: str) -> Path:
    """The one command the agent runs a graph with.

    It blocks for a bounded time and rejoins the same run when called again,
    so the agent needs no long command timeout, no background job of its own
    and no timer -- none of which work for a session driven through
    meta-harness.
    """
    path = attempt_dir / "graph.sh"
    path.write_text(GRAPH_SCRIPT.replace("@WAIT@", str(GRAPH_WAIT))
                    .replace("@DIR@", shlex.quote(str(attempt_dir / "graph-runs")))
                    .replace("@RUNNER@", shlex.quote(str(runner)))
                    .replace("@TG@", shlex.quote(tg_root)))
    path.chmod(0o755)
    return path


def build_brief(run: dict, graphs: list[str], runner: Path, report_path: Path, *,
                fix: bool = False, isolated: str | None = None, effects: list[str] | None = None,
                max_fix_lines: int = DEFAULT_MAX_FIX_LINES, max_fix_files: int = DEFAULT_MAX_FIX_FILES,
                max_runs: int = DEFAULT_MAX_RUNS) -> str:
    tg = run["test_graph_root"]
    # ``runner`` is the attempt's graph.sh (write_graph_script), not run.py itself.
    run_cmd = f"bash {runner} <graph>"
    resume_cmd = f"bash {runner} --resume <runId>"
    skeleton = json.dumps({
        "sha": run["sha"],
        "graphs": [{
            "graph": "<name>",
            "status": "passed | failed | errored | not_run",
            "attempts": [{"runId": "<runId>", "command": "<command>", "status": "passed | failed | errored"}],
        }],
        "attribution": [{
            "graph": "<graph>",
            "node": "<failing node id>",
            "origin": " | ".join(ORIGINS),
            "area": "<in your own words, the part of the code or of the test apparatus where the defect lives>",
            "effect": "faithful | false red",
            "observed": "<text quoted from the report or log>",
            "fix": "<commit sha of your fix> | escalated | none",
            "pinned_by": "<node or assertion that now catches it, or null>",
            "introduced_by": "<ticket id from the subject of the commit that caused it, or null>",
        }],
        "escalation": None,
        "notes": "<anything the next reader must know, or empty>",
    }, indent=2)
    escalation = json.dumps({
        "graph": "<graph>", "node": "<node id>",
        "reason": "<why this is not a small fix>",
        "needed": "<what has to change, as specifically as you can say>",
        "files": ["<files you believe are involved>"],
        "evidence": "<text quoted from the report or log>",
    })
    if fix:
        mode = f"""YOU MAY MAKE SMALL FIXES, AND ONLY SMALL ONES
This run is isolated: {isolated}
Stay inside that. Do not point any command at a cluster, host, account or directory
other than the ones this worktree and its graphs already use.

A small fix is one that is obviously right from the report and the log:
a wrong path, a missing import, a typo, a stale fixture, a timeout that is too short,
a node script that crashes for a reason unrelated to what it asserts.
- Change the fewest lines that make the failing node pass. Touch only the file the report
  or the log points at. Do not tidy, rename, reformat, upgrade or "improve" anything else,
  and do not fix something that is not failing.
- A fix belongs in the test graph project ({tg}) unless the log quotes a crash at a named
  line of another file. Changing how the code under test behaves is never a small fix.
- Commit each fix on its own: `git commit -am "regress: <what you fixed>"`.
  You are on branch {run.get('branch', '(detached)')}. Do not push. Do not switch branches.
- All of your fixes together must stay within {max_fix_lines} changed lines in {max_fix_files} files.
- NEVER make a red go away by weakening the check: do not delete, skip, loosen or comment out
  an assertion or a node, and do not change an expected value to whatever the code now prints.
- After a fix, resume from the failed node:  {resume_cmd}
  When that passes, run the whole graph once more from the beginning. Only a full run
  that finished after your last commit counts.
- Run one graph at most {max_runs} times in total (full runs and resumes together).

STOP AND ESCALATE, do not attempt the fix, when any of these is true:
- the fix would not fit the limits above, or needs a new file, a new dependency, or a
  change to an interface, a schema, a spec or a model;
- you would have to decide what the correct behaviour is;
- you fixed it once and the same node still fails;
- you cannot tell why it failed;
- the graph cannot run because something is not set up, or the failure is in the
  isolated environment itself. You never repair the environment.
To escalate: make no further changes, run no further graphs, mark the remaining graphs
`not_run`, and set `escalation` in the report to:
  {escalation}
"""
    else:
        mode = f"""YOU DO NOT FIX ANYTHING
- Do not edit, create or delete any tracked file. Do not commit, push, or change branches.
- Only when the origin of a failure is `environment`, retry ONCE by resuming from the failed node:
    {resume_cmd}
  Never run a graph more than twice in total. Never retry a `product` or `instrument` failure.
- If a failure needs a change or some setup to pass, say what is needed in `escalation`:
    {escalation}
"""
    fix_cmds = ";\n- in the worktree: your edits, `git add` and `git commit`" if fix else ""
    effects_line = ", ".join(effects) if effects else "none found in the node sources"
    return f"""You are a test-graph regression runner. Your job is to run the test graphs listed
below on one commit and report exactly what happened.

Commit under test: {run['sha']}
Worktree (your working directory): {run['worktree']}
Test graph project: {tg}
Side effects these graphs declare: {effects_line}

THE ONLY COMMANDS YOU RUN
- the graph command given below, to run a graph and to wait for it;
- commands that only read: cat, ls, grep, head, tail, `git log`, `git diff`, `git status`{fix_cmds}.
Nothing else. In particular:
- NO setup of any kind. Do not install, build, bootstrap, refresh, index, migrate, log in,
  or start, stop or restart any service, daemon, container, cluster or server. Do not run
  docker, kubectl, helm, k3d, pip, uv, npm, brew, make, or any script from this repository
  other than the graph command. If a graph cannot run because something is not set up
  (a missing home, tool, index, credential or service), that is an `environment` failure:
  do not repair it. Record it and escalate, saying exactly what is missing.
- NO background work and NO timers. Do not end a command with `&`, do not use nohup, and
  do not use a background-run option, a scheduled wakeup, a reminder, a monitor or a
  "check back later" tool. Nothing will ever wake you: you would stop for good. The only
  way to wait is to run the graph command again.

GRAPHS TO RUN, in this order:
{chr(10).join(f'  - {g}' for g in graphs)}

FOR EACH GRAPH
1. Run it, with exactly this command:
     {run_cmd}
   It prints FINISHED or STILL RUNNING within about two minutes. On STILL RUNNING, run the
   same command again, and keep doing that until it prints FINISHED. A run can take tens
   of minutes. Slow is not failed. Run one graph at a time.
2. Find the report directory the run wrote: the newest directory under
     {tg}/{REPORTS}/
   Its name is the runId. Read `summary.json` (field `status`). On anything other than
   `passed`, read `report.md` and the failing node's files under `envelope/` and `node-logs/`.
3. If the status is `passed`, record it and go on.
4. If not, decide the ORIGIN, which means where the fix belongs:
     product      the code under test is wrong: an assertion about it was false
     instrument   the test apparatus is wrong: the node, its fixture or the harness
     environment  the machine got in the way: timeout, port in use, network, missing tool, disk
     unknown      you cannot tell; say what you looked at
5. Add one ATTRIBUTION row for this failure, now, before you do anything about it.
   Every failure gets a row, including one you go on to fix and one that passes on a retry.
   - `area`: for an instrument failure, name the apparatus ("the fixture's port handling"),
     not the product feature the node was testing.
   - `effect`: `faithful` when the red was about a real defect in the code under test;
     `false red` when the code under test was fine and the instrument or the environment failed.
   - `observed`: quote the report or the log. Do not guess.
   - `introduced_by`: the commit under test may hold several tickets, each commit subject
     starting with its ticket id. If `git log --oneline -- <the files involved>` shows which
     ticket's commit caused this, give that ticket id. If it does not, write null.

{mode}
WHEN YOU ARE DONE, OR HAVE ESCALATED, write this JSON file, and nothing else, to:
  {report_path}

{skeleton}

`escalation` is null unless you escalated; when you did, it is the object described above.
`attribution` is an empty list only when no run failed at all. For a graph you did not
get to, use `not_run`. Then reply with one line: the path of the file you wrote.
"""


# ------------------------------------------------------------------ verdict

def tree_changes(run: dict, since: str | None = None) -> dict:
    """What changed in the worktree since ``since`` (default: the commit under test).

    Measured from git and not from the agent's report. Untracked files count:
    a new file nobody ``git add``ed is still a change, and ``close`` would
    otherwise delete it without a word.
    """
    wt = run["worktree"]
    base = since or run["sha"]
    files, lines = [], 0
    for row in _git(["diff", "--numstat", base], wt).splitlines():
        added, deleted, path = row.split("\t", 2)
        files.append(path)
        lines += (int(added) if added.isdigit() else 0) + (int(deleted) if deleted.isdigit() else 0)
    tg_rel = os.path.relpath(run["test_graph_root"], wt)
    # The graph runs write their reports under <test graph>/build. That output is
    # the runner's, whether or not the repository ignores it.
    untracked = [u for u in _git(["ls-files", "--others", "--exclude-standard"], wt).splitlines()
                 if u and not u.startswith(f"{tg_rel}/build/")]
    for path in untracked:
        files.append(path)
        try:
            lines += len((Path(wt) / path).read_bytes().splitlines())
        except OSError:
            pass
    status = _git(["status", "--porcelain", "--untracked-files=no"], wt)
    head = _git(["rev-parse", "HEAD"], wt)
    return {
        "files": files,
        "lines": lines,
        "commits": _git(["rev-list", f"{base}..HEAD"], wt).split(),
        "untracked": untracked,
        "uncommitted": bool(status.strip()) or bool(untracked),
        "outside_test_graph": [f for f in files if not f.startswith(tg_rel + "/")],
        "last_commit_time": int(_git(["log", "-1", "--format=%ct", "HEAD"], wt)) if head != base else None,
    }


def read_verdict(tg_root: str, graphs: list[str], since: float,
                 changed_at: float | None = None) -> tuple[list[dict], list[dict]]:
    """Per requested graph, what the graph runs themselves recorded since ``since``.

    A report older than the invocation is ignored: ``validation-reports``
    keeps earlier green runs, so a graph that never executed looks green
    there. A pass by resume counts while the tree is unchanged; a single
    node run on its own never does. Once the tree has changed
    (``changed_at``), a pass counts only if it is a full run that finished
    after the last change.

    Also returns every non-passed run seen, for the attribution check.
    """
    runs: dict[str, list[dict]] = {}
    root = Path(tg_root) / REPORTS
    if root.is_dir():
        for summary in root.glob("*/summary.json"):
            mtime = summary.stat().st_mtime
            if mtime < since:
                continue
            try:
                data = json.loads(summary.read_text())
            except (OSError, ValueError):
                continue
            execution = data.get("execution") or {}
            name = execution.get("graphName")
            if not name:
                continue
            runs.setdefault(name, []).append({
                "graph": name,
                "runId": data.get("runId") or summary.parent.name,
                "status": data.get("status"),
                "mode": execution.get("mode"),
                "report": str(summary.parent / "report.md"),
                "mtime": mtime,
            })
    rows, reds = [], []
    for graph in graphs:
        attempts = sorted(runs.get(graph, []), key=lambda r: r["mtime"])
        reds += [a for a in attempts if a["status"] != "passed"]
        if not attempts:
            rows.append({"graph": graph, "status": "not_run", "runs": 0})
            continue
        last = attempts[-1]
        status = last["status"] or "unknown"
        mode = last["mode"] or "full"
        via_resume = mode != "full"
        if status == "passed" and (
            # One node on its own proves nothing about the nodes after it.
            (via_resume and not mode.startswith("resume"))
            # Once the tree has changed, only a full run that finished in a later
            # second than the last change counts (commit times are whole seconds).
            or (changed_at is not None and (via_resume or int(last["mtime"]) <= int(changed_at)))
        ):
            status = "needs_full_run"
        rows.append({
            "graph": graph,
            "status": status,
            "runs": len(attempts),
            "runId": last["runId"],
            "mode": last["mode"],
            "via_resume": via_resume,
            "report": last["report"],
        })
    return rows, reds


def read_agent_report(path: Path) -> tuple[dict | None, str | None]:
    if not path.is_file():
        return None, "the agent wrote no report"
    try:
        data = json.loads(path.read_text())
    except ValueError as err:
        return None, f"the agent's report is not JSON ({err})"
    if not isinstance(data, dict) or not isinstance(data.get("graphs"), list):
        return None, "the agent's report has no `graphs` list"
    return data, None


def attribution_gaps(agent_report: dict | None, reds: list[dict]) -> list[str]:
    """Failures the reports show that the agent's attribution does not account for."""
    rows = [r for r in (agent_report or {}).get("attribution") or [] if isinstance(r, dict)]
    gaps = []
    for index, row in enumerate(rows, 1):
        missing = [f for f in ATTRIBUTION_FIELDS if not str(row.get(f) or "").strip()]
        if row.get("origin") not in ORIGINS:
            missing.append("origin (not one of " + "/".join(ORIGINS) + ")")
        if missing:
            gaps.append(f"attribution row {index} lacks: {', '.join(dict.fromkeys(missing))}")
    covered = {r.get("graph") for r in rows}
    for graph in dict.fromkeys(r["graph"] for r in reds):
        if graph not in covered:
            first = next(r for r in reds if r["graph"] == graph)
            gaps.append(f"{graph} went red (run {first['runId']}) with no attribution row: {first['report']}")
    return gaps


def write_attribution_yaml(path: Path, run: dict, attempt_no: int, rows: list[dict]) -> None:
    """The agent's rows as ledger-shaped YAML (bug_attribution.md §4), for the epic agent to absorb."""
    out = [f"# Candidate CATCH rows from skt regress {run['id']} attempt {attempt_no}, commit {run['sha']}.",
           "# Written by a small model: read each against its report before absorbing it."]
    for index, row in enumerate(rows, 1):
        out.append(f"- id: REGRESS-{run['id']}-{attempt_no}-{index}")
        out.append("  channel: test-graph")
        for key in ("graph", "node", "origin", "area", "effect", "observed", "fix", "pinned_by",
                    "introduced_by"):
            out.append(f"  {key}: {json.dumps(row.get(key))}")  # a JSON scalar is a YAML scalar
    path.write_text("\n".join(out) + "\n")


# ------------------------------------------------------------- meta-harness

def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


AUTH_ENV = ("CLAUDE_CODE_OAUTH_TOKEN", "CLAUDE_CODE_USE_BEDROCK", "CLAUDE_CODE_USE_VERTEX")


def _agent_env() -> dict:
    # A session spawned from inside another agent session must not inherit its
    # identity. Its credentials are another matter: without them the agent has
    # nothing to log in with.
    return {k: v for k, v in os.environ.items()
            if k in AUTH_ENV or not (k == "CLAUDECODE" or k.startswith("CLAUDE_CODE_"))}


# ------------------------------------------------------------- one at a time

def _alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except OSError:
        return True
    return True


def live_runs(start: str | Path = ".") -> list[dict]:
    """Regression runs of this repository that are executing right now."""
    found = []
    root = state_root(start)
    for marker in sorted(root.glob("*/running.json")) if root.is_dir() else []:
        try:
            data = json.loads(marker.read_text())
        except (OSError, ValueError):
            continue
        if isinstance(data.get("pid"), int) and _alive(data["pid"]):
            found.append(data)
        else:
            marker.unlink(missing_ok=True)  # left by a run that was killed
    return found


def refuse_shared_concurrency(run_id: str, isolated: str | None, start: str | Path = ".") -> None:
    """Two runs may overlap only when both say what they touch is private."""
    for other in live_runs(start):
        if other["id"] == run_id:
            raise RegressError(f"regress {run_id} is already running (pid {other['pid']})",
                               fix="wait for it; `skt regress list` shows what is running")
        if not (isolated or "").strip() or not (other.get("isolated") or "").strip():
            which = "this run has" if not (isolated or "").strip() else f"regress {other['id']} has"
            raise RegressError(
                f"regress {other['id']} is running (pid {other['pid']}, graphs: "
                f"{', '.join(other.get('graphs') or [])}) and {which} no isolation statement: two "
                "runs sharing ports, clusters or output directories fail each other's graphs",
                fix='wait for it to finish, or give every overlapping run --isolated "<statement>"',
            )


def _wait_listening(base_url: str, proc: subprocess.Popen, seconds: float = 60) -> None:
    deadline = time.time() + seconds
    while time.time() < deadline:
        if proc.poll() is not None:
            raise RegressError(f"meta-harness serve exited with {proc.returncode} before listening",
                               code=EXIT_INCOMPLETE)
        try:
            urllib.request.urlopen(f"{base_url}/v1/models", timeout=2).close()
            return
        except urllib.error.HTTPError:
            return  # it answered; that is all this asks
        except OSError:
            time.sleep(0.5)
    raise RegressError("meta-harness serve did not start listening within 60s", code=EXIT_INCOMPLETE)


def read_trace(evidence: Path) -> dict | None:
    """What the agent did, from meta-harness's own event log. None when there is none."""
    logs = sorted(evidence.glob("*/events.jsonl")) if evidence.is_dir() else []
    if not logs:
        return None
    trace = {"events": 0, "tool_calls": 0, "agent_messages": 0, "tools": {}, "wait_tools": [],
             "last_tool": None, "last_event": None, "tokens": None, "cost_usd": None}
    for log in logs:
        try:
            lines = log.read_text(errors="replace").splitlines()
        except OSError:
            continue
        for line in lines:
            try:
                event = json.loads(line)
            except ValueError:
                continue
            kind, data = event.get("kind"), event.get("data") or {}
            trace["events"] += 1
            trace["last_event"] = event.get("ts") or trace["last_event"]
            if kind == "tool.call":
                name = data.get("name") or data.get("title") or "?"
                trace["tool_calls"] += 1
                trace["tools"][name] = trace["tools"].get(name, 0) + 1
                trace["last_tool"] = name
                if name in WAIT_TOOLS and name not in trace["wait_tools"]:
                    trace["wait_tools"].append(name)
            elif kind in ("agent.message.chunk", "agent.message.complete", "agent.thought.chunk"):
                # A turn that failed at once still closes with one empty message.
                content = data.get("content")
                parts = content if isinstance(content, list) else [content]
                if any(isinstance(c, dict) and (c.get("text") or "").strip() for c in parts):
                    trace["agent_messages"] += 1
            elif kind == "turn.ended":
                usage = data.get("usage") or {}
                if usage.get("session_total_tokens") is not None:
                    trace["tokens"] = {k[len("session_"):]: v for k, v in usage.items()
                                       if k.startswith("session_")}
            elif kind == "usage.update":
                cost = ((data.get("usage") or {}).get("raw") or {}).get("cost") or {}
                if cost.get("amount") is not None:
                    trace["cost_usd"] = cost["amount"]
    return trace


def _trace_mtime(evidence: Path) -> float | None:
    times = [f.stat().st_mtime for f in evidence.glob("*/events.jsonl")] if evidence.is_dir() else []
    return max(times) if times else None


def _stop_group(proc: subprocess.Popen) -> None:
    """Stop a process and everything it started that stayed in its group."""
    for sig, grace in ((signal.SIGTERM, 20), (signal.SIGKILL, 5)):
        try:
            os.killpg(proc.pid, sig)
        except (ProcessLookupError, PermissionError):
            pass
        try:
            proc.wait(timeout=grace)
            return
        except subprocess.TimeoutExpired:
            continue


def run_episode(binary: str, attempt_dir: Path, request: dict, base_url: str | None,
                stall_timeout: int = DEFAULT_STALL_TIMEOUT) -> tuple[dict, str]:
    """Drive one episode. Starts a private ``serve`` unless ``base_url`` names one.

    The private server runs in its own process group, and the group is stopped
    when the episode ends, so nothing the agent started outlives the run unless
    it detached itself. With a private server the trace is watched: an episode
    that records nothing for ``stall_timeout`` seconds is stopped.
    """
    request_path = attempt_dir / "request.json"
    result_path = attempt_dir / "episode.json"
    request_path.write_text(json.dumps(request, indent=2) + "\n")
    evidence = attempt_dir / ".meta-harness" / "evidence"
    serve = client = log = None
    stopped = None
    try:
        if base_url is None:
            port = _free_port()
            base_url = f"http://127.0.0.1:{port}"
            log = open(attempt_dir / "serve.log", "w")
            serve = subprocess.Popen(
                [binary, "--project-root", str(attempt_dir), "serve", "--port", str(port)],
                stdout=log, stderr=subprocess.STDOUT, env=_agent_env(), cwd=str(attempt_dir),
                start_new_session=True,
            )
            _wait_listening(base_url, serve)
        client = subprocess.Popen(
            [binary, "--project-root", str(attempt_dir), "episode", "--base-url", base_url,
             "--request", str(request_path), "--output", str(result_path)],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        began = time.time()
        deadline = began + request["timeoutSeconds"] + 300
        while client.poll() is None:
            now = time.time()
            if now > deadline:
                stopped = "the episode ran past its timeout"
                break
            if serve is not None and stall_timeout:
                quiet = now - (_trace_mtime(evidence) or began)
                if quiet > stall_timeout:
                    stopped = (f"the agent recorded nothing for {int(quiet)}s and was stopped "
                               f"(--stall-timeout {stall_timeout})")
                    break
            time.sleep(2)
    finally:
        if client is not None and client.poll() is None:
            client.kill()
            client.wait()
        if serve is not None:
            _stop_group(serve)
        if log is not None:
            log.close()
    if stopped:
        return {"outcome": "stopped", "error": stopped}, base_url
    try:
        return json.loads(result_path.read_text()), base_url
    except (OSError, ValueError):
        return {"outcome": "failed", "error": "meta-harness episode wrote no result"}, base_url


# ---------------------------------------------------------------------- run

def run(run_id: str, graphs: list[str], *, all_graphs: bool = False, model: str | None = None,
        timeout: int = DEFAULT_TIMEOUT, meta_harness: str | None = None, runner: str | None = None,
        base_url: str | None = None, dry_run: bool = False, as_json: bool = False,
        fix: bool = False, isolated: str | None = None, env: list[str] | None = None,
        max_fix_lines: int = DEFAULT_MAX_FIX_LINES, max_fix_files: int = DEFAULT_MAX_FIX_FILES,
        max_runs: int = DEFAULT_MAX_RUNS, stall_timeout: int = DEFAULT_STALL_TIMEOUT,
        start: str | Path = ".") -> int:
    record = load_run(run_id, start)
    if not Path(record["worktree"]).is_dir():
        raise RegressError(f"worktree {record['worktree']} is gone", fix=f"skt regress close {run_id}")
    if all_graphs == bool(graphs):
        raise RegressError("name the graphs to run, or pass --all (not both)")
    if fix and not (isolated or "").strip():
        raise RegressError(
            "--fix needs --isolated: an agent that edits and reruns until green must not share "
            "what the graphs touch",
            fix='add --isolated "<what these graphs touch, and why nobody else is on it>", '
                "or drop --fix for a report-only run",
        )
    agent_env = {}
    for pair in env or []:
        if "=" not in pair:
            raise RegressError(f"--env takes KEY=VALUE, got {pair!r}")
        key, value = pair.split("=", 1)
        agent_env[key] = value
    # Branch-scoped environments (test-graph environment repositories) key on this,
    # so the run provisions its own instead of reusing the feature branch's.
    agent_env.setdefault("TEST_GRAPH_FEATURE_BRANCH", f"regress-{record['id']}")

    if not Path(record["test_graph_root"]).is_dir():
        raise RegressError(
            f"no test graph project at {record['test_graph_root']}",
            fix=f"skt regress close {run_id}, then `skt regress new <ref> --test-graph-root <dir>`",
        )
    runner_path = find_runner(record, runner, start)
    registered = discover_graphs(runner_path, record["test_graph_root"])
    if all_graphs:
        if not registered:
            raise RegressError("graph discovery found no graphs", fix="name the graphs instead of --all")
        graphs = list(registered)
    effects = declared_effects([str(Path(record["test_graph_root"]).parent / s)
                                for g in graphs for s in registered.get(g, [])])
    shared = beyond_local(effects)
    model = model or os.environ.get("SKT_REGRESS_MODEL") or DEFAULT_MODEL

    # A directory left by an interrupted or dry run is reused, never read: nothing
    # in it may be taken for this attempt's output.
    attempt_no = len(record["attempts"]) + 1
    attempt_dir = Path(record["state"]) / f"attempt-{attempt_no}"
    attempt_dir.mkdir(parents=True, exist_ok=True)
    report_path = attempt_dir / "agent-report.json"
    for stale in ("agent-report.json", "episode.json", "result.json", "attribution.yaml", "fixes.patch"):
        (attempt_dir / stale).unlink(missing_ok=True)
    graph_script = write_graph_script(attempt_dir, runner_path, record["test_graph_root"])
    shutil.rmtree(attempt_dir / "graph-runs", ignore_errors=True)
    brief = build_brief(record, graphs, graph_script, report_path, fix=fix, isolated=isolated,
                        effects=effects, max_fix_lines=max_fix_lines, max_fix_files=max_fix_files,
                        max_runs=max_runs)
    (attempt_dir / "brief.md").write_text(brief)
    request = {
        "attemptId": f"skt-regress-{record['id']}-{attempt_no}",
        "model": model,
        "messages": [{"role": "user", "content": brief}],
        "workingDirectory": record["worktree"],
        "timeoutSeconds": timeout,
        "env": agent_env,
    }
    if fix and shared:
        print(f"note: these graphs declare effects beyond this machine: {', '.join(shared)}.\n"
              f"      The isolation statement has to cover them: {isolated}", file=sys.stderr)
    if dry_run:
        (attempt_dir / "request.json").write_text(json.dumps(request, indent=2) + "\n")
        print(f"dry run: nothing started\nbrief      {attempt_dir / 'brief.md'}\n"
              f"request    {attempt_dir / 'request.json'}\ngraphs     {', '.join(graphs)}\n"
              f"mode       {'fix (isolated: ' + isolated + ')' if fix else 'report-only'}\n"
              f"effects    {', '.join(effects) or 'none declared'}")
        return EXIT_GREEN

    binary = find_meta_harness(meta_harness)
    refuse_shared_concurrency(record["id"], isolated, start)
    head_at_start = _git(["rev-parse", "HEAD"], record["worktree"])
    started = time.time()
    marker = Path(record["state"]) / "running.json"
    marker.write_text(json.dumps({"id": record["id"], "pid": os.getpid(), "graphs": graphs,
                                  "isolated": isolated, "started": started}) + "\n")
    try:
        episode, used_url = run_episode(binary, attempt_dir, request, base_url, stall_timeout)
    finally:
        marker.unlink(missing_ok=True)

    changes = tree_changes(record)                      # the whole branch: what would be merged
    this_attempt = tree_changes(record, head_at_start)  # what this run did
    changed = bool(changes["files"])
    rows, reds = read_verdict(record["test_graph_root"], graphs, started,
                              changed_at=(changes["last_commit_time"] or time.time()) if changed else None)
    agent_report, report_problem = read_agent_report(report_path)
    escalation = (agent_report or {}).get("escalation")
    if not isinstance(escalation, dict) or not escalation:
        escalation = None  # "none", "", [] and the like are a slip, not an escalation
    over = []
    if this_attempt["files"] and not fix:
        over.append("the agent changed the tree in a report-only run: "
                    + ", ".join(this_attempt["files"][:5]))
    # The budget is for the branch as a whole: fixes spread over several
    # attempts are not smaller for having been made in instalments.
    if changes["lines"] > max_fix_lines:
        over.append(f"{changes['lines']} changed lines (limit {max_fix_lines})")
    if len(changes["files"]) > max_fix_files:
        over.append(f"{len(changes['files'])} changed files (limit {max_fix_files})")
    for row in rows:
        if row["runs"] > max_runs:
            over.append(f"{row['graph']} was run {row['runs']} times (limit {max_runs})")
    statuses = {r["status"] for r in rows}
    if escalation or over:
        verdict, code = "escalated", EXIT_ESCALATED
    elif statuses & {"failed", "errored"}:
        verdict, code = "red", EXIT_RED
    elif statuses == {"passed"} and not changes["uncommitted"]:
        verdict, code = "green", EXIT_GREEN
    else:
        verdict, code = "incomplete", EXIT_INCOMPLETE
    # Whether the agent ever got to work is read from meta-harness's trace, not
    # guessed from what is missing afterwards: an agent that ran tools and then
    # hung leaves the same empty hands as one that could not log in.
    trace = read_trace(attempt_dir / ".meta-harness" / "evidence") if base_url is None else None
    silent = (episode.get("outcome") != "succeeded" and agent_report is None
              and all(r["runs"] == 0 for r in rows) and not this_attempt["files"])
    if trace is None:
        agent_started = None if silent else True   # no trace to read (--base-url, or none written)
    else:
        agent_started = bool(trace["tool_calls"] or trace["agent_messages"]) or not silent
    gaps = attribution_gaps(agent_report, reds)
    attribution = [r for r in (agent_report or {}).get("attribution") or [] if isinstance(r, dict)]
    if attribution:
        write_attribution_yaml(attempt_dir / "attribution.yaml", record, attempt_no, attribution)
    if changed:
        patch = _git(["diff", record["sha"]], record["worktree"]) + "\n"
        if changes["untracked"]:
            patch += "\n# Untracked files, not in the diff above:\n" + "".join(
                f"#   {u}\n" for u in changes["untracked"])
        (attempt_dir / "fixes.patch").write_text(patch)

    result = {
        "id": record["id"],
        "sha": record["sha"],
        "branch": record.get("branch"),
        "attempt": attempt_no,
        "model": model,
        "mode": "fix" if fix else "report-only",
        "isolated": isolated,
        "declared_effects": effects,
        "verdict": verdict,
        "agent_started": agent_started,
        "trace": trace,
        "graphs": rows,
        "escalation": escalation,
        "over_budget": over,
        "fixes": {**changes, "patch": str(attempt_dir / "fixes.patch") if changed else None},
        "attribution": str(attempt_dir / "attribution.yaml") if attribution else None,
        "attribution_rows": len(attribution),
        "attribution_gaps": gaps,
        "episode": {k: episode.get(k) for k in
                    ("outcome", "error", "executionId", "conversationId", "durationMillis", "usage")},
        "agent_report": str(report_path) if agent_report else None,
        "agent_report_problem": report_problem,
        "evidence": str(attempt_dir / ".meta-harness" / "evidence") if base_url is None else used_url,
        "duration_seconds": round(time.time() - started),
    }
    (attempt_dir / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    record["attempts"].append({"attempt": attempt_no, "verdict": verdict, "graphs": graphs, "model": model})
    _save_run(record)

    if as_json:
        print(json.dumps(result, indent=2))
        return code
    print(f"regress {record['id']} @{record['sha'][:10]}: {verdict.upper()} "
          f"(attempt {attempt_no}, {model}, {result['mode']}, {result['duration_seconds']}s)")
    for row in rows:
        line = f"  {row['status']:<14} {row['graph']}"
        if row["runs"] > 1:
            line += f"  ({row['runs']} runs)"
        print(line)
        if row["status"] == "needs_full_run":
            print("                 passed, but not on a full run after the last change")
        if row["status"] != "passed" and row.get("report"):
            print(f"                 report: {row['report']}")
    if escalation:
        esc = escalation if isinstance(escalation, dict) else {"reason": str(escalation)}
        print(f"  escalation     {esc.get('graph')} / {esc.get('node')}: {esc.get('reason')}")
        print(f"                 needed: {esc.get('needed')}")
    for item in over:
        print(f"  over budget    {item}")
    if changed:
        print(f"  fixes          {len(changes['commits'])} commit(s) on {record.get('branch')}, "
              f"{changes['lines']} lines in {len(changes['files'])} file(s)"
              f"{' -- UNCOMMITTED changes or untracked files left' if changes['uncommitted'] else ''}")
        if changes["outside_test_graph"]:
            print(f"                 outside the test graph: {', '.join(changes['outside_test_graph'])}")
        print(f"                 review before merging: {attempt_dir / 'fixes.patch'}")
    if attribution:
        print(f"  attribution    {len(attribution)} row(s): {attempt_dir / 'attribution.yaml'}")
    for gap in gaps:
        print(f"  ATTRIBUTION GAP  {gap}")
    if agent_started is False:
        print("  AGENT DID NOT START  the trace holds no tool call and no message from the agent.\n"
              "                 Do not rerun as it is.\n"
              f"                 episode {episode.get('outcome')}: {episode.get('error')}\n"
              f"                 server log: {attempt_dir / 'serve.log'}\n"
              "                 Usual cause: the provider CLI behind this model has no logged-in\n"
              "                 session on this machine (for CLAUDE_*: run `claude` once in a\n"
              "                 terminal and log in). Then run this command again.")
    elif episode.get("outcome") != "succeeded":
        print(f"  episode        {episode.get('outcome')}: {episode.get('error')}")
        if agent_started is None:
            print("                 whether the agent started is unknown: no local trace to read")
        elif agent_report is None and trace:
            print(f"  AGENT STOPPED WITHOUT REPORTING  it had started: {trace['tool_calls']} tool call(s), "
                  f"last tool {trace['last_tool']}, last event {trace['last_event']}.\n"
                  "                 This is not a login problem. Read the trace before running again:\n"
                  f"                 {attempt_dir / '.meta-harness' / 'evidence'}")
    if trace and trace["wait_tools"]:
        print(f"  WAIT TOOL USED  {', '.join(trace['wait_tools'])}: nothing wakes a session driven "
              "through meta-harness, so the agent stopped there")
    if trace and trace["tokens"]:
        cost = f", ${trace['cost_usd']:.2f}" if isinstance(trace["cost_usd"], (int, float)) else ""
        print(f"  usage          {trace['tokens'].get('total_tokens')} tokens, "
              f"{trace['tool_calls']} tool call(s){cost}")
    notes = (agent_report or {}).get("notes")
    if isinstance(notes, str) and notes.strip():
        print(f"  agent notes    {notes.strip()}")
    if report_problem:
        print(f"  agent report   {report_problem}")
    print(f"result     {attempt_dir / 'result.json'}")
    return code


# -------------------------------------------------------------- info / close

def info(run_id: str, start: str | Path = ".") -> int:
    record = load_run(run_id, start)
    for key in ("id", "sha", "ref", "branch", "worktree", "test_graph_root", "state", "created"):
        print(f"{key:<16} {record.get(key)}")
    for attempt in record["attempts"]:
        print(f"attempt {attempt['attempt']:<8} {attempt['verdict']}  {attempt['model']}  "
              f"{', '.join(attempt['graphs'])}")
    return 0


def list_runs(start: str | Path = ".") -> int:
    root = state_root(start)
    found = sorted(root.glob("*/run.json")) if root.is_dir() else []
    if not found:
        print("no regression worktrees")
        return 0
    running = {r["id"] for r in live_runs(start)}
    for path in found:
        record = json.loads(path.read_text())
        last = record["attempts"][-1]["verdict"] if record["attempts"] else "never run"
        if record["id"] in running:
            last = "RUNNING"
        gone = "" if Path(record["worktree"]).is_dir() else "  (worktree gone)"
        print(f"{record['id']:<16} @{record['sha'][:10]}  {last:<10} {record['worktree']}{gone}")
    return 0


def close(run_id: str, keep_state: bool = False, start: str | Path = ".") -> int:
    record = load_run(run_id, start)
    worktree = Path(record["worktree"])
    branch = record.get("branch")
    if record.get("adopted"):
        if keep_state:
            print(f"released {worktree} (adopted; left as it is); results kept in {record['state']}")
        else:
            shutil.rmtree(record["state"], ignore_errors=True)
            print(f"released {worktree} (adopted; the worktree and its branch are left as they are)")
        return 0
    if worktree.is_dir():
        here = Path.cwd().resolve()
        if here == worktree.resolve() or worktree.resolve() in here.parents:
            raise RegressError("close cannot run from inside the worktree it removes",
                               fix=f"cd {_main_worktree(start)} && skt regress close {run_id}")
        left = tree_changes(record)
        if left["uncommitted"]:
            what = ", ".join(left["untracked"][:5]) or "modified tracked files"
            raise RegressError(
                f"{worktree} holds uncommitted work ({what})",
                fix=f"commit or delete it in {worktree}, then close again",
            )
        # --force: build output under test_graph/build is untracked, and expected.
        _git(["worktree", "remove", "--force", str(worktree)], start)
    _git(["worktree", "prune"], start)
    kept = ""
    if branch:
        ahead = subprocess.run(["git", "rev-list", "--count", f"{record['sha']}..{branch}"],
                               cwd=str(start), capture_output=True, text=True)
        if ahead.returncode == 0 and ahead.stdout.strip() == "0":
            _git(["branch", "-D", branch], start)
        elif ahead.returncode == 0:
            # The agent's fixes. Deleting the only ref to them is not this command's call.
            kept = f"; branch {branch} kept ({ahead.stdout.strip()} fix commit(s))"
    if keep_state:
        print(f"closed {worktree}{kept}; results kept in {record['state']}")
    else:
        shutil.rmtree(record["state"], ignore_errors=True)
        print(f"closed {worktree}{kept}")
    return 0


def main(args) -> int:
    try:
        verb = args.verb
        if verb == "list":
            return list_runs()
        if not args.target:
            raise RegressError(f"skt regress {verb or '<verb>'}: missing argument",
                               fix="skt regress --help")
        if verb == "new":
            record = new(args.target, run_id=args.id, path=args.path,
                         test_graph_root=args.test_graph_root)
            print(f"created regression worktree {record['worktree']} @{record['sha'][:10]} "
                  f"on {record['branch']}")
            if not Path(record["test_graph_root"]).is_dir():
                print(f"note: no test graph project at {record['test_graph_root']} "
                      f"(--test-graph-root names another)")
            if (_main_worktree() / ".skill-manager").is_dir():
                print("note: this repository's checkouts carry a skill home and this worktree has none.\n"
                      "      It holds only what git tracks. If the graphs need the home, an index or\n"
                      "      other local setup, close this and use `skt regress adopt <ticket worktree>`.")
            print(f"next: skt regress run {record['id']} <graph>...   # or --all")
            return 0
        if verb == "adopt":
            record = adopt(args.target, run_id=args.id, test_graph_root=args.test_graph_root)
            print(f"adopted {record['worktree']} @{record['sha'][:10]} "
                  f"({record['branch'] or 'detached'}) as regression run {record['id']}")
            print("note: fix commits land on that branch; `skt regress close` leaves the worktree alone")
            print(f"next: skt regress run {record['id']} <graph>...   # or --all")
            return 0
        if verb == "run":
            return run(args.target, args.graphs, all_graphs=args.all, model=args.model,
                       timeout=args.timeout, meta_harness=args.meta_harness, runner=args.runner,
                       base_url=args.base_url, dry_run=args.dry_run, as_json=args.json,
                       fix=args.fix, isolated=args.isolated, env=args.env,
                       max_fix_lines=args.max_fix_lines, max_fix_files=args.max_fix_files,
                       max_runs=args.max_runs, stall_timeout=args.stall_timeout)
        if verb == "info":
            return info(args.target)
        if verb == "close":
            return close(args.target, keep_state=args.keep_state)
        raise RegressError(f"unknown verb {verb!r}", fix="skt regress --help")
    except RegressError as err:
        print(f"error: {err.reason}", file=sys.stderr)
        if err.fix:
            print(f"fix:   {err.fix}", file=sys.stderr)
        return err.code
    except (OSError, ValueError, KeyError) as err:
        # Exit 1 means "a graph is red". A crash in here is not that.
        print(f"error: skt regress failed before a verdict: {type(err).__name__}: {err}", file=sys.stderr)
        return EXIT_INCOMPLETE
