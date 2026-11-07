"""Issue #185 (+ #168, BS-10-DF-01): every run.py invocation writes outcome.json.

Callers learned a run's outcome by grepping logs, and a timeout or a dead runner
read as a red. ``run.py`` now always writes ``<record>/outcome.json`` and prints
its path as the last stdout line, with per-graph and per-node status
(``passed | failed | errored | not_run``), cause, duration, timeout bound, host
load average at start and end, and report directory; exit codes are 0/1/3.

Two layers:

* unit tests over ``collect_nodes`` / ``build_outcome``, fed run directories;
* ``RealSdkFixtureTest``: the issue's own acceptance, under the REAL test-graph
  SDK (build-logic + Python SDK copied from ``project_sdk_sources``) and real
  Gradle. One graph has a node asserting red, a node that SIGKILLs itself and a
  node that outlives its timeout; another graph has a node whose describe fails
  on every retry (``NodeDescribeErroredException``). Set
  ``TEST_GRAPH_SKIP_GRADLE_FIXTURES=1`` to skip that layer.
"""
from __future__ import annotations

import contextlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
SKILL_ROOT = SCRIPTS_DIR.parent
SDK = SKILL_ROOT / "project_sdk_sources"
sys.path.insert(0, str(SCRIPTS_DIR))

import run  # noqa: E402
import sweep  # noqa: E402


def write_envelope(run_dir: Path, node: str, status: str, **extra) -> None:
    (run_dir / "envelope").mkdir(parents=True, exist_ok=True)
    envelope = {"nodeId": node, "status": status,
                "executorStartedAt": "2026-11-07T10:00:00.123456789Z",
                "executorEndedAt": "2026-11-07T10:00:04.623456Z", "spawnExitCode": 0}
    envelope.update(extra)
    (run_dir / "envelope" / f"{node}.json").write_text(json.dumps(envelope))


class CollectNodesTest(unittest.TestCase):
    def run_dir(self) -> Path:
        holder = tempfile.TemporaryDirectory()
        self.addCleanup(holder.cleanup)
        d = Path(holder.name) / "20990101-000000"
        d.mkdir()
        return d

    def test_statuses_causes_durations_and_timeout_bound(self) -> None:
        d = self.run_dir()
        (d / "execution-scope.json").write_text(json.dumps(
            {"expectedNodeIds": ["n.red", "n.killed", "n.slow", "n.skipped", "n.inflight", "n.never"]}))
        write_envelope(d, "n.red", "failed", failureMessage="expected 1 but was 2", spawnExitCode=1)
        write_envelope(d, "n.killed", "errored", spawnExitCode=137,
                       failureMessage="node exited 137 without writing --result-out")
        write_envelope(d, "n.slow", "errored", spawnExitCode=-1,
                       failureMessage="node timed out after 3s; executor force-killed the subprocess")
        write_envelope(d, "n.skipped", "skipped", spawnExitCode=-1)
        (d / "context").mkdir()
        (d / "context" / "n.inflight.input.json").write_text("[]")

        rows = {r["node"]: r for r in run.collect_nodes(str(d), None)}
        self.assertEqual(["n.red", "n.killed", "n.slow", "n.skipped", "n.inflight", "n.never"], list(rows))
        self.assertEqual(
            {"n.red": ("failed", "assertion"), "n.killed": ("errored", "signal"),
             "n.slow": ("errored", "timeout"), "n.skipped": ("not_run", "skipped"),
             "n.inflight": ("errored", "runner_died"), "n.never": ("not_run", "skipped")},
            {n: (r["status"], r["cause"]) for n, r in rows.items()})
        self.assertEqual(4.5, rows["n.red"]["duration_seconds"])
        self.assertEqual((3.0, "3s"), (rows["n.slow"]["timeout_bound_seconds"], rows["n.slow"]["timeout_bound"]))
        self.assertIsNone(rows["n.skipped"]["duration_seconds"])
        self.assertEqual(str(d), rows["n.red"]["report_dir"])

    def test_load_average_is_looked_up_at_node_start_and_end(self) -> None:
        d = self.run_dir()
        write_envelope(d, "n.ok", "passed")
        monitor = run.InvocationMonitor(d / "ledger.jsonl")
        start = run._parse_instant("2026-11-07T10:00:00.123456Z")
        monitor.samples = [(start - 1, [1.0, 1.0, 1.0]), (start + 2, [7.0, 2.0, 1.0]),
                           (start + 9, [9.0, 3.0, 1.0])]
        row = run.collect_nodes(str(d), monitor)[0]
        self.assertEqual(([1.0, 1.0, 1.0], [7.0, 2.0, 1.0]), (row["load_avg_start"], row["load_avg_end"]))

    def test_describe_errored_graph_is_errored_with_its_own_cause(self) -> None:
        records = [{"event": "scheduled", "task": "g", "graph": True},
                   {"event": "started", "task": "g", "graph": True},
                   {"event": "finished", "task": "g", "graph": True, "outcome": "failed",
                    "runDirs": [], "seconds": 2.0, "failure": "Execution failed for task ':g'."}]
        summary = run.summarize_sweep(["g"], records, run_all=False)
        self.assertEqual("errored", summary["results"][0]["status"])
        self.assertIn("NodeDescribeErroredException", summary["results"][0]["reason"])
        self.assertEqual(run.SWEEP_EXIT_ERRORED, run.sweep_exit_code(1, summary))
        outcome = run.build_outcome(summary, None, started=0.0, ended=2.0, gradle_rc=1, exit_code=3,
                                    argv=["g"], continue_after_failure=False, record_dir=Path("/r"))
        self.assertEqual(("errored", "no_run_dir"), (outcome["graphs"][0]["status"], outcome["graphs"][0]["cause"]))

    def test_exit_codes_never_leave_0_1_3(self) -> None:
        unknown = run.summarize_sweep([], [], run_all=True)
        for rc in (0, 1, 2, 130, 137):
            self.assertIn(run.sweep_exit_code(rc, unknown), (0, 1, 3))
        green = run.summarize_sweep(["a"], [{"event": "scheduled", "task": "a", "graph": True},
                                            {"event": "finished", "task": "a", "outcome": "passed"}], False)
        self.assertEqual(1, run.sweep_exit_code(130, green))


class SweepPyReadsOutcomeTest(unittest.TestCase):
    def test_run_one_takes_status_and_run_id_from_outcome_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            run_dir = repo / sweep.REPORTS / "20990101-000009"
            run_dir.mkdir(parents=True)
            outcome = repo / "outcome.json"
            outcome.write_text(json.dumps({"status": "errored", "exit_code": 3, "graphs": [
                {"graph": "g", "status": "errored", "report_dir": str(run_dir), "nodes": []}]}))

            def fake_call(cmd, cwd, stdout, stderr):
                stdout.write(f"some log mentioning validation-reports/stale-id\n{outcome}\n")
                stdout.flush()
                return 3

            log_dir = repo / "logs"
            log_dir.mkdir()
            with patch.object(sweep.subprocess, "call", side_effect=fake_call):
                result = sweep.run_one(repo, "g", log_dir, None, None)
            self.assertEqual(("20990101-000009", "errored"), (result["run_id"], result["outcome_status"]))
            self.assertEqual(str(outcome), result["outcome"])


# ---------------------------------------------------------------- real SDK

NODE_HEADER = '''\
# /// script
# requires-python = ">=3.10"
# dependencies = ["testgraphsdk"]
#
# [tool.uv.sources]
# testgraphsdk = { path = "../sdk/python", editable = true }
# ///
'''

RED_NODE = NODE_HEADER + '''
from testgraphsdk import NodeResult, NodeSpec, node

SPEC = NodeSpec("fixture.red").kind("assertion").timeout("60s")


@node(SPEC)
def main(ctx):
    return NodeResult.fail(ctx.node_id, "expected 1 but was 2").assertion("one_is_two", False)


if __name__ == "__main__":
    main()
'''

KILLED_NODE = NODE_HEADER + '''
import os
import signal

from testgraphsdk import NodeResult, NodeSpec, node

SPEC = NodeSpec("fixture.killed").kind("assertion").timeout("60s")


@node(SPEC)
def main(ctx):
    # SIGKILL the node process itself: it never delivers a verdict.
    os.kill(os.getpid(), signal.SIGKILL)
    return NodeResult.pass_(ctx.node_id)


if __name__ == "__main__":
    main()
'''

SLOW_NODE = NODE_HEADER + '''
import time

from testgraphsdk import NodeResult, NodeSpec, node

SPEC = NodeSpec("fixture.slow").kind("assertion").timeout("3s")


@node(SPEC)
def main(ctx):
    time.sleep(120)
    return NodeResult.pass_(ctx.node_id)


if __name__ == "__main__":
    main()
'''

BROKEN_DESCRIBE_NODE = NODE_HEADER + '''
import sys

if any(arg.startswith("--describe-out") for arg in sys.argv):
    sys.stderr.write("describe cannot start: interpreter environment is broken\\n")
    sys.exit(3)
'''

FIXTURE_BUILD = '''\
plugins {
    id("com.hayden.testgraphsdk.graph")
}

// No sourcesDir(): only each graph's explicit nodes are described, so the
// broken-describe node breaks its own graph and no other.
validationGraph {
    testGraph("threeWays") {
        node("nodes/red.py")
        node("nodes/killed.py")
        node("nodes/slow.py")
    }
    testGraph("onlySlow") {
        node("nodes/slow.py")
    }
    testGraph("describeErrored") {
        node("nodes/broken_describe.py")
    }
}
'''

FIXTURE_SETTINGS = '''\
pluginManagement {
    includeBuild("build-logic")
    repositories {
        gradlePluginPortal()
        mavenCentral()
    }
}
dependencyResolutionManagement {
    repositories { mavenCentral() }
}
rootProject.name = "outcome-json-fixture"
'''


def _real_sdk_unavailable() -> str | None:
    if os.environ.get("TEST_GRAPH_SKIP_GRADLE_FIXTURES"):
        return "TEST_GRAPH_SKIP_GRADLE_FIXTURES is set"
    for tool in ("java", "uv"):
        if shutil.which(tool) is None:
            return f"no {tool} on PATH"
    if not (SDK / "gradlew").is_file() or not (SDK / "build-logic").is_dir():
        return "no Gradle wrapper or build-logic in project_sdk_sources"
    return None


@unittest.skipIf(_real_sdk_unavailable(), _real_sdk_unavailable() or "")
class RealSdkFixtureTest(unittest.TestCase):
    """The issue's acceptance: red, SIGKILLed and timed-out nodes, real SDK."""

    @classmethod
    def setUpClass(cls) -> None:
        cls._holder = tempfile.TemporaryDirectory()
        cls.root = Path(cls._holder.name) / "test_graph"
        cls.root.mkdir()
        shutil.copy2(SDK / "gradlew", cls.root / "gradlew")
        shutil.copytree(SDK / "gradle", cls.root / "gradle")
        shutil.copytree(SDK / "build-logic", cls.root / "build-logic",
                        ignore=shutil.ignore_patterns("build", ".gradle", ".kotlin"))
        shutil.copytree(SDK / "sdk" / "python", cls.root / "sdk" / "python",
                        ignore=shutil.ignore_patterns(".venv", "__pycache__", "*.egg-info"))
        (cls.root / "settings.gradle.kts").write_text(FIXTURE_SETTINGS)
        (cls.root / "build.gradle.kts").write_text(FIXTURE_BUILD)
        nodes = cls.root / "nodes"
        nodes.mkdir()
        for name, text in (("red.py", RED_NODE), ("killed.py", KILLED_NODE),
                           ("slow.py", SLOW_NODE), ("broken_describe.py", BROKEN_DESCRIBE_NODE)):
            (nodes / name).write_text(text)

    @classmethod
    def tearDownClass(cls) -> None:
        cls._holder.cleanup()

    def invoke(self, *argv: str) -> tuple[int, dict, str]:
        proc = subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "run.py"), *argv, "--test-graph-root", str(self.root)],
            capture_output=True, text=True, timeout=1500,
        )
        transcript = proc.stdout[-4000:] + proc.stderr[-4000:]
        lines = proc.stdout.strip().splitlines()
        self.assertTrue(lines, transcript)
        last = Path(lines[-1])
        self.assertEqual("outcome.json", last.name, "last stdout line is not outcome.json\n" + transcript)
        self.assertTrue(last.is_file(), transcript)
        return proc.returncode, json.loads(last.read_text()), transcript

    def nodes(self, outcome: dict) -> dict[str, dict]:
        return {n["node"]: n for g in outcome["graphs"] for n in g["nodes"]}

    def test_red_killed_and_timed_out_nodes_get_distinct_outcomes(self) -> None:
        rc, outcome, transcript = self.invoke("threeWays", "--continue-after-failure")
        nodes = self.nodes(outcome)
        self.assertEqual(
            {"fixture.red": ("failed", "assertion"),
             "fixture.killed": ("errored", "signal"),
             "fixture.slow": ("errored", "timeout")},
            {n: (r["status"], r["cause"]) for n, r in nodes.items()}, transcript)
        # Three nodes, three distinct (status, cause) outcomes.
        self.assertEqual(3, len({(r["status"], r["cause"]) for r in nodes.values()}))
        self.assertEqual(3.0, nodes["fixture.slow"]["timeout_bound_seconds"])
        for row in nodes.values():
            self.assertIsInstance(row["duration_seconds"], float)
            self.assertIsNotNone(row["load_avg_start"], row)
            self.assertIsNotNone(row["load_avg_end"], row)
            self.assertTrue(Path(row["report_dir"]).is_dir())
        graph = outcome["graphs"][0]
        self.assertEqual(("threeWays", "failed"), (graph["graph"], graph["status"]))
        self.assertIsNotNone(graph["load_avg_start"])
        self.assertIsNotNone(graph["load_avg_end"])
        self.assertTrue(Path(graph["report_dir"]).is_dir())
        self.assertTrue(outcome["continue_after_failure"])
        # A failure outranks an error: exit 1, recorded in the outcome too.
        self.assertEqual((1, 1), (rc, outcome["exit_code"]), transcript)

    def test_without_continue_after_failure_later_nodes_are_not_run(self) -> None:
        rc, outcome, transcript = self.invoke("threeWays")
        self.assertEqual(
            {"fixture.red": "failed", "fixture.killed": "not_run", "fixture.slow": "not_run"},
            {n: r["status"] for n, r in self.nodes(outcome).items()}, transcript)
        self.assertEqual(1, rc)

    def test_a_timeout_alone_is_errored_and_exits_3(self) -> None:
        rc, outcome, transcript = self.invoke("onlySlow")
        self.assertEqual(("errored", "node_errored"),
                         (outcome["graphs"][0]["status"], outcome["graphs"][0]["cause"]), transcript)
        self.assertEqual((3, 3), (rc, outcome["exit_code"]), transcript)

    def test_describe_errored_graph_is_errored_not_not_run(self) -> None:
        rc, outcome, transcript = self.invoke("describeErrored")
        graph = outcome["graphs"][0]
        self.assertEqual(("errored", "no_run_dir"), (graph["status"], graph["cause"]), transcript)
        self.assertEqual([], graph["nodes"])
        self.assertEqual((3, 3), (rc, outcome["exit_code"]), transcript)
        self.assertIn("errored: describe for broken_describe.py failed", transcript)


if __name__ == "__main__":
    unittest.main()
