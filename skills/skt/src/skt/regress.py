"""skt regress: run the test graphs of one commit with a small-model agent.

The split this exists for: a big model writes a large batch of change and
never runs the graphs itself; a cheap model, driven through meta-harness,
runs them on a detached worktree of the pushed commit, retries what is
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
import shutil
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

DEFAULT_MODEL = "CLAUDE_haiku"
DEFAULT_TIMEOUT = 4 * 60 * 60
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
        for call in re.findall(r"side_effects\(([^)]*)\)", text):
            found.update(re.findall(r"[\"']([a-z]+:[A-Za-z0-9_.-]+)[\"']", call))
            found.update(f"environment:{m}" for m in
                         re.findall(r"SideEffect\.environment\(\s*[\"'](\w+)[\"']", call))
        if re.search(r"environment_?[rR]epository", text):
            found.add("environment:repository")
    return sorted(found)


def beyond_local(effects: list[str]) -> list[str]:
    return [e for e in effects if not e.startswith(LOCAL_EFFECTS)]


# ------------------------------------------------------------------- brief

def build_brief(run: dict, graphs: list[str], runner: Path, report_path: Path, *,
                fix: bool = False, isolated: str | None = None, effects: list[str] | None = None,
                max_fix_lines: int = DEFAULT_MAX_FIX_LINES, max_fix_files: int = DEFAULT_MAX_FIX_FILES,
                max_runs: int = DEFAULT_MAX_RUNS) -> str:
    tg = run["test_graph_root"]
    run_cmd = f"python3 {runner} <graph> --test-graph-root {tg}"
    resume_cmd = f"python3 {runner} --resume <runId> --test-graph-root {tg}"
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
- the failure is in the isolated environment itself and you cannot repair it from this worktree.
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
- If a failure needs a change to pass, say what is needed in `escalation`:
    {escalation}
"""
    effects_line = ", ".join(effects) if effects else "none found in the node sources"
    return f"""You are a test-graph regression runner. Your job is to run the test graphs listed
below on one commit and report exactly what happened.

Commit under test: {run['sha']}
Worktree (your working directory): {run['worktree']}
Test graph project: {tg}
Side effects these graphs declare: {effects_line}

GRAPHS TO RUN, in this order:
{chr(10).join(f'  - {g}' for g in graphs)}

FOR EACH GRAPH
1. Run it:
     {run_cmd}
   Run one graph at a time and wait for it. A run can take tens of minutes: use the longest
   command timeout you have, or run it in the background and wait. Slow is not failed.
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

`attribution` is an empty list only when no run failed at all. For a graph you did not
get to, use `not_run`. Then reply with one line: the path of the file you wrote.
"""


# ------------------------------------------------------------------ verdict

def tree_changes(run: dict) -> dict:
    """What the agent changed, measured from git and not from its report."""
    wt = run["worktree"]
    files, lines = [], 0
    for row in _git(["diff", "--numstat", run["sha"]], wt).splitlines():
        added, deleted, path = row.split("\t", 2)
        files.append(path)
        lines += (int(added) if added.isdigit() else 0) + (int(deleted) if deleted.isdigit() else 0)
    status = _git(["status", "--porcelain", "--untracked-files=no"], wt)
    head = _git(["rev-parse", "HEAD"], wt)
    tg_rel = os.path.relpath(run["test_graph_root"], wt)
    return {
        "files": files,
        "lines": lines,
        "commits": _git(["rev-list", f"{run['sha']}..HEAD"], wt).split(),
        "uncommitted": bool(status.strip()),
        "outside_test_graph": [f for f in files if not f.startswith(tg_rel + "/")],
        "last_commit_time": int(_git(["log", "-1", "--format=%ct", "HEAD"], wt)) if head != run["sha"] else None,
    }


def read_verdict(tg_root: str, graphs: list[str], since: float,
                 changed_at: float | None = None) -> tuple[list[dict], list[dict]]:
    """Per requested graph, what the graph runs themselves recorded since ``since``.

    A report older than the invocation is ignored: ``validation-reports``
    keeps earlier green runs, so a graph that never executed looks green
    there. When the tree was changed during the run (``changed_at``), a pass
    counts only if it is a full run that finished after the last change.

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
        via_resume = last["mode"] not in (None, "full")
        if status == "passed" and changed_at is not None and (via_resume or last["mtime"] < changed_at):
            # Green on a tree that has since changed, or only from the failed node on.
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


def _agent_env() -> dict:
    # A session spawned from inside another agent session must not inherit its identity.
    return {k: v for k, v in os.environ.items()
            if not (k == "CLAUDECODE" or k.startswith("CLAUDE_CODE_"))}


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


def run_episode(binary: str, attempt_dir: Path, request: dict, base_url: str | None) -> tuple[dict, str]:
    """Drive one episode. Starts a private ``serve`` unless ``base_url`` names one."""
    request_path = attempt_dir / "request.json"
    result_path = attempt_dir / "episode.json"
    request_path.write_text(json.dumps(request, indent=2) + "\n")
    serve = None
    log = None
    try:
        if base_url is None:
            port = _free_port()
            base_url = f"http://127.0.0.1:{port}"
            log = open(attempt_dir / "serve.log", "w")
            serve = subprocess.Popen(
                [binary, "--project-root", str(attempt_dir), "serve", "--port", str(port)],
                stdout=log, stderr=subprocess.STDOUT, env=_agent_env(), cwd=str(attempt_dir),
            )
            _wait_listening(base_url, serve)
        subprocess.run(
            [binary, "--project-root", str(attempt_dir), "episode", "--base-url", base_url,
             "--request", str(request_path), "--output", str(result_path)],
            capture_output=True, text=True, timeout=request["timeoutSeconds"] + 300,
        )
    except subprocess.TimeoutExpired:
        pass
    finally:
        if serve is not None:
            serve.terminate()
            try:
                serve.wait(timeout=30)
            except subprocess.TimeoutExpired:
                serve.kill()
        if log is not None:
            log.close()
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
        max_runs: int = DEFAULT_MAX_RUNS, start: str | Path = ".") -> int:
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

    attempt_no = len(record["attempts"]) + 1
    attempt_dir = Path(record["state"]) / f"attempt-{attempt_no}"
    attempt_dir.mkdir(parents=True, exist_ok=True)
    report_path = attempt_dir / "agent-report.json"
    brief = build_brief(record, graphs, runner_path, report_path, fix=fix, isolated=isolated,
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
    started = time.time()
    episode, used_url = run_episode(binary, attempt_dir, request, base_url)

    changes = tree_changes(record)
    changed = bool(changes["files"])
    rows, reds = read_verdict(record["test_graph_root"], graphs, started,
                              changed_at=(changes["last_commit_time"] or time.time()) if changed else None)
    agent_report, report_problem = read_agent_report(report_path)
    escalation = (agent_report or {}).get("escalation") or None
    over = []
    if changed and not fix:
        over.append("the agent changed the tree in a report-only run")
    if changes["lines"] > max_fix_lines:
        over.append(f"{changes['lines']} changed lines (limit {max_fix_lines})")
    if len(changes["files"]) > max_fix_files:
        over.append(f"{len(changes['files'])} changed files (limit {max_fix_files})")
    statuses = {r["status"] for r in rows}
    if escalation or over:
        verdict, code = "escalated", EXIT_ESCALATED
    elif statuses & {"failed", "errored"}:
        verdict, code = "red", EXIT_RED
    elif statuses == {"passed"} and not changes["uncommitted"]:
        verdict, code = "green", EXIT_GREEN
    else:
        verdict, code = "incomplete", EXIT_INCOMPLETE
    gaps = attribution_gaps(agent_report, reds)
    attribution = [r for r in (agent_report or {}).get("attribution") or [] if isinstance(r, dict)]
    if attribution:
        write_attribution_yaml(attempt_dir / "attribution.yaml", record, attempt_no, attribution)
    if changed:
        (attempt_dir / "fixes.patch").write_text(_git(["diff", record["sha"]], record["worktree"]) + "\n")

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
              f"{' -- UNCOMMITTED changes left' if changes['uncommitted'] else ''}")
        if changes["outside_test_graph"]:
            print(f"                 outside the test graph: {', '.join(changes['outside_test_graph'])}")
        print(f"                 review before merging: {attempt_dir / 'fixes.patch'}")
    if attribution:
        print(f"  attribution    {len(attribution)} row(s): {attempt_dir / 'attribution.yaml'}")
    for gap in gaps:
        print(f"  ATTRIBUTION GAP  {gap}")
    if episode.get("outcome") != "succeeded":
        print(f"  episode        {episode.get('outcome')}: {episode.get('error')}")
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
    for path in found:
        record = json.loads(path.read_text())
        last = record["attempts"][-1]["verdict"] if record["attempts"] else "never run"
        gone = "" if Path(record["worktree"]).is_dir() else "  (worktree gone)"
        print(f"{record['id']:<16} @{record['sha'][:10]}  {last:<10} {record['worktree']}{gone}")
    return 0


def close(run_id: str, keep_state: bool = False, start: str | Path = ".") -> int:
    record = load_run(run_id, start)
    worktree = Path(record["worktree"])
    branch = record.get("branch")
    if worktree.is_dir():
        if tree_changes(record)["uncommitted"]:
            raise RegressError(
                f"{worktree} has uncommitted changes to tracked files",
                fix=f"commit or discard them in {worktree}, then close again",
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
            print(f"next: skt regress run {record['id']} <graph>...   # or --all")
            return 0
        if verb == "run":
            return run(args.target, args.graphs, all_graphs=args.all, model=args.model,
                       timeout=args.timeout, meta_harness=args.meta_harness, runner=args.runner,
                       base_url=args.base_url, dry_run=args.dry_run, as_json=args.json,
                       fix=args.fix, isolated=args.isolated, env=args.env,
                       max_fix_lines=args.max_fix_lines, max_fix_files=args.max_fix_files,
                       max_runs=args.max_runs)
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
