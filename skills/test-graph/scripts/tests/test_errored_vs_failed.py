"""Issue #175: a dead runner is ERRORED, a red node is FAILED, and they never merge.

They need opposite responses -- retry / fix the environment versus investigate
the code -- so they get distinct statuses, distinct ``graphs_*`` counts and
distinct exit codes. Downstream, meta-harness lost an hour three times
(DEF-240) reading "Gradle build daemon disappeared unexpectedly" as a red graph.

Two layers:

* unit tests over ``summarize_sweep`` / ``sweep_exit_code`` and sweep.py's
  classification, fed ledger records and run directories directly;
* ``GradleFixtureTest``: two real fixture graphs run through ``scripts/run.py``
  under real Gradle with the real ledger init script. One node fails its
  assertion; the other halts its own Gradle JVM mid-task. Set
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

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
SKILL_ROOT = SCRIPTS_DIR.parent
sys.path.insert(0, str(SCRIPTS_DIR))

import run  # noqa: E402
import sweep  # noqa: E402


def scheduled(task: str) -> dict:
    return {"event": "scheduled", "task": task, "graph": True}


def started(task: str) -> dict:
    return {"event": "started", "task": task, "graph": True}


def finished(task: str, outcome: str, run_dirs: list[str] | None = None, failure: str | None = None) -> dict:
    return {"event": "finished", "task": task, "graph": True, "outcome": outcome,
            "seconds": 1.0, "runDirs": run_dirs or [], "failure": failure, "skipMessage": None}


class _Tmp(unittest.TestCase):
    def tmp(self) -> Path:
        holder = tempfile.TemporaryDirectory()
        self.addCleanup(holder.cleanup)
        return Path(holder.name)

    def run_dir(self, status: str | None, name: str = "run") -> str:
        """A run dir; ``status`` None means the graph never wrote summary.json."""
        d = self.tmp() / name
        d.mkdir()
        if status is not None:
            (d / "summary.json").write_text(json.dumps({"status": status}))
        return str(d)


class SummarizeErroredTest(_Tmp):
    def statuses(self, records: list[dict], graphs: list[str]) -> dict[str, str]:
        summary = run.summarize_sweep(graphs, records, run_all=False)
        return {r["graph"]: r["status"] for r in summary["results"]}

    def test_started_but_never_finished_is_errored_not_never_started(self) -> None:
        summary = run.summarize_sweep(
            ["dies", "after"], [scheduled("dies"), scheduled("after"), started("dies")], run_all=False)
        dies, after = summary["results"]
        self.assertEqual("errored", dies["status"])
        self.assertIn("never finished", dies["reason"])
        self.assertNotIn("never started", dies["reason"])
        # A graph Gradle never began is still not_run, with the old reason.
        self.assertEqual("not_run", after["status"])
        self.assertEqual("scheduled, but Gradle never started it", after["reason"])
        self.assertEqual((1, 0, 1, 1), (summary["graphs_executed"], summary["graphs_failed"],
                                        summary["graphs_errored"], summary["graphs_not_run"]))

    def test_red_verdict_is_failed(self) -> None:
        red = self.run_dir("failed")
        self.assertEqual({"g": "failed"}, self.statuses(
            [scheduled("g"), started("g"), finished("g", "failed", [red], "assertion red")], ["g"]))

    def test_task_failure_without_a_report_is_errored(self) -> None:
        none = self.run_dir(None)
        summary = run.summarize_sweep(
            ["g"], [scheduled("g"), started("g"),
                    finished("g", "failed", [none], "Gradle build daemon disappeared unexpectedly")],
            run_all=False)
        entry = summary["results"][0]
        self.assertEqual("errored", entry["status"])
        self.assertIn("no summary.json", entry["reason"])
        self.assertIn("daemon disappeared", entry["reason"])
        self.assertEqual(0, summary["graphs_failed"])

    def test_node_that_never_reported_a_verdict_is_errored(self) -> None:
        crashed = self.run_dir("errored")
        self.assertEqual({"g": "errored"}, self.statuses(
            [scheduled("g"), started("g"), finished("g", "failed", [crashed], "node crashed")], ["g"]))

    def test_old_ledger_without_started_events_still_reads(self) -> None:
        # A ledger written by the pre-#175 init script: no "started" events.
        summary = run.summarize_sweep(["a", "b"], [scheduled("a"), scheduled("b"),
                                                   finished("a", "passed")], run_all=False)
        self.assertEqual(["passed", "not_run"], [r["status"] for r in summary["results"]])
        self.assertEqual(0, summary["graphs_errored"])


class ExitCodeTest(_Tmp):
    def summary(self, *records: dict, graphs: list[str]) -> dict:
        return run.summarize_sweep(graphs, list(records), run_all=False)

    def test_errored_failed_and_green_have_distinct_exit_codes(self) -> None:
        red = self.summary(scheduled("a"), started("a"),
                           finished("a", "failed", [self.run_dir("failed")]), graphs=["a"])
        dead = self.summary(scheduled("a"), started("a"), graphs=["a"])
        green = self.summary(scheduled("a"), started("a"), finished("a", "passed"), graphs=["a"])
        codes = (run.sweep_exit_code(1, red), run.sweep_exit_code(1, dead), run.sweep_exit_code(0, green))
        self.assertEqual((1, run.SWEEP_EXIT_ERRORED, 0), codes)
        self.assertEqual(3, run.SWEEP_EXIT_ERRORED)
        self.assertEqual(3, len(set(codes)))

    def test_a_failure_outranks_an_error(self) -> None:
        both = self.summary(scheduled("a"), scheduled("b"), started("a"), started("b"),
                            finished("a", "failed", [self.run_dir("failed")]), graphs=["a", "b"])
        self.assertEqual((1, 1), (both["graphs_failed"], both["graphs_errored"]))
        self.assertEqual(1, run.sweep_exit_code(1, both))

    def test_killed_gradle_exit_code_does_not_mask_errored(self) -> None:
        dead = self.summary(scheduled("a"), started("a"), graphs=["a"])
        self.assertEqual(run.SWEEP_EXIT_ERRORED, run.sweep_exit_code(137, dead))

    def test_format_summary_labels_and_explains_errored(self) -> None:
        dead = self.summary(scheduled("a"), started("a"), graphs=["a"])
        text = run.format_summary(dead, "s", Path("/"), Path("/s/sweep.json"))
        self.assertIn("graphs_errored=1", text)
        self.assertIn("ERRORED  a", text)
        self.assertIn("retry it or fix the environment", text)


class SweepPyTest(_Tmp):
    def repo_with_run(self, run_id: str, status: str | None, envelopes: dict[str, str]) -> Path:
        repo = self.tmp()
        d = repo / sweep.REPORTS / run_id
        (d / "envelope").mkdir(parents=True)
        if status is not None:
            (d / "summary.json").write_text(json.dumps({"status": status}))
        for node, node_status in envelopes.items():
            (d / "envelope" / f"{node}.json").write_text(json.dumps({"nodeId": node, "status": node_status}))
        return repo

    def test_graph_status_needs_a_red_verdict_to_be_failed(self) -> None:
        self.assertEqual("passed", sweep.graph_status(0, None))
        self.assertEqual("failed", sweep.graph_status(1, "failed"))
        self.assertEqual("errored", sweep.graph_status(1, "errored"))
        self.assertEqual("errored", sweep.graph_status(1, None))

    def test_node_outcomes_split_failed_errored_skipped(self) -> None:
        repo = self.repo_with_run("r1", "errored", {"a": "passed", "b": "failed", "c": "errored", "d": "skipped"})
        self.assertEqual((["b"], ["c"], ["d"]), sweep.node_outcomes(repo, "r1"))

    def test_retry_resumes_a_failed_graph_and_restarts_an_errored_one(self) -> None:
        repo = self.repo_with_run("red", "failed", {"n.red": "failed", "n.after": "skipped"})
        crashed = repo / sweep.REPORTS / "crashed"
        (crashed / "envelope").mkdir(parents=True)
        (crashed / "summary.json").write_text(json.dumps({"status": "errored"}))
        (crashed / "envelope" / "n.crash.json").write_text(json.dumps({"nodeId": "n.crash", "status": "errored"}))
        prev = {"results": [
            {"graph": "green", "passed": True, "exit_code": 0, "run_id": None},
            {"graph": "redGraph", "passed": False, "exit_code": 1, "run_id": "red", "status": "failed"},
            {"graph": "crashGraph", "passed": False, "exit_code": 1, "run_id": "crashed", "status": "errored"},
            # pre-#175 record: no status, no report at all (the daemon died)
            {"graph": "deadGraph", "passed": False, "exit_code": 1, "run_id": None},
        ]}
        graphs, plan = sweep.plan_retry(repo, prev)
        self.assertEqual(["redGraph", "crashGraph", "deadGraph"], graphs)
        self.assertEqual({"redGraph": (f"{sweep.REPORTS}/red", "n.red")}, plan)


GRADLE_FIXTURE_BUILD = '''\
// validationGraph fixture for issue #175: real graph-shaped tasks, no SDK.
// The ledger init script recognises a graph task by its class name.
abstract class RunTestGraphTask : DefaultTask() {
    @get:Internal abstract val reportRoot: DirectoryProperty
    @get:Internal abstract val mode: Property<String>

    @TaskAction
    fun execute() {
        val runDir = reportRoot.get().asFile.resolve("run-$name")
        runDir.mkdirs()
        when (mode.get()) {
            "red" -> {
                // The node completed and its assertion was red.
                runDir.resolve("summary.json").writeText("""{"status":"failed"}""")
                throw GradleException("node fixture.red: expected 1 but was 2")
            }
            // The runner dies mid-task, as when a harness kills the daemon.
            "dies" -> Runtime.getRuntime().halt(137)
        }
    }
}

tasks.register<RunTestGraphTask>("redNode") {
    reportRoot.set(layout.buildDirectory.dir("validation-reports"))
    mode.set("red")
}
tasks.register<RunTestGraphTask>("deadRunner") {
    reportRoot.set(layout.buildDirectory.dir("validation-reports"))
    mode.set("dies")
}
'''


def _gradle_fixture_unavailable() -> str | None:
    if os.environ.get("TEST_GRAPH_SKIP_GRADLE_FIXTURES"):
        return "TEST_GRAPH_SKIP_GRADLE_FIXTURES is set"
    if shutil.which("java") is None:
        return "no java on PATH"
    if not (SKILL_ROOT / "project_sdk_sources" / "gradlew").is_file():
        return "no Gradle wrapper in project_sdk_sources"
    return None


@unittest.skipIf(_gradle_fixture_unavailable(), _gradle_fixture_unavailable() or "")
class GradleFixtureTest(unittest.TestCase):
    """The issue's own harness: real Gradle, real ledger, through scripts/run.py."""

    @classmethod
    def setUpClass(cls) -> None:
        cls._holder = tempfile.TemporaryDirectory()
        cls.root = Path(cls._holder.name) / "test_graph"
        cls.root.mkdir()
        sdk = SKILL_ROOT / "project_sdk_sources"
        shutil.copy2(sdk / "gradlew", cls.root / "gradlew")
        shutil.copytree(sdk / "gradle", cls.root / "gradle")
        (cls.root / "settings.gradle.kts").write_text('rootProject.name = "errored-vs-failed"\n')
        (cls.root / "build.gradle.kts").write_text(GRADLE_FIXTURE_BUILD)

    @classmethod
    def tearDownClass(cls) -> None:
        cls._holder.cleanup()

    def sweep(self, graph: str) -> tuple[int, dict, str]:
        before = set((self.root / "build" / "validation-sweeps").glob("*"))
        proc = subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "run.py"), graph, "--continue",
             "--test-graph-root", str(self.root)],
            capture_output=True, text=True, timeout=900,
        )
        after = set((self.root / "build" / "validation-sweeps").glob("*")) - before
        self.assertEqual(1, len(after), proc.stdout[-3000:] + proc.stderr[-3000:])
        record = json.loads((after.pop() / "sweep.json").read_text())
        return proc.returncode, record, proc.stdout

    def test_red_node_and_dead_runner_are_told_apart(self) -> None:
        red_rc, red, red_out = self.sweep("redNode")
        dead_rc, dead, dead_out = self.sweep("deadRunner")

        self.assertEqual("failed", red["results"][0]["status"], red_out[-2000:])
        self.assertEqual("errored", dead["results"][0]["status"], dead_out[-2000:])
        self.assertIn("never finished", dead["results"][0]["reason"])

        self.assertEqual((1, 0), (red["graphs_failed"], red["graphs_errored"]))
        self.assertEqual((0, 1), (dead["graphs_failed"], dead["graphs_errored"]))
        # The old fields are still there for existing consumers.
        for record in (red, dead):
            for key in ("graphs_selected", "graphs_executed", "graphs_passed", "graphs_not_run"):
                self.assertIn(key, record)
        self.assertEqual(1, red["graphs_executed"])
        self.assertEqual(1, dead["graphs_executed"])

        self.assertEqual(1, red_rc)
        self.assertEqual(run.SWEEP_EXIT_ERRORED, dead_rc)
        self.assertIn("FAILED   redNode", red_out)
        self.assertIn("ERRORED  deadRunner", dead_out)


if __name__ == "__main__":
    unittest.main()
