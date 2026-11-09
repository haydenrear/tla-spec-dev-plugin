#!/usr/bin/env python3
"""Drive every registered graph ONE AT A TIME, with per-graph resumption.

WHY THIS EXISTS -- DEF-011, and the owner's instruction of 2026-08-24.

UPDATE (OHV-7, DEF-OUN-023): `run.py --all` and `run.py A B C` no longer stop
at the first red graph; they run Gradle with `--continue` and end with a summary
counted from that invocation's own ledger. What remains unique here is per-graph
resumption across a sweep and the CI selector's graph set. The paragraph below
describes run.py before that change.

`run.py --all` hands the whole set to Gradle as one task chain, and Gradle stops
at the first failing task. So a red graph at position 1 yields "stopped at 1",
which is indistinguishable from "only 1 graph exists". Measured 2026-08-21: one
lost teardown race in `smoke` meant 1 of 24 executed and 23 never ran.

`run.py` ALSO REFUSES to combine `--all` with resumption:

    if args.run_all and (args.resume_from_build or replay_node_count):
        parser.error("resume options apply to one graph; pass <graph> instead of --all")

Resumption is per-graph. So "sweep everything" and "resume from the failing
node" cannot both be asked of `--all`, and the owner's instruction -- never
restart from the beginning -- requires driving the graphs individually.

That is this script. One graph at a time; a red graph does NOT stop the sweep;
every graph's outcome is recorded whether it passed or failed; and a graph that
failed can be resumed from its own failing node without re-running the ones
before it.

OUTCOME (issue #185). Each graph's run.py prints its outcome.json path as the
last log line; the run directory and the passed/failed/errored status are read
from it, and the log is grepped only when an older run.py wrote none.

FAILED vs ERRORED (issue #175). A non-zero exit is not one thing. A graph is
`failed` only when its own summary.json says a node completed with a red
assertion; any other non-zero exit -- no report at all because the Gradle
process or daemon died, or a report saying a node never delivered a verdict --
is `errored`. They need opposite responses (investigate the code vs retry / fix
the environment), and `--retry-failed-from` treats them differently: a failed
graph resumes from its first failing node, an errored graph RESTARTS, because
the node it stopped at never failed and has nothing to resume from.

WHAT IT DOES NOT DO: decide anything. It records. `graphs_executed` is a count
of graphs whose task RAN, red or green -- `graphs_passed` is the separate
question, and both are written to the report so neither can be inferred from
the other.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
RUN_PY = HERE / "run.py"


def registered_graphs(repo_root: Path, scope: str) -> list[str]:
    """Ask the CI selector, so the sweep and CI cannot disagree about the set."""
    sel = repo_root / ".github/scripts/select-graph-set.py"
    out = subprocess.run(
        ["uv", "run", "--with", "pyyaml", "python3", str(sel), "--scope", scope, "--print"],
        capture_output=True, text=True, cwd=repo_root,
    )
    if out.returncode != 0:
        raise SystemExit(f"selector failed: {out.stderr[-800:]}")
    for line in out.stdout.splitlines():
        if line.startswith("- selected for this run"):
            return [t.strip(" `") for t in line.split("—", 1)[1].split(",")]
    raise SystemExit("selector printed no selection line")


REPORTS = Path("test_graph/build/validation-reports")


def report_status(repo_root: Path, run_id: str | None) -> str | None:
    """The graph's own verdict from its summary.json, or None if it wrote none."""
    if not run_id:
        return None
    try:
        status = json.loads((repo_root / REPORTS / run_id / "summary.json").read_text()).get("status")
    except Exception:
        return None
    return status if isinstance(status, str) else None


def graph_status(exit_code: int, verdict: str | None) -> str:
    """passed | failed | errored -- `failed` needs the graph's own red verdict."""
    if exit_code == 0:
        return "passed"
    return "failed" if verdict == "failed" else "errored"


def run_one(repo_root: Path, graph: str, log_dir: Path,
            resume_build: str | None, resume_node: str | None) -> dict:
    cmd = [sys.executable, str(RUN_PY), graph]
    if resume_build and resume_node:
        cmd += ["--resume-from-build", resume_build, "--resume-from-node", resume_node]
    log = log_dir / f"{graph}.log"
    started = time.time()
    with log.open("w") as fh:
        rc = subprocess.call(cmd, cwd=repo_root, stdout=fh, stderr=subprocess.STDOUT)
    text = log.read_text(errors="replace")
    outcome_path, outcome = read_outcome(text)
    run_id = None
    if outcome is not None:
        # #185: run.py's last stdout line names outcome.json; read the run
        # directory from it instead of grepping the log.
        for g in outcome.get("graphs") or []:
            if g.get("graph") == graph and g.get("report_dir"):
                run_id = Path(g["report_dir"]).name
    else:
        for line in text.splitlines():
            if "validation-reports/" in line:
                frag = line.split("validation-reports/", 1)[1]
                run_id = frag.split()[0].split("/")[0].strip()
    return {
        "graph": graph, "exit_code": rc, "passed": rc == 0,
        "run_id": run_id, "seconds": round(time.time() - started, 1),
        "log": str(log.relative_to(repo_root)),
        "outcome": outcome_path,
        "outcome_status": outcome.get("status") if outcome else None,
        "resumed_from": {"build": resume_build, "node": resume_node} if resume_node else None,
    }


def read_outcome(log_text: str) -> tuple[str | None, dict | None]:
    """run.py prints its outcome.json path as the last stdout line (#185)."""
    lines = [line.strip() for line in log_text.splitlines() if line.strip()]
    if not lines or not lines[-1].endswith("outcome.json"):
        return None, None
    try:
        doc = json.loads(Path(lines[-1]).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return lines[-1], None
    return lines[-1], doc if isinstance(doc, dict) else None


def node_outcomes(repo_root: Path, run_id: str | None) -> tuple[list[str], list[str], list[str]]:
    """Split nodes that FAILED from nodes that ERRORED and nodes that never RAN.

    `errored` (#175) is a node that never delivered a verdict -- it crashed, was
    killed, or timed out. It is not a red assertion, and is not resumed from.

    Caught by its own selftest on 2026-08-24: the first version returned every
    node whose status was not "passed", which lumps `skipped` in with `failed`.
    On `artifact-dag` that reported three failing nodes where there is ONE --
    `uninstall.prunes.the.subgraph` failed and `home.fixpoint.law` /
    `home.membership.law` are downstream, `spawnExitCode: -1`, zero assertions.
    Reporting a node that never executed as a node that failed would have told
    HIS-6 the cross-cutting laws were broken.

    It also matters for resumption: you resume from the node that FAILED. A
    skipped node has no saved input context to resume from.
    """
    if not run_id:
        return [], [], []
    env = repo_root / REPORTS / run_id / "envelope"
    if not env.is_dir():
        return [], [], []
    failed, errored, skipped = [], [], []
    for f in sorted(env.glob("*.json")):
        try:
            e = json.loads(f.read_text())
        except Exception:
            continue
        status = e.get("status")
        node = e.get("nodeId") or f.stem
        if status == "passed":
            continue
        if status == "skipped":
            skipped.append(node)
        elif status == "errored":
            errored.append(node)
        else:
            failed.append(node)
    return failed, errored, skipped


def plan_retry(repo_root: Path, prev: dict) -> tuple[list[str], dict[str, tuple[str, str]]]:
    """Graphs to re-run from a previous sweep.json, and which resume from a node.

    Only a FAILED graph resumes, from its first failing node. An ERRORED graph
    restarts: the node it stopped at never failed, so there is nothing to
    resume from. Records written before #175 carry no ``status``; it is derived
    the same way a fresh run derives it.
    """
    graphs: list[str] = []
    resume_plan: dict[str, tuple[str, str]] = {}
    for r in prev["results"]:
        if r["passed"]:
            continue
        graphs.append(r["graph"])
        status = r.get("status") or graph_status(
            r.get("exit_code", 1), report_status(repo_root, r.get("run_id")))
        if status != "failed":
            continue
        nodes, _, _ = node_outcomes(repo_root, r.get("run_id"))
        if nodes and r.get("run_id"):
            resume_plan[r["graph"]] = (f"{REPORTS}/{r['run_id']}", nodes[0])
    return graphs, resume_plan


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--scope", default="full", choices=["core", "full"])
    ap.add_argument("--out", default="results/epic-home-integrity-sync/sweep")
    ap.add_argument("--only", nargs="*", help="run just these graphs")
    ap.add_argument("--start-at", help="skip graphs before this one")
    ap.add_argument("--retry-failed-from", help="a previous sweep.json; re-run its non-green graphs: a failed graph resumes from its first failing node, an errored graph restarts")
    args = ap.parse_args()

    repo_root = Path(subprocess.check_output(
        ["git", "rev-parse", "--show-toplevel"], text=True).strip())
    out_dir = repo_root / args.out
    out_dir.mkdir(parents=True, exist_ok=True)
    log_dir = out_dir / "logs"
    log_dir.mkdir(exist_ok=True)

    resume_plan: dict[str, tuple[str, str]] = {}
    if args.retry_failed_from:
        prev = json.loads((repo_root / args.retry_failed_from).read_text())
        graphs, resume_plan = plan_retry(repo_root, prev)
        print(f"retrying {len(graphs)} non-green graph(s); {len(resume_plan)} resumable from a "
              f"failing node, {len(graphs) - len(resume_plan)} restarted")
    else:
        graphs = args.only or registered_graphs(repo_root, args.scope)
        if args.start_at:
            graphs = graphs[graphs.index(args.start_at):]

    print(f"sweep: {len(graphs)} graph(s), one at a time, a red one does NOT stop the sweep")
    results = []
    for i, g in enumerate(graphs, 1):
        rb, rn = resume_plan.get(g, (None, None))
        note = f"  (resuming from {rn})" if rn else ""
        print(f"[{i}/{len(graphs)}] {g}{note} ...", flush=True)
        r = run_one(repo_root, g, log_dir, rb, rn)
        r["failing_nodes"], r["errored_nodes"], r["skipped_nodes"] = node_outcomes(
            repo_root, r.get("run_id"))
        r["status"] = r.get("outcome_status") if r.get("outcome_status") in (
            "passed", "failed", "errored") else graph_status(
            r["exit_code"], report_status(repo_root, r.get("run_id")))
        results.append(r)
        mark = {"passed": "PASS", "failed": "FAIL", "errored": "ERROR"}[r["status"]]
        if not r["passed"]:
            mark += f" rc={r['exit_code']}"
        nodes = f"  failed: {', '.join(r['failing_nodes'])}" if r["failing_nodes"] else ""
        nodes += f"  errored: {', '.join(r['errored_nodes'])}" if r["errored_nodes"] else ""
        skips = f"  (skipped downstream: {len(r['skipped_nodes'])})" if r["skipped_nodes"] else ""
        print(f"      {mark}  {r['seconds']}s  run={r['run_id']}{nodes}{skips}", flush=True)
        (out_dir / "sweep.json").write_text(json.dumps({
            "graphs_selected": len(graphs),
            "graphs_executed": len(results),
            "graphs_passed": sum(1 for x in results if x["passed"]),
            "graphs_failed": sum(1 for x in results if x["status"] == "failed"),
            "graphs_errored": sum(1 for x in results if x["status"] == "errored"),
            "results": results,
        }, indent=2) + "\n")

    ex, ps = len(results), sum(1 for r in results if r["passed"])
    fl = sum(1 for r in results if r["status"] == "failed")
    print(f"\ngraphs_executed={ex}  graphs_passed={ps}  graphs_failed={fl}  graphs_errored={ex - ps - fl}")
    for r in results:
        if not r["passed"]:
            sk = f"  [+{len(r['skipped_nodes'])} skipped downstream]" if r["skipped_nodes"] else ""
            nodes = r["failing_nodes"] if r["status"] == "failed" else r["errored_nodes"]
            label = "FAILED " if r["status"] == "failed" else "ERRORED"
            print(f"  {label} {r['graph']}: {', '.join(nodes) or 'no node envelope'}{sk}")
    if ex - ps - fl:
        print("  ERRORED = the run did not complete: retry it or fix the environment, "
              "do not investigate the code.")
    print(f"\nwrote {out_dir / 'sweep.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
