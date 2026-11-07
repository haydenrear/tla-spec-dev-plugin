#!/usr/bin/env python3
"""Run a test graph by name (or several, or every registered graph).

Every ``testGraph("X") { ... }`` in build.gradle.kts registers a Gradle
task named ``X``. This script invokes ``./gradlew X`` for a single graph,
``./gradlew A B C`` for several, or ``./gradlew validationRunAll`` to fan
out across every registered graph in declared order. Each
``RunTestGraphTask`` rolls its own per-node envelopes into
``summary.json`` + ``report.md`` inline at the end of plan execution, so
every run dir under ``build/validation-reports/<runId>/`` gets a report
regardless of how many graphs the invocation spans.

A SWEEP (``--all``, more than one graph, or ``--continue``) keeps going
past a red graph (Gradle ``--continue``) and ends with a summary of the
graphs this invocation selected, executed, passed, failed, errored and did
not run.
Those counts come from a ledger written by ``sweep-ledger.init.gradle``
during THIS Gradle invocation -- never from ``build/validation-reports/``,
which still holds passing reports from earlier runs (DEF-OUN-023). The
summary is also written to ``build/validation-sweeps/<sweepId>/sweep.json``.

FAILED and ERRORED need opposite responses, so they are never merged:

    FAILED   a node completed and an assertion was red -> investigate the code
    ERRORED  the run did not complete: the Gradle process or daemon died
             mid-task, or a node never reported a verdict (crashed, killed by
             a signal, timed out) -> retry it or fix the environment

The split uses positive evidence, not message matching: a task that started
and never finished is ERRORED, and a task that threw is FAILED only when the
graph's own summary.json says ``failed``.

Exit codes (every invocation, one graph or many): 0 all selected graphs
passed; 1 any graph FAILED, or a graph did not run; 3 (SWEEP_EXIT_ERRORED) at
least one graph ERRORED and none FAILED.

outcome.json (issue #185). EVERY invocation -- one graph, several, ``--all``, a
resume -- writes ``build/validation-sweeps/<id>/outcome.json`` and prints that
path as the LAST line of stdout, so a caller reads the outcome instead of
grepping logs. Per graph and per node it records the status
(``passed | failed | errored | not_run``), a ``cause``, the duration, the
timeout bound, the host load average at start and end, and the report
directory. A graph task that threw before allocating its run directory -- for
example a node describe that errored on every retry
(``NodeDescribeErroredException``) -- ran no node and is ERRORED, never FAILED.

``--continue-after-failure`` (issue #168) keeps running the NODES of a graph
after one fails (``TESTGRAPH_CONTINUE_AFTER_FAILURE=1`` for PlanExecutor). It is
not ``--continue``, which spans GRAPHS.

Usage:
    run.py <graph-name>           # single graph (e.g. run.py smoke)
    run.py doc-smoke artifact-dag smoke   # several graphs, a red one does not stop the rest
    run.py --all                  # every registered graph, serial, keeps going past a red
    run.py --all --fail-fast      # stop at the first red graph (the old behaviour)
    run.py scenarios --continue-after-failure   # every node runs and reports its own status
    run.py --resume build/validation-reports/<runId>          # from its first failed/errored node
    run.py --resume <runId> --from-node login.smoke           # from a chosen node, downstream too
    run.py --resume <runId> --only-node login.smoke           # that node only
    run.py --resume <previous-resume>/outcome.json            # a resume of a resume runs the tail
    run.py smoke --resume-from-build build/validation-reports/<runId> --resume-from-node login.smoke
    run.py smoke --resume-from-build build/validation-reports/<runId> --run-only-node login.smoke

``--resume <report>`` (issue #186) is the front door for resuming: it wraps the
chained resume of #180, accepts a relative path, a bare runId, a file inside a
report or an ``outcome.json``, reads the graph name from the report, and writes
the same ``outcome.json`` as a fresh run (plus a ``resume`` block naming the
source report, node and mode). Relative ``--resume-from-build`` paths resolve
the same way (#138 SF-023).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

from _common import add_test_graph_root_arg, run_gradle, target_project_root

SWEEP_LEDGER_ENV = "TEST_GRAPH_SWEEP_LEDGER"
SWEEP_INIT_SCRIPT = Path(__file__).resolve().parent / "sweep-ledger.init.gradle"
SWEEP_SCHEMA = "test-graph.sweep.v1"
SWEEP_EXIT_ERRORED = 3
OUTCOME_SCHEMA = "test-graph.outcome.v1"
OUTCOME_FILE = "outcome.json"
CONTINUE_AFTER_FAILURE_ENV = "TESTGRAPH_CONTINUE_AFTER_FAILURE"
LOAD_SAMPLE_SECONDS = 0.5


def allocate_sweep_dir(test_graph_root: Path) -> Path:
    """Create a fresh ``build/validation-sweeps/<UTC stamp>[-n]`` directory."""
    base = test_graph_root / "build" / "validation-sweeps"
    base.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S", time.gmtime())
    for suffix in range(10_000):
        candidate = base / (stamp if suffix == 0 else f"{stamp}-{suffix}")
        try:
            candidate.mkdir()
            return candidate
        except FileExistsError:
            continue
    raise RuntimeError(f"could not allocate a unique sweep directory under {base}")


def read_ledger(path: Path) -> list[dict]:
    """Parse the init script's JSON lines. A missing file means no events."""
    if not path.is_file():
        return []
    records = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            record = json.loads(line)
        except ValueError:
            continue
        if isinstance(record, dict):
            records.append(record)
    return records


def report_status(run_dirs: list[str]) -> str | None:
    """The graph's own verdict from the newest ``summary.json`` it wrote, if any.

    The SDK writes ``failed`` only when nodes completed with red assertions and
    ``errored`` when a node did not deliver a verdict, so this is the positive
    signal that separates a red node from a run that broke. ``None`` means the
    graph wrote no report at all.
    """
    for run_dir in reversed(run_dirs):
        path = Path(run_dir) / "summary.json"
        if not path.is_file():
            continue
        try:
            status = json.loads(path.read_text(encoding="utf-8")).get("status")
        except (ValueError, OSError, AttributeError):
            continue
        if isinstance(status, str):
            return status
    return None


def failed_nodes(run_dirs: list[str]) -> list[str]:
    """Node ids whose envelope says ``failed`` (a completed, red assertion)."""
    red = []
    for run_dir in run_dirs:
        for path in sorted((Path(run_dir) / "envelope").glob("*.json")):
            try:
                envelope = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            if isinstance(envelope, dict) and envelope.get("status") == "failed":
                red.append(envelope.get("nodeId") or path.stem)
    return red


def summarize_sweep(requested: list[str], records: list[dict], run_all: bool) -> dict:
    """Compute the sweep outcome from this invocation's ledger events only.

    ``requested`` is the graph names given on the command line (empty for
    ``--all``). For ``--all`` the selected set is every graph task Gradle
    scheduled; for named graphs it is the names themselves, in Gradle's
    execution order where Gradle scheduled them.
    """
    scheduled: list[str] = []
    for record in records:
        if record.get("event") != "scheduled":
            continue
        name = record.get("task")
        wanted = bool(record.get("graph")) if run_all else name in requested
        if wanted and name not in scheduled:
            scheduled.append(name)

    if run_all:
        selected = list(scheduled)
    else:
        selected = list(scheduled) + [g for g in requested if g not in scheduled]

    finished: dict[str, dict] = {}
    started: set[str] = set()
    for record in records:
        if record.get("task") not in selected:
            continue
        if record.get("event") == "finished":
            finished[record["task"]] = record
        elif record.get("event") == "started":
            started.add(record["task"])

    results = []
    for graph in selected:
        record = finished.get(graph)
        entry = {"graph": graph, "status": "not_run", "seconds": None,
                 "run_dirs": [], "reason": None, "report_status": None}
        if record is None and graph in started:
            entry["status"] = "errored"
            entry["reason"] = (
                "started, but never finished: the Gradle process ended mid-task "
                "(daemon disappeared, killed by a signal, or interrupted)"
            )
        elif record is None:
            entry["reason"] = (
                "scheduled, but Gradle never started it"
                if graph in scheduled
                else "Gradle never scheduled it (configuration failed or unknown task)"
            )
        elif record.get("outcome") == "passed":
            entry["status"] = "passed"
            entry["seconds"] = record.get("seconds")
            entry["run_dirs"] = list(record.get("runDirs") or [])
            entry["report_status"] = report_status(entry["run_dirs"])
        elif record.get("outcome") == "failed":
            entry["seconds"] = record.get("seconds")
            entry["run_dirs"] = list(record.get("runDirs") or [])
            verdict = report_status(entry["run_dirs"])
            entry["report_status"] = verdict
            failure = record.get("failure")
            red_nodes = failed_nodes(entry["run_dirs"])
            if verdict == "failed":
                entry["status"] = "failed"
                entry["reason"] = failure
            elif red_nodes:
                # A graph whose summary says errored can still hold a node that
                # completed red (e.g. under --continue-after-failure). A red
                # assertion outranks an error, at graph level as for the sweep.
                entry["status"] = "failed"
                entry["reason"] = (
                    f"node(s) {', '.join(red_nodes)} completed with a red assertion; "
                    f"the graph's summary.json says {verdict!r} because other nodes "
                    "did not report a verdict"
                )
            else:
                entry["status"] = "errored"
                cause = (
                    "the graph task threw before allocating a run directory, so no "
                    "node ran (for example a node describe errored on every retry: "
                    "NodeDescribeErroredException)"
                    if verdict is None and not entry["run_dirs"]
                    else "the graph wrote no summary.json, so no node reported a verdict"
                    if verdict is None
                    else f"the graph's summary.json says {verdict!r}: a node did not "
                         "report a verdict (crashed, killed or timed out)"
                )
                entry["reason"] = f"{cause}: {failure}" if failure else cause
        else:
            entry["reason"] = record.get("skipMessage") or "skipped by Gradle"
        results.append(entry)

    def count(status: str) -> int:
        return sum(1 for r in results if r["status"] == status)

    selection_known = not run_all or bool(scheduled)
    return {
        "schema": SWEEP_SCHEMA,
        "mode": "all" if run_all else "graphs",
        "selection_known": selection_known,
        "graphs_selected": len(selected) if selection_known else None,
        "graphs_executed": count("passed") + count("failed") + count("errored"),
        "graphs_passed": count("passed"),
        "graphs_failed": count("failed"),
        "graphs_errored": count("errored"),
        "graphs_not_run": count("not_run"),
        "results": results,
    }


def sweep_exit_code(gradle_rc: int, summary: dict) -> int:
    """Non-zero whenever the sweep was not a complete green run.

    1 when any graph FAILED (a red node: investigate the code);
    SWEEP_EXIT_ERRORED when a graph ERRORED and none failed (the run broke:
    retry or fix the environment). Otherwise 1 for a non-zero Gradle exit or a
    graph that did not run. Never any other code: callers branch on 0/1/3.
    """
    if summary["graphs_failed"]:
        return 1
    if summary.get("graphs_errored"):
        return SWEEP_EXIT_ERRORED
    if gradle_rc != 0:
        return 1
    if not summary["selection_known"] or summary["graphs_not_run"]:
        return 1
    return 0


def _display_path(path: str, root: Path) -> str:
    try:
        return str(Path(path).relative_to(root))
    except ValueError:
        return path


def format_summary(summary: dict, sweep_id: str, root: Path, record_path: Path) -> str:
    labels = {"passed": "PASSED", "failed": "FAILED", "errored": "ERRORED", "not_run": "NOT RUN"}
    selected = summary["graphs_selected"]
    lines = [
        "",
        f"== test graph sweep {sweep_id} ==",
        "Counted from this invocation's own task outcomes, not from build/validation-reports/.",
        f"graphs_selected={'unknown' if selected is None else selected}  "
        f"graphs_executed={summary['graphs_executed']}  "
        f"graphs_passed={summary['graphs_passed']}  "
        f"graphs_failed={summary['graphs_failed']}  "
        f"graphs_errored={summary['graphs_errored']}  "
        f"graphs_not_run={summary['graphs_not_run']}",
    ]
    if not summary["selection_known"]:
        lines.append(
            "Gradle never reached task execution, so the selected set is unknown "
            "and no graph executed."
        )
    width = max([len(r["graph"]) for r in summary["results"]] + [5])
    for r in summary["results"]:
        detail = []
        if r["seconds"] is not None:
            detail.append(f"{r['seconds']:.1f}s")
        detail.extend(_display_path(d, root) for d in r["run_dirs"])
        if r["status"] != "passed" and r["reason"]:
            detail.append(f"({r['reason'].splitlines()[0]})")
        lines.append(f"  {labels[r['status']]:<8} {r['graph']:<{width}}  {'  '.join(detail)}".rstrip())
    if summary["graphs_errored"]:
        lines.append(
            "ERRORED = the run did not complete (runner, daemon or node process died, "
            "or a node never reported a verdict): retry it or fix the environment. "
            "FAILED = a node completed and an assertion was red: investigate the code."
        )
    lines.append(f"sweep record: {record_path}")
    return "\n".join(lines)


def _utc(ts: float | None) -> str | None:
    if ts is None:
        return None
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat().replace("+00:00", "Z")


def _parse_instant(value: object) -> float | None:
    """Epoch seconds from an envelope's ISO-8601 ``...Z`` instant, or None."""
    if not isinstance(value, str) or not value:
        return None
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    # Java prints up to nanoseconds; Python parses at most microseconds.
    text = re.sub(r"(\.\d{6})\d+", r"\1", text)
    try:
        return datetime.fromisoformat(text).timestamp()
    except ValueError:
        return None


def _loadavg() -> list[float] | None:
    try:
        return [round(v, 2) for v in os.getloadavg()]
    except (AttributeError, OSError):
        return None


class InvocationMonitor:
    """Samples the host load average and stamps ledger events as they land.

    The SDK's envelopes carry node start/end instants but no host load, and the
    ledger carries no wall-clock time, so a background thread records both while
    Gradle runs. ``load_at(t)`` answers "what was the 1/5/15-minute load average
    when this graph or node started/ended" from the nearest earlier sample.
    """

    def __init__(self, ledger: Path, interval: float = LOAD_SAMPLE_SECONDS) -> None:
        self.ledger = ledger
        self.interval = interval
        self.samples: list[tuple[float, list[float]]] = []
        self.event_times: dict[tuple[str, str], float] = {}
        self._offset = 0
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._loop, daemon=True)

    def start(self) -> "InvocationMonitor":
        self._sample()
        self._thread.start()
        return self

    def stop(self) -> None:
        self._stop.set()
        self._thread.join(timeout=5)
        self._sample()

    def _sample(self) -> None:
        now = time.time()
        load = _loadavg()
        if load is not None:
            self.samples.append((now, load))
        self._scan_ledger(now)

    def _scan_ledger(self, now: float) -> None:
        try:
            with self.ledger.open("rb") as fh:
                fh.seek(self._offset)
                chunk = fh.read()
        except OSError:
            return
        complete, _, _ = chunk.rpartition(b"\n")
        if not complete:
            return
        self._offset += len(complete) + 1
        for line in complete.decode("utf-8", errors="replace").splitlines():
            try:
                record = json.loads(line)
            except ValueError:
                continue
            if isinstance(record, dict) and record.get("task") and record.get("event"):
                self.event_times.setdefault((record["event"], record["task"]), now)

    def _loop(self) -> None:
        while not self._stop.wait(self.interval):
            self._sample()

    def load_at(self, ts: float | None) -> list[float] | None:
        if ts is None or not self.samples:
            return None
        best = self.samples[0][1]
        for when, load in self.samples:
            if when > ts:
                break
            best = load
        return best


_TIMED_OUT = re.compile(r"timed out after (\S+?)(?:;|\s|$)")
_DURATION = re.compile(r"^(\d+(?:\.\d+)?)(ms|s|m|h)?$")


def _duration_seconds(text: str) -> float | None:
    match = _DURATION.match(text.strip())
    if not match:
        return None
    value, unit = float(match.group(1)), match.group(2) or "s"
    return value * {"ms": 0.001, "s": 1, "m": 60, "h": 3600}[unit]


def _node_cause(status: str, reason: str | None, exit_code: object) -> str | None:
    """Why a node is not green, from positive evidence in its envelope."""
    if status == "passed":
        return None
    if status == "failed":
        return "assertion"
    if status == "not_run":
        return "skipped"
    text = reason or ""
    if "timed out" in text:
        return "timeout"
    if isinstance(exit_code, int) and (exit_code > 128 or exit_code < -1):
        return "signal"
    return "crash"


def collect_nodes(run_dir: str, monitor: InvocationMonitor | None) -> list[dict]:
    """Per-node outcome rows from one graph run directory.

    ``skipped`` envelopes and expected nodes with no envelope are ``not_run``;
    a node whose input context was written but which never delivered an
    envelope was in flight when the runner died, so it is ``errored``.
    """
    root = Path(run_dir)
    expected: list[str] = []
    for name in ("execution-scope.json", "summary.json"):
        try:
            doc = json.loads((root / name).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        ids = doc.get("expectedNodeIds") or (doc.get("execution") or {}).get("expectedNodeIds")
        if isinstance(ids, list):
            expected = [i for i in ids if isinstance(i, str)]
            break
    envelopes: dict[str, dict] = {}
    env_dir = root / "envelope"
    if env_dir.is_dir():
        for path in sorted(env_dir.glob("*.json")):
            try:
                envelope = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            if isinstance(envelope, dict):
                envelopes[envelope.get("nodeId") or path.stem] = envelope
    order = expected + [n for n in envelopes if n not in expected]

    nodes = []
    for node in order:
        envelope = envelopes.get(node)
        row = {"node": node, "status": "not_run", "cause": None, "reason": None,
               "started_at": None, "ended_at": None, "duration_seconds": None,
               "timeout_bound_seconds": None, "timeout_bound": None,
               "load_avg_start": None, "load_avg_end": None, "spawn_exit_code": None,
               "report_dir": str(root), "envelope": None}
        if envelope is None:
            in_flight = (root / "context" / f"{node}.input.json").is_file()
            row["status"] = "errored" if in_flight else "not_run"
            row["cause"] = "runner_died" if in_flight else "skipped"
            row["reason"] = (
                "its input context was written but it never delivered an envelope: "
                "the runner died while it ran" if in_flight
                else "no envelope: the graph stopped before this node"
            )
            nodes.append(row)
            continue
        raw = envelope.get("status")
        status = {"passed": "passed", "failed": "failed", "skipped": "not_run"}.get(raw, "errored")
        reason = envelope.get("failureMessage") or envelope.get("reason")
        start = _parse_instant(envelope.get("executorStartedAt") or envelope.get("startedAt"))
        end = _parse_instant(envelope.get("executorEndedAt") or envelope.get("endedAt"))
        row.update({
            "status": status,
            "cause": _node_cause(status, reason, envelope.get("spawnExitCode")),
            "reason": reason,
            "started_at": _utc(start), "ended_at": _utc(end),
            "duration_seconds": round(end - start, 3) if start is not None and end is not None else None,
            "spawn_exit_code": envelope.get("spawnExitCode"),
            "envelope": str(env_dir / f"{node}.json"),
        })
        bound = _TIMED_OUT.search(reason or "")
        if bound:
            row["timeout_bound"] = bound.group(1)
            row["timeout_bound_seconds"] = _duration_seconds(bound.group(1))
        if status == "not_run":
            row["started_at"] = row["ended_at"] = row["duration_seconds"] = None
        elif monitor is not None:
            row["load_avg_start"] = monitor.load_at(start)
            row["load_avg_end"] = monitor.load_at(end)
        nodes.append(row)
    return nodes


def _graph_cause(entry: dict) -> str | None:
    status, verdict = entry["status"], entry.get("report_status")
    if status == "passed":
        return None
    if status == "failed":
        return "assertion"
    if status == "not_run":
        return "not_scheduled" if "never scheduled" in (entry.get("reason") or "") else "skipped"
    if "never finished" in (entry.get("reason") or ""):
        return "runner_died"
    if verdict is None and not entry.get("run_dirs"):
        return "no_run_dir"
    return "node_errored" if verdict is not None else "no_report"


def build_outcome(summary: dict, monitor: InvocationMonitor | None, *, started: float,
                  ended: float, gradle_rc: int, exit_code: int, argv: list[str],
                  continue_after_failure: bool, record_dir: Path) -> dict:
    """The machine-readable outcome of one run.py invocation (``outcome.json``)."""
    graphs = []
    for entry in summary["results"]:
        g_start = g_end = None
        if monitor is not None:
            g_start = monitor.event_times.get(("started", entry["graph"]))
            g_end = monitor.event_times.get(("finished", entry["graph"]))
        nodes: list[dict] = []
        for run_dir in entry["run_dirs"]:
            nodes.extend(collect_nodes(run_dir, monitor))
        ran = entry["status"] != "not_run"
        graphs.append({
            "graph": entry["graph"],
            "status": entry["status"],
            "cause": _graph_cause(entry),
            "reason": entry["reason"],
            "report_status": entry["report_status"],
            "started_at": _utc(g_start) if ran else None,
            "ended_at": _utc(g_end) if ran else None,
            "duration_seconds": entry["seconds"],
            # A graph task has no timeout of its own: each node carries its bound.
            "timeout_bound_seconds": None,
            "load_avg_start": monitor.load_at(g_start) if monitor and ran and g_start else None,
            "load_avg_end": monitor.load_at(g_end) if monitor and ran and g_end else None,
            "report_dirs": list(entry["run_dirs"]),
            "report_dir": entry["run_dirs"][-1] if entry["run_dirs"] else None,
            "nodes": nodes,
        })

    def worst(statuses: list[str]) -> str:
        for status in ("failed", "errored", "not_run"):
            if status in statuses:
                return status
        return "passed" if statuses else "not_run"

    counts = {f"graphs_{s}": sum(1 for g in graphs if g["status"] == s)
              for s in ("passed", "failed", "errored", "not_run")}
    all_nodes = [n for g in graphs for n in g["nodes"]]
    node_counts = {f"nodes_{s}": sum(1 for n in all_nodes if n["status"] == s)
                   for s in ("passed", "failed", "errored", "not_run")}
    return {
        "schema": OUTCOME_SCHEMA,
        "status": worst([g["status"] for g in graphs]) if summary["selection_known"] else "not_run",
        "exit_code": exit_code,
        "gradle_exit_code": gradle_rc,
        "exit_codes": {"0": "passed", "1": "failed or not run", str(SWEEP_EXIT_ERRORED): "errored"},
        "command": ["run.py", *argv],
        "mode": summary["mode"],
        "continue_after_failure": continue_after_failure,
        "started_at": _utc(started),
        "ended_at": _utc(ended),
        "duration_seconds": round(ended - started, 3),
        "load_avg_start": monitor.load_at(started) if monitor else None,
        "load_avg_end": monitor.load_at(ended) if monitor else None,
        "report_dir": str(record_dir),
        "selection_known": summary["selection_known"],
        **counts,
        **node_counts,
        "graphs": graphs,
    }


def format_outcome_line(outcome: dict) -> str:
    """One human line per graph for a single-graph run (a sweep prints its table)."""
    labels = {"passed": "PASSED", "failed": "FAILED", "errored": "ERRORED", "not_run": "NOT RUN"}
    lines = []
    for g in outcome["graphs"]:
        nodes = ", ".join(f"{n['node']}={n['status']}" for n in g["nodes"] if n["status"] != "passed")
        cause = f" ({g['cause']})" if g["cause"] else ""
        lines.append(f"{labels[g['status']]} {g['graph']}{cause}" + (f": {nodes}" if nodes else ""))
    return "\n".join(lines)


REPORTS_SUBDIR = Path("build") / "validation-reports"
_REPORT_FILES = ("summary.json", "report.md", "execution-scope.json")
RESUMABLE_STATUSES = ("failed", "errored")


class ReportPathError(ValueError):
    """A ``--resume`` / ``--resume-from-build`` argument names no usable report."""


def resolve_report_dir(spec: str, test_graph_root: Path) -> Path:
    """Turn what a caller has in hand into an absolute report directory.

    Accepted (issue #186, #138 SF-023): a report directory, absolute or
    RELATIVE -- tried against the current directory, then the test-graph root,
    then ``<root>/build/validation-reports/`` (so a bare ``<runId>`` works) --
    a file inside one (``summary.json``, ``report.md``,
    ``execution-scope.json``), or a single-graph ``outcome.json``, whose graph
    ``report_dir`` is the run to resume. That last form is what makes chaining
    a one-liner: the previous resume's last stdout line is the next one's
    ``--resume`` argument.

    The result is lexically normalized (``os.path.abspath``), never
    symlink-resolved: the Gradle task stays the authority that the directory
    is a real, direct child of the configured report root.
    """
    expanded = Path(os.path.expanduser(spec))
    if expanded.is_absolute():
        candidates = [expanded]
    else:
        candidates = [Path.cwd() / expanded, test_graph_root / expanded,
                      test_graph_root / REPORTS_SUBDIR / expanded]
    for candidate in candidates:
        path = Path(os.path.abspath(candidate))
        if path.is_dir():
            return path
        if path.is_file():
            if path.name == OUTCOME_FILE:
                return _report_dir_from_outcome(path)
            if path.name in _REPORT_FILES:
                return path.parent
            raise ReportPathError(
                f"{spec!r} is a file but not a report: pass a report directory, "
                f"one of {', '.join(_REPORT_FILES)}, or an {OUTCOME_FILE}")
    tried = "\n  ".join(str(Path(os.path.abspath(c))) for c in candidates)
    raise ReportPathError(f"no report directory found for {spec!r}; tried:\n  {tried}")


def _report_dir_from_outcome(path: Path) -> Path:
    try:
        outcome = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ReportPathError(f"cannot read {path}: {exc}") from exc
    dirs = [g.get("report_dir") for g in outcome.get("graphs") or [] if isinstance(g, dict)]
    dirs = [d for d in dirs if d]
    if len(dirs) != 1:
        raise ReportPathError(
            f"{path} records {len(dirs)} graph report directories; resume takes one "
            "graph -- pass that graph's report directory instead")
    report = Path(dirs[0])
    if not report.is_dir():
        raise ReportPathError(f"{path} points at {report}, which is not a directory")
    return Path(os.path.abspath(report))


def report_graph_name(report_dir: Path) -> str | None:
    """The graph a report belongs to, from ``execution-scope.json`` or ``summary.json``."""
    for name in ("execution-scope.json", "summary.json"):
        try:
            doc = json.loads((report_dir / name).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        graph = doc.get("graphName") or (doc.get("execution") or {}).get("graphName")
        if isinstance(graph, str) and graph:
            return graph
    return None


def first_resumable_node(report_dir: Path) -> str | None:
    """The report's first FAILED or ERRORED node, in plan order.

    In a resume report the plan order is the selected-to-tail scope, so a
    resume of a resume picks the first red node of the TAIL, never a node an
    earlier attempt already passed.
    """
    for row in collect_nodes(str(report_dir), None):
        if row["status"] in RESUMABLE_STATUSES:
            return row["node"]
    return None


def run_invocation(args: argparse.Namespace, graphs: list[str], *, sweep: bool,
                   argv: list[str]) -> int:
    """Run one or more graphs under the ledger and always write outcome.json."""
    root = target_project_root(args.test_graph_root)
    sweep_dir = allocate_sweep_dir(root)
    ledger = sweep_dir / "ledger.jsonl"
    ledger.touch()
    gradle_args = ["--console=plain", "--init-script", str(SWEEP_INIT_SCRIPT)]
    if sweep and not args.fail_fast:
        gradle_args.append("--continue")
    gradle_args += ["validationRunAll"] if args.run_all else graphs
    if args.resume_from_build:
        # main() already resolved this to an absolute, lexically normalized
        # report directory (resolve_report_dir); the Gradle task is the
        # authority that verifies it is a real direct report-root child.
        gradle_args.append(f"--resume-from-build={args.resume_from_build}")
        if args.resume_from_node:
            gradle_args.append(f"--resume-from-node={args.resume_from_node}")
        if args.run_only_node:
            gradle_args.append(f"--run-only-node={args.run_only_node}")
    extra_env = {SWEEP_LEDGER_ENV: str(ledger)}
    if args.continue_after_failure:
        extra_env[CONTINUE_AFTER_FAILURE_ENV] = "1"
    if sweep:
        what = "every registered graph" if args.run_all else ", ".join(graphs)
        policy = "stopping at the first red graph" if args.fail_fast else "continuing past red graphs"
        print(f"sweep {sweep_dir.name}: {what} ({policy})", flush=True)

    monitor = InvocationMonitor(ledger).start()
    started = time.time()
    try:
        rc = run_gradle(gradle_args, str(root), extra_env=extra_env)
    except KeyboardInterrupt:
        rc = 130
    finally:
        ended = time.time()
        monitor.stop()

    summary = summarize_sweep(graphs, read_ledger(ledger), args.run_all)
    exit_code = sweep_exit_code(rc, summary)
    if sweep:
        summary["sweep_id"] = sweep_dir.name
        summary["gradle_exit_code"] = rc
        summary["continue_past_failures"] = not args.fail_fast
        record = sweep_dir / "sweep.json"
        record.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
        print(format_summary(summary, sweep_dir.name, root, record), flush=True)
    outcome = build_outcome(
        summary, monitor, started=started, ended=ended, gradle_rc=rc, exit_code=exit_code,
        argv=argv, continue_after_failure=bool(args.continue_after_failure), record_dir=sweep_dir)
    if args.resume_from_build:
        outcome["resume"] = {
            "source_report": args.resume_from_build,
            "node": args.resume_from_node or args.run_only_node,
            "mode": "run-only-node" if args.run_only_node else "resume-from-node",
        }
    outcome_path = sweep_dir / OUTCOME_FILE
    outcome_path.write_text(json.dumps(outcome, indent=2) + "\n", encoding="utf-8")
    if not sweep:
        print(format_outcome_line(outcome), flush=True)
    # Last stdout line, always: the path a caller reads instead of grepping logs.
    print(outcome_path, flush=True)
    return exit_code


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__.splitlines()[0],
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Resume (the front door):\n"
            "  Resume from the report's first failed or errored node:\n"
            "    run.py --resume build/validation-reports/<runId>\n"
            "  Resume from a chosen node, or rerun one node only:\n"
            "    run.py --resume <runId> --from-node login.smoke\n"
            "    run.py --resume <runId> --only-node login.smoke\n"
            "  Chain: a resume's last stdout line (its outcome.json) is a valid --resume:\n"
            "    run.py --resume \"$(run.py --resume <runId> | tail -n 1)\"\n"
            "  <report> may be absolute or relative (to the current directory, the\n"
            "  test-graph root, or its build/validation-reports/), a bare runId, a\n"
            "  file inside a report, or an outcome.json. <graph> is read from the\n"
            "  report when omitted.\n\n"
            "Replay examples (explicit form):\n"
            "  Continue a graph from a saved node context:\n"
            "    run.py smoke --resume-from-build build/validation-reports/<runId> "
            "--resume-from-node login.smoke\n"
            "  Run only one node from a saved node context:\n"
            "    run.py smoke --resume-from-build build/validation-reports/<runId> "
            "--run-only-node login.smoke\n\n"
            "Use --resume-from-build with exactly one node selector. "
            "--resume-from-node continues downstream; --run-only-node does not. "
            "Both preserve the source build and write a fresh replay report."
        ),
    )
    parser.add_argument(
        "graphs",
        nargs="*",
        metavar="graph",
        help="Test graph name(s) (also the Gradle task names). "
             "List available graphs with `discover.py`. More than one "
             "runs as a sweep that continues past failures.",
    )
    parser.add_argument(
        "--all",
        dest="run_all",
        action="store_true",
        help="Run every registered test graph sequentially (Gradle "
             "task `validationRunAll`), continuing past failures. "
             "Mutually exclusive with <graph>.",
    )
    policy = parser.add_mutually_exclusive_group()
    policy.add_argument(
        "--continue",
        dest="keep_going",
        action="store_true",
        help="Run as a sweep that keeps going past a failing graph and ends "
             "with an executed/passed/failed/errored/not-run summary. Implied by --all "
             "and by more than one graph; with a single graph it adds the summary.",
    )
    policy.add_argument(
        "--fail-fast",
        dest="fail_fast",
        action="store_true",
        help="In a sweep, stop at the first failing graph. Graphs after it are "
             "reported as not run.",
    )
    parser.add_argument(
        "--resume",
        metavar="REPORT",
        help="Resume a previous run (a fresh run's or a resume's report). With no "
             "node selector, resumes from the report's first failed or errored "
             "node. REPORT may be relative, a bare runId, a file inside the "
             "report, or an outcome.json. <graph> is optional (read from the report).",
    )
    parser.add_argument(
        "--from-node",
        help="With --resume: resume from this node and continue downstream.",
    )
    parser.add_argument(
        "--only-node",
        help="With --resume: run only this node from its saved input context.",
    )
    parser.add_argument(
        "--resume-from-build",
        help="Existing build/validation-reports/<runId> directory whose saved "
             "context/<node-id>.input.json should seed resumed execution. "
             "Requires one <graph> and exactly one of --resume-from-node or "
             "--run-only-node. A relative path is tried against the current "
             "directory, then the test-graph root, then its build/validation-reports/.",
    )
    parser.add_argument(
        "--resume-from-node",
        help="Node id to resume from. The selected node's saved input context "
             "must exist under --resume-from-build/context/.",
    )
    parser.add_argument(
        "--run-only-node",
        help="Node id to run by itself from --resume-from-build. The selected "
             "node's saved input context must exist under "
             "--resume-from-build/context/.",
    )
    parser.add_argument(
        "--continue-after-failure",
        action="store_true",
        help="Within a graph, keep running NODES after one fails (sets "
             f"{CONTINUE_AFTER_FAILURE_ENV}=1 for PlanExecutor). For a graph of "
             "independent scenarios measured together (N of M) or a "
             "deliberately red baseline. Every node still reports its own "
             "status in outcome.json and the run still fails. Not --continue, "
             "which spans GRAPHS.",
    )
    add_test_graph_root_arg(parser)
    args = parser.parse_args(argv)

    graphs: list[str] = []
    for graph in args.graphs:
        if graph not in graphs:
            graphs.append(graph)

    if args.resume is None and (args.from_node or args.only_node):
        parser.error("--from-node and --only-node apply to --resume <report>")
    if args.resume is not None:
        if args.resume_from_build:
            parser.error("pass either --resume or --resume-from-build, not both")
        if args.run_all or len(graphs) > 1 or args.keep_going or args.fail_fast:
            parser.error("--resume applies to one graph; drop --all/--continue/--fail-fast")
        # --resume-from-node / --run-only-node are accepted as synonyms here.
        from_node = args.from_node or args.resume_from_node
        only_node = args.only_node or args.run_only_node
        if from_node and only_node:
            parser.error("pass at most one of --from-node or --only-node")
        root = target_project_root(args.test_graph_root)
        try:
            report = resolve_report_dir(args.resume, root)
        except ReportPathError as exc:
            parser.error(str(exc))
        recorded = report_graph_name(report)
        if not graphs:
            if recorded is None:
                parser.error(f"{report} does not record its graph name; pass <graph>")
            graphs = [recorded]
        elif recorded is not None and recorded != graphs[0]:
            parser.error(f"{report} is a report of graph {recorded!r}, not {graphs[0]!r}")
        if not (from_node or only_node):
            from_node = first_resumable_node(report)
            if from_node is None:
                parser.error(
                    f"{report} has no failed or errored node to resume from; "
                    "pass --from-node or --only-node to choose one")
        selected = from_node or only_node
        if not (report / "context" / f"{selected}.input.json").is_file():
            parser.error(
                f"{report} has no saved input context for {selected!r} "
                f"(context/{selected}.input.json): the run never reached that node")
        args.resume_from_build = str(report)
        args.resume_from_node, args.run_only_node = from_node, only_node
        print(f"resume {graphs[0]}: {'only ' + only_node if only_node else 'from ' + from_node} "
              f"(report {report})", flush=True)

    if args.run_all and graphs:
        parser.error("cannot pass both <graph> and --all — pick one")
    if not args.run_all and not graphs:
        parser.error("either <graph> or --all is required")
    replay_node_count = sum(bool(v) for v in (args.resume_from_node, args.run_only_node))
    replaying = bool(args.resume_from_build or replay_node_count)
    if replaying and (args.run_all or len(graphs) != 1 or args.keep_going or args.fail_fast):
        parser.error("resume options apply to one graph; pass a single <graph> without --all/--continue")
    if args.resume_from_build and replay_node_count != 1:
        parser.error(
            "--resume-from-build requires exactly one of --resume-from-node "
            "or --run-only-node"
        )
    if not args.resume_from_build and replay_node_count:
        parser.error(
            "--resume-from-build (or --resume <report>) is required with "
            "--resume-from-node or --run-only-node")
    if args.resume_from_build and args.resume is None:
        try:
            args.resume_from_build = str(resolve_report_dir(
                args.resume_from_build, target_project_root(args.test_graph_root)))
        except ReportPathError as exc:
            parser.error(str(exc))

    argv_list = list(sys.argv[1:] if argv is None else argv)
    if args.run_all or len(graphs) > 1 or args.keep_going:
        return run_invocation(args, graphs, sweep=True, argv=argv_list)
    if args.fail_fast:
        parser.error("--fail-fast applies to a sweep (--all or more than one graph)")

    # Single graph (or a resume of one): the same ledger, the same outcome.json
    # and the same 0/1/3 exit codes, without the sweep table.
    return run_invocation(args, graphs, sweep=False, argv=argv_list)


if __name__ == "__main__":
    sys.exit(main())
