"""Issue #186 (+ #138 SF-023): ``run.py --resume <report>`` is the front door.

Resuming used to mean a hand-written ``--resume-from-build <abs path>
--resume-from-node <node>`` per attempt; a relative path was resolved against
the caller's cwd rather than the test-graph root, so ``--run-only-node`` with
``build/validation-reports/<runId>`` from a repository root was refused.

Acceptance, red on ``origin/epic/bug-sweep`` and green on the fix:

* a resume of a resume runs only the tail;
* ``--from-node`` with a relative report path works;
* ``--run-only-node`` with a relative report path works.

Two layers, as in ``test_outcome_json.py``: unit tests with Gradle mocked, and
``RealSdkResumeTest`` under the real SDK and real Gradle
(``TEST_GRAPH_SKIP_GRADLE_FIXTURES=1`` skips it).
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
sys.path.insert(0, str(SCRIPTS_DIR))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import run  # noqa: E402
from test_outcome_json import (  # noqa: E402
    FIXTURE_SETTINGS, NODE_HEADER, SDK, _real_sdk_unavailable, write_envelope)


@contextlib.contextmanager
def chdir(path: Path):
    old = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(old)


def make_report(root: Path, run_id: str, statuses: dict[str, str], graph: str = "chain",
                contexts: tuple[str, ...] | None = None) -> Path:
    """A report dir with an execution scope, envelopes and saved input contexts."""
    d = root / "build" / "validation-reports" / run_id
    d.mkdir(parents=True)
    (d / "execution-scope.json").write_text(json.dumps(
        {"graphName": graph, "expectedNodeIds": list(statuses)}))
    (d / "context").mkdir()
    for node, status in statuses.items():
        if status != "absent":
            write_envelope(d, node, status)
    for node in contexts if contexts is not None else statuses:
        (d / "context" / f"{node}.input.json").write_text("[]")
    # run.py resolves the test-graph root (macOS: /var -> /private/var).
    return d.resolve()


class ResumeFrontDoorTest(unittest.TestCase):
    def setUp(self) -> None:
        holder = tempfile.TemporaryDirectory()
        self.addCleanup(holder.cleanup)
        self.tmp = Path(holder.name)
        self.root = self.tmp / "test_graph"
        self.root.mkdir()
        (self.root / "settings.gradle.kts").write_text('rootProject.name = "fixture"\n')
        (self.root / "build.gradle.kts").write_text("validationGraph { }\n")
        self.ledger = [{"event": "scheduled", "task": "chain", "graph": True},
                       {"event": "finished", "task": "chain", "graph": True, "outcome": "passed",
                        "seconds": 1.0, "runDirs": [], "failure": None}]

    def main(self, *argv: str, cwd: Path | None = None):
        calls = []

        def fake_run_gradle(args, test_graph_root=None, extra_env=None):
            calls.append(list(args))
            with open(extra_env[run.SWEEP_LEDGER_ENV], "a", encoding="utf-8") as fh:
                for line in self.ledger:
                    fh.write(json.dumps(line) + "\n")
            return 0

        out, err = io.StringIO(), io.StringIO()
        with chdir(cwd or self.tmp), patch.object(run, "run_gradle", side_effect=fake_run_gradle), \
                contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            try:
                code = run.main([*argv, "--test-graph-root", str(self.root)])
            except SystemExit as exc:
                code = exc.code
        return code, calls, out.getvalue(), err.getvalue()

    def gradle_flag(self, args: list[str], flag: str) -> str | None:
        hits = [a.split("=", 1)[1] for a in args if a.startswith(f"--{flag}=")]
        return hits[0] if hits else None

    def test_resume_relative_report_picks_first_failed_node_and_infers_graph(self) -> None:
        report = make_report(self.root, "20990101-000001",
                             {"n.a": "passed", "n.b": "failed", "n.c": "absent"}, contexts=("n.a", "n.b"))
        code, calls, out, err = self.main("--resume", "build/validation-reports/20990101-000001")
        self.assertEqual(0, code, err)
        args = calls[0]
        self.assertIn("chain", args)
        self.assertEqual(str(report), self.gradle_flag(args, "resume-from-build"))
        self.assertEqual("n.b", self.gradle_flag(args, "resume-from-node"))
        self.assertIsNone(self.gradle_flag(args, "run-only-node"))
        outcome = json.loads(Path(out.strip().splitlines()[-1]).read_text())
        self.assertEqual({"source_report": str(report), "node": "n.b", "mode": "resume-from-node"},
                         outcome["resume"])

    def test_from_node_with_a_relative_path_and_a_bare_run_id(self) -> None:
        report = make_report(self.root, "20990101-000002", {"n.a": "passed", "n.b": "failed"})
        for spec in ("test_graph/build/validation-reports/20990101-000002", "20990101-000002"):
            code, calls, _out, err = self.main("--resume", spec, "--from-node", "n.a")
            self.assertEqual(0, code, err)
            self.assertEqual(str(report), self.gradle_flag(calls[0], "resume-from-build"))
            self.assertEqual("n.a", self.gradle_flag(calls[0], "resume-from-node"))

    def test_errored_node_is_resumable_when_nothing_failed(self) -> None:
        make_report(self.root, "20990101-000003", {"n.a": "passed", "n.b": "errored"})
        _code, calls, _out, err = self.main("--resume", "20990101-000003")
        self.assertEqual("n.b", self.gradle_flag(calls[0], "resume-from-node"), err)

    def test_an_outcome_json_chains_to_its_report(self) -> None:
        report = make_report(self.root, "20990101-000004", {"n.b": "passed", "n.c": "failed"})
        outcome = self.tmp / "outcome.json"
        outcome.write_text(json.dumps({"graphs": [{"graph": "chain", "report_dir": str(report)}]}))
        code, calls, _out, err = self.main("--resume", str(outcome))
        self.assertEqual(0, code, err)
        self.assertEqual(str(report), self.gradle_flag(calls[0], "resume-from-build"))
        self.assertEqual("n.c", self.gradle_flag(calls[0], "resume-from-node"))

    def test_only_node_and_its_legacy_synonym(self) -> None:
        make_report(self.root, "20990101-000005", {"n.a": "passed", "n.b": "failed"})
        for flag in ("--only-node", "--run-only-node"):
            code, calls, _out, err = self.main("--resume", "20990101-000005", flag, "n.a")
            self.assertEqual(0, code, err)
            self.assertEqual("n.a", self.gradle_flag(calls[0], "run-only-node"))
            self.assertIsNone(self.gradle_flag(calls[0], "resume-from-node"))

    def test_legacy_run_only_node_resolves_a_relative_path_against_the_test_graph_root(self) -> None:
        # #138 SF-023: cwd is the repository root, not test_graph/.
        report = make_report(self.root, "20990101-000006", {"n.a": "passed"})
        code, calls, _out, err = self.main(
            "chain", "--resume-from-build", "build/validation-reports/20990101-000006",
            "--run-only-node", "n.a")
        self.assertEqual(0, code, err)
        self.assertEqual(str(report), self.gradle_flag(calls[0], "resume-from-build"))

    def test_refusals_name_the_problem(self) -> None:
        make_report(self.root, "20990101-000007", {"n.a": "passed", "n.b": "passed"})
        make_report(self.root, "20990101-000008", {"n.a": "passed", "n.b": "failed"},
                    contexts=("n.a",))
        cases = [
            (("--resume", "20990101-000007"), "no failed or errored node"),
            (("--resume", "nope"), "no report directory found"),
            (("other", "--resume", "20990101-000008", "--from-node", "n.a"), "not 'other'"),
            (("--resume", "20990101-000008"), "no saved input context for 'n.b'"),
            (("--resume", "20990101-000008", "--from-node", "n.a", "--only-node", "n.a"), "at most one"),
            (("chain", "--from-node", "n.a"), "apply to --resume"),
        ]
        for argv, needle in cases:
            code, calls, _out, err = self.main(*argv)
            self.assertEqual(2, code, argv)
            self.assertEqual([], calls, argv)
            self.assertIn(needle, err, argv)


# ---------------------------------------------------------------- real SDK

def chain_node(node_id: str, depends: str | None) -> str:
    dep = f'.depends_on("{depends}")' if depends else ""
    return NODE_HEADER + f'''
from pathlib import Path

from testgraphsdk import NodeResult, NodeSpec, node

SPEC = NodeSpec("{node_id}").kind("assertion").timeout("60s"){dep}
ROOT = Path(__file__).resolve().parents[1]


@node(SPEC)
def main(ctx):
    with open(ROOT / "runs.log", "a", encoding="utf-8") as fh:
        fh.write(ctx.node_id + "\\n")
    if (ROOT / ("fail-" + ctx.node_id)).exists():
        return NodeResult.fail(ctx.node_id, "marker says fail").assertion("marker_absent", False)
    return NodeResult.pass_(ctx.node_id)


if __name__ == "__main__":
    main()
'''


CHAIN_BUILD = '''\
plugins {
    id("com.hayden.testgraphsdk.graph")
}

validationGraph {
    testGraph("chain") {
        node("nodes/a.py")
        node("nodes/b.py")
        node("nodes/c.py")
    }
}
'''


@unittest.skipIf(_real_sdk_unavailable(), _real_sdk_unavailable() or "")
class RealSdkResumeTest(unittest.TestCase):
    """The issue's acceptance under the real SDK: chain a -> b -> c, b red first."""

    @classmethod
    def setUpClass(cls) -> None:
        cls._holder = tempfile.TemporaryDirectory()
        cls.repo = Path(cls._holder.name)
        cls.root = cls.repo / "test_graph"
        cls.root.mkdir()
        shutil.copy2(SDK / "gradlew", cls.root / "gradlew")
        shutil.copytree(SDK / "gradle", cls.root / "gradle")
        shutil.copytree(SDK / "build-logic", cls.root / "build-logic",
                        ignore=shutil.ignore_patterns("build", ".gradle", ".kotlin"))
        shutil.copytree(SDK / "sdk" / "python", cls.root / "sdk" / "python",
                        ignore=shutil.ignore_patterns(".venv", "__pycache__", "*.egg-info"))
        (cls.root / "settings.gradle.kts").write_text(FIXTURE_SETTINGS)
        (cls.root / "build.gradle.kts").write_text(CHAIN_BUILD)
        nodes = cls.root / "nodes"
        nodes.mkdir()
        for name, node_id, dep in (("a.py", "fixture.a", None), ("b.py", "fixture.b", "fixture.a"),
                                   ("c.py", "fixture.c", "fixture.b")):
            (nodes / name).write_text(chain_node(node_id, dep))
        (cls.root / "fail-fixture.b").touch()
        try:
            rc, outcome, transcript = cls._invoke("chain")
        finally:
            (cls.root / "fail-fixture.b").unlink()
        statuses = {n["node"]: n["status"] for g in outcome["graphs"] for n in g["nodes"]}
        assert (rc, statuses) == (1, {"fixture.a": "passed", "fixture.b": "failed",
                                      "fixture.c": "not_run"}), transcript
        cls.first = Path(outcome["graphs"][0]["report_dir"])
        # Relative to the TEST-GRAPH root, invoked from the repository root.
        cls.first_rel = f"build/validation-reports/{cls.first.name}"

    @classmethod
    def tearDownClass(cls) -> None:
        cls._holder.cleanup()

    @classmethod
    def _invoke(cls, *argv: str) -> tuple[int, dict, str]:
        proc = subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "run.py"), *argv, "--test-graph-root", "test_graph"],
            cwd=cls.repo, capture_output=True, text=True, timeout=1500)
        transcript = proc.stdout[-4000:] + proc.stderr[-4000:]
        lines = proc.stdout.strip().splitlines()
        last = Path(lines[-1]) if lines else Path("/nonexistent")
        if last.name != "outcome.json" or not last.is_file():
            raise AssertionError("no outcome.json on the last stdout line\n" + transcript)
        return proc.returncode, json.loads(last.read_text()), transcript

    def invoke(self, *argv: str) -> tuple[int, dict, list[str], str]:
        """Run, and return the node ids that actually EXECUTED in this invocation."""
        log = self.root / "runs.log"
        before = len(log.read_text().splitlines()) if log.exists() else 0
        rc, outcome, transcript = self._invoke(*argv)
        executed = log.read_text().splitlines()[before:] if log.exists() else []
        return rc, outcome, executed, transcript

    def statuses(self, outcome: dict) -> dict[str, str]:
        return {n["node"]: n["status"] for g in outcome["graphs"] for n in g["nodes"]}

    def test_a_resume_of_a_resume_runs_only_the_tail(self) -> None:
        marker = self.root / "fail-fixture.c"
        marker.touch()
        try:
            # Resume 1: no node named -> the first failed node, fixture.b.
            rc, second, executed, transcript = self.invoke("--resume", self.first_rel)
        finally:
            marker.unlink()
        self.assertEqual(["fixture.b", "fixture.c"], executed, transcript)
        self.assertEqual({"fixture.b": "passed", "fixture.c": "failed"}, self.statuses(second), transcript)
        self.assertEqual(1, rc, transcript)
        # Resume 2 sources resume 1, through its outcome.json: only fixture.c runs.
        second_outcome = Path(second["report_dir"]) / "outcome.json"
        rc, third, executed, transcript = self.invoke("--resume", str(second_outcome))
        self.assertEqual(["fixture.c"], executed, transcript)
        self.assertEqual({"fixture.c": "passed"}, self.statuses(third), transcript)
        self.assertEqual((0, 0), (rc, third["exit_code"]), transcript)
        self.assertEqual(("fixture.c", "resume-from-node"),
                         (third["resume"]["node"], third["resume"]["mode"]), transcript)

    def test_from_node_with_a_relative_report_path(self) -> None:
        rc, outcome, executed, transcript = self.invoke(
            "--resume", self.first_rel, "--from-node", "fixture.b")
        self.assertEqual(["fixture.b", "fixture.c"], executed, transcript)
        self.assertEqual({"fixture.b": "passed", "fixture.c": "passed"}, self.statuses(outcome), transcript)
        self.assertEqual(0, rc, transcript)

    def test_run_only_node_with_a_relative_report_path(self) -> None:
        rc, outcome, executed, transcript = self.invoke(
            "chain", "--resume-from-build", self.first_rel, "--run-only-node", "fixture.b")
        self.assertEqual(["fixture.b"], executed, transcript)
        self.assertEqual({"fixture.b": "passed"}, self.statuses(outcome), transcript)
        self.assertEqual(0, rc, transcript)
        rc, outcome, executed, transcript = self.invoke(
            "--resume", self.first_rel, "--only-node", "fixture.b")
        self.assertEqual(["fixture.b"], executed, transcript)
        self.assertEqual(0, rc, transcript)


if __name__ == "__main__":
    unittest.main()
