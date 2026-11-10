#!/usr/bin/env python3
"""Run this repository's behavioural test graphs — one command, one table.

WHAT THIS IS FOR
----------------
`tla-spec-dev` registers three graphs in `test_graph/build.gradle.kts`. This
script is the single front door that runs the ones meant to run here, and says
what it did NOT run and why. Every graph is reported as one of:

    RUN      executed here, verdict read from its own report
    OPT-IN   deliberately not run by default, with the opt-in command printed
    DEAD     registered but known not to work; nobody should expect it

REPORTS, NOT EXIT CODES
-----------------------
A graph's verdict is read from `build/validation-reports/<runId>/summary.json`
written by that run, never inferred from the runner's exit code. A run dir that
predates this invocation is ignored on purpose: `build/validation-reports/`
keeps passing reports from earlier runs, so a graph that never executed looks
green there. No fresh report for a graph means UNDECIDED, which is neither
green nor a failure.

WHY IT MATERIALISES BINDINGS FIRST
----------------------------------
`test_graph/settings.gradle.kts` line 2 declares `includeBuild("build-logic")`,
and `build-logic`, `sdk` and `standard-nodes` are MANAGED PROVIDER BINDINGS:
generated symlinks, gitignored (`test_graph/.gitignore`), with
`test_graph/provider-bindings.json` as the committed durable record. They were
untracked deliberately in 175f5c7c — as tracked symlinks their blobs held one
developer's absolute home path and were dangling in every other checkout.
So a FRESH WORKTREE has no `build-logic`, and a bare `cd test_graph &&
./gradlew specWorkflow` fails at configuration time in ~2s with "Included build
'.../build-logic' does not exist" (SI-12-DF-05 measured exactly this).

The test-graph skill's own runner already materialises the bindings —
`run_gradle()` in `scripts/_common.py` calls `prepare_provider_bindings_or_warn`
before invoking Gradle — so the graphs DO run in a fresh worktree when invoked
through the skill, and only fail when Gradle is invoked directly. This script
materialises the bindings explicitly anyway, and prints the result, so the step
is visible rather than a side effect somebody has to know about.

THIS SCRIPT NEVER REFUSES. It always exits 0. It is a reporting front door, not
a gate; a red or undecided graph is printed, not turned into a stop.

Usage:
    python3 test_graph/run-graphs.py            # materialise, run the RUN set, report
    python3 test_graph/run-graphs.py --list     # classification only; run nothing
    python3 test_graph/run-graphs.py --only cliWorkflow [--only ...]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

TEST_GRAPH_ROOT = Path(__file__).resolve().parent
REPO_ROOT = TEST_GRAPH_ROOT.parent

# ---------------------------------------------------------------------------
# Classification. Every graph registered in build.gradle.kts must appear in
# exactly one of these three, or this script says so and stops classifying —
# an unclassified graph is the failure mode this file exists to remove.
# ---------------------------------------------------------------------------
RUN: dict[str, str] = {
    "specWorkflow": (
        "the tla-spec-dev workflow end to end (scaffold, open, complete, "
        "spec-unit, close) against a disposable git repository, plus the "
        "reference-adapter import check"
    ),
    "cliWorkflow": "the CLI installs from this checkout and answers --help",
    "effectProviderExamples": "the committed effect-provider examples execute",
}

# Graphs deliberately not run by default.
#
# SI-16 MADE THIS NON-EMPTY, and the sentence it replaces is retired. It used
# to read "none of its three graphs reaches a third-party service", which was
# true of the three. Absorbing skt added two more, and they do: the skt nodes
# run on a PINNED interpreter matrix (3.11 and 3.13) that
# `test_graph/support/skt_fixture.py` provisions with `uv python find` and,
# failing that, `uv python install` -- a download. `skt.wrapper-installed`
# declares `side_effects("fs:tmp", "net:external")` for exactly that reason.
#
# They are OPT-IN rather than RUN so the default front door stays offline and
# cannot hang on a network fetch; they are NOT dead, and they are not silently
# dropped -- the reason below is printed on every run, which is what keeps
# "did not run" distinguishable from "is not run here" (SI-13's rule).
OPT_IN: dict[str, str] = {
    "sktSurface": (
        "provisions a pinned CPython 3.11/3.13 matrix through uv "
        "(net:external) to execute install-skt.sh, the wrapper it writes, the "
        "two shipped hooks and the ticket round trip; run it with "
        "`python3 test_graph/run-graphs.py --only sktSurface` once uv can "
        "reach its interpreter downloads"
    ),
    "sktHooks": (
        "the hook-change subset of sktSurface (wrapper + cached-cost + hook "
        "contract); same pinned-interpreter provisioning, same opt-in "
        "command with --only sktHooks"
    ),
}

# Graphs registered but known not to work. Empty; see --list output.
DEAD: dict[str, str] = {}

_TESTGRAPH_RE = re.compile(r'(?<![\w.])testGraph\("([^"]+)"\)')


def registered_graphs() -> list[str]:
    build_file = TEST_GRAPH_ROOT / "build.gradle.kts"
    text = build_file.read_text(encoding="utf-8")
    names: list[str] = []
    for name in _TESTGRAPH_RE.findall(text):
        if name not in names:
            names.append(name)
    return names


def skill_runner() -> Path | None:
    """The test-graph skill's runner from the INSTALLED tla-spec-dev plugin.

    The graphs run against the test-graph skill installed in this checkout's
    Skill Manager home (`<home>/plugins/tla-spec-dev/skills/test-graph`), never
    the in-repo `skills/test-graph` source. `provider-bindings.json` declares
    only the `skill-root` candidate, so whichever runner executes decides the
    SDK the links point at — which is why the in-repo copy is deliberately NOT
    a candidate here: it would silently bind the graphs back to the working
    tree. An edit to `skills/test-graph` reaches the graphs after
    `skt sync tla-spec-dev` pulls it into the home.
    """
    rel = Path("plugins") / "tla-spec-dev" / "skills" / "test-graph" / "scripts" / "run.py"
    candidates = []
    home = os.environ.get("SKILL_MANAGER_HOME")
    if home:
        candidates.append(Path(home) / rel)
    candidates.append(REPO_ROOT / ".skill-manager" / rel)
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


def prepare_bindings() -> str:
    script = None
    runner = skill_runner()
    if runner is not None:
        script = runner.parent / "prepare-bindings.py"
    if script is None or not script.is_file():
        return "no prepare-bindings.py found next to the runner; skipped"
    proc = subprocess.run(
        [sys.executable, str(script), "--test-graph-root", str(TEST_GRAPH_ROOT)],
        capture_output=True,
        text=True,
    )
    links = {
        name: (os.readlink(TEST_GRAPH_ROOT / name)
               if (TEST_GRAPH_ROOT / name).is_symlink() else "ABSENT")
        for name in ("build-logic", "sdk", "standard-nodes")
    }
    detail = ", ".join(f"{k} -> {v}" for k, v in sorted(links.items()))
    if proc.returncode != 0:
        return f"prepare-bindings exited {proc.returncode}: {proc.stderr.strip()[:300]} | {detail}"
    return detail


def fresh_report(graph: str, started_at: float) -> tuple[str, str]:
    """(verdict, evidence path) read from a report written by THIS invocation."""
    reports = TEST_GRAPH_ROOT / "build" / "validation-reports"
    if not reports.is_dir():
        return "UNDECIDED", "no build/validation-reports directory"
    best: tuple[float, Path] | None = None
    for run_dir in reports.iterdir():
        summary = run_dir / "summary.json"
        if not summary.is_file():
            continue
        if summary.stat().st_mtime < started_at:
            continue  # a report from an earlier run is not evidence about this one
        try:
            data = json.loads(summary.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if (data.get("execution") or {}).get("graphName") != graph:
            continue
        stamp = summary.stat().st_mtime
        if best is None or stamp > best[0]:
            best = (stamp, summary)
    if best is None:
        return "UNDECIDED", "no report written by this invocation"
    data = json.loads(best[1].read_text(encoding="utf-8"))
    status = str(data.get("status", "?"))
    complete = bool((data.get("execution") or {}).get("complete"))
    verdict = "PASSED" if (status == "passed" and complete) else status.upper()
    if status == "passed" and not complete:
        verdict = "UNDECIDED"  # a partial run is not a pass
    return verdict, str(best[1])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--list", action="store_true", help="classification only; run nothing")
    parser.add_argument("--only", action="append", default=[], metavar="GRAPH",
                        help="run just this graph (repeatable). May name an OPT-IN graph: "
                             "naming it IS the opt-in, which is what the OPT_IN entries "
                             "below tell you to do. Some provision interpreters over the "
                             "network, so they stay out of the default set.")
    args = parser.parse_args()

    registered = registered_graphs()
    classified = set(RUN) | set(OPT_IN) | set(DEAD)
    unclassified = [g for g in registered if g not in classified]
    stale = sorted(classified - set(registered))

    print("== tla-spec-dev test graphs ==")
    print(f"registered in test_graph/build.gradle.kts: {len(registered)}")
    if not registered:
        print("  NOTHING REGISTERED — this script found no testGraph(...) in the build "
              "file, so the classification below describes nothing. Treat as UNDECIDED.")
    for graph in registered:
        if graph in RUN:
            print(f"  RUN      {graph:26} {RUN[graph]}")
        elif graph in OPT_IN:
            print(f"  OPT-IN   {graph:26} {OPT_IN[graph]}")
        elif graph in DEAD:
            print(f"  DEAD     {graph:26} {DEAD[graph]}")
    for graph in unclassified:
        print(f"  UNCLASSIFIED {graph:22} not named in this file — nobody has said "
              f"whether it should run. Report it; do not assume either answer.")
    for graph in stale:
        print(f"  STALE    {graph:26} classified here but no longer registered")
    if not OPT_IN:
        print("  (no opt-in graphs here: none of these reaches a third-party service)")
    if not DEAD:
        print("  (no dead graphs here)")

    if args.list:
        return 0

    started_at = time.time() - 1
    print("\n== managed provider bindings ==")
    print("  " + prepare_bindings())

    runner = skill_runner()
    if runner is None:
        print("\nUNDECIDED: no test-graph runner found (looked in skills/test-graph/, "
              "$SKILL_MANAGER_HOME, .skill-manager/). Nothing was run; no graph is green.")
        return 0
    print(f"  runner: {runner}")

    # An explicit --only may name an OPT-IN graph. It used to be filtered to RUN,
    # which made every printed opt-in command ("run it with --only sktSurface") a
    # no-op that exited 0 having run nothing -- a silent skip, inside the script
    # written to make silent skips impossible (SI-13). Only a name that is
    # registered nowhere is dropped now, and that is still announced.
    selectable = set(RUN) | set(OPT_IN)
    wanted = args.only or list(RUN)
    unknown = [g for g in wanted if g not in selectable]
    if unknown:
        print(f"\nnot a registered graph, skipping: {', '.join(unknown)}")
        wanted = [g for g in wanted if g in selectable]
    opted_in = [g for g in wanted if g in OPT_IN]
    if opted_in:
        print(f"\nopted in to {', '.join(opted_in)} -- these are OPT-IN because they "
              f"reach the network; you asked for them explicitly.")

    results: list[tuple[str, str, int, str]] = []
    for graph in wanted:
        print(f"\n---- {graph} ----", flush=True)
        proc = subprocess.run([sys.executable, str(runner), graph], cwd=str(REPO_ROOT))
        verdict, evidence = fresh_report(graph, started_at)
        results.append((graph, verdict, proc.returncode, evidence))

    print("\n== verdicts (read from each run's own summary.json, not from exit codes) ==")
    for graph, verdict, code, evidence in results:
        print(f"  {verdict:9} {graph:26} runner_exit={code}  {evidence}")
    # ONLY the opt-in graphs this invocation did NOT run. Printing all of them
    # unconditionally meant an opt-in graph that DID run appeared twice -- once
    # with its real verdict and once as NOT RUN. Observed 2026-09-21:
    # `--only sktHooks --only sktSurface` reported sktSurface as ERRORED and
    # then again as NOT RUN in the same table. A red graph that also prints
    # NOT RUN reads as skipped, which is the did-not-run versus is-not-run-here
    # confusion this script exists to prevent (SI-13).
    ran = {graph for graph, _, _, _ in results}
    for graph, reason in OPT_IN.items():
        if graph in ran:
            continue
        print(f"  {'NOT RUN':9} {graph:26} opt-in: {reason}")
    for graph, reason in DEAD.items():
        print(f"  {'DEAD':9} {graph:26} {reason}")
    print("\nThis command always exits 0. A red or undecided graph is a report, "
          "not a refusal.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
