"""BS-14 / issue #147 step 1: the milestone runner and its lock.

Each test feeds a vacuum the hand-kept milestone.sh mishandled: no graphs
configured, a dead owner's lock, an ancestor holding the lock (the 4.1 h
deadlock), a run that leaves no outcome.json, and a shared graph reached while
default is red. The runner is a fake ``run.py`` that writes a real
``test-graph.outcome.v1``-shaped outcome.json, so the verdict path is the one
BS-11's run.py produces.
"""
from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
import signal
import socket
import time
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path
from unittest import mock

SCRIPT = Path(__file__).parents[1] / "milestone.py"
SPEC = importlib.util.spec_from_file_location("milestone", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
ms = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = ms
SPEC.loader.exec_module(ms)

# Fake run.py: statuses come from FAKE_STATUSES (json {graph: status}); a graph
# with status "absent" is left out of outcome.json; FAKE_NO_OUTCOME=1 prints no
# path at all. Every invocation is appended to FAKE_CALLS.
FAKE_RUNNER = textwrap.dedent('''
    import json, os, sys, pathlib
    graphs = [a for a in sys.argv[1:] if not a.startswith("-")]
    with open(os.environ["FAKE_CALLS"], "a") as fh:
        fh.write(json.dumps(graphs) + "\\n")
    if os.environ.get("FAKE_NO_OUTCOME") == "1":
        print("gradle blew up before writing anything")
        sys.exit(3)
    statuses = json.loads(os.environ.get("FAKE_STATUSES", "{}"))
    out = pathlib.Path(os.environ["FAKE_OUT"]) / str(len(open(os.environ["FAKE_CALLS"]).readlines()))
    out.mkdir(parents=True, exist_ok=True)
    rows = [{"graph": g, "status": statuses.get(g, "passed"), "cause": None,
             "duration_seconds": 1.5, "report_dir": str(out),
             "nodes": [{"node": "fixture.observed", "status": statuses.get(g, "passed")}]}
            for g in graphs if statuses.get(g) != "absent"]
    (out / "outcome.json").write_text(json.dumps({"schema": "test-graph.outcome.v1", "graphs": rows}))
    print(out / "outcome.json")
''')


class MilestoneCase(unittest.TestCase):
    def setUp(self) -> None:
        holder = tempfile.TemporaryDirectory()
        self.addCleanup(holder.cleanup)
        self.root = Path(holder.name).resolve()
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)
        subprocess.run(["git", "-C", str(self.root), "-c", "user.name=Milestone fixture",
                        "-c", "user.email=fixture@example.invalid", "commit", "--allow-empty",
                        "-qm", "source identity"], check=True)
        (self.root / "fake_run.py").write_text(FAKE_RUNNER)
        self.calls = self.root / "calls.jsonl"
        self.calls.touch()
        env = {"FAKE_CALLS": str(self.calls), "FAKE_OUT": str(self.root / "out"),
               "FAKE_STATUSES": "{}", "FAKE_NO_OUTCOME": "0", "SKILL_GATES": "on"}
        patcher = mock.patch.dict(os.environ, env)
        patcher.start()
        self.addCleanup(patcher.stop)
        os.environ.pop(ms.CONFIG_ENV, None)

    def config(self, default=(), shared=(), extra="") -> None:
        (self.root / "epic-workflow.toml").write_text(
            "[milestone]\n"
            f"default = {json.dumps(list(default))}\n"
            f"shared = {json.dumps(list(shared))}\n"
            'runner = "fake_run.py"\n' + extra)

    def run_ms(self, *argv: str) -> tuple[int, str, str]:
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = ms.milestone(list(argv), cwd=self.root)
        return code, out.getvalue(), err.getvalue()

    def invoked(self) -> list[list[str]]:
        return [json.loads(ln) for ln in self.calls.read_text().splitlines()]

    @property
    def lock(self) -> Path:
        return self.root / "build" / "milestone.lock"

    def write_lock(self, pid: int, **extra) -> None:
        self.lock.parent.mkdir(parents=True, exist_ok=True)
        self.lock.write_text(json.dumps({"pid": pid, "host": socket.gethostname(),
                                         "acquired_at": "earlier", **extra}))


class FailureCustodyTest(MilestoneCase):
    def test_stderr_only_failure_is_retained_privately(self):
        self.config(default=['gate'], shared=['load'])
        (self.root / 'fake_run.py').write_text(
            "import sys\nsys.stderr.write('pre-SDK diagnostic\\n')\nsys.exit(3)\n")
        self.assertEqual(self.run_ms()[0], ms.EXIT_ERRORED)
        path = next((self.root / 'build/milestone-runs').glob('*/default.stderr.log'))
        self.assertEqual(path.read_text(), 'pre-SDK diagnostic\n')
        self.assertEqual(path.stat().st_mode & 0o777, 0o600)


    def test_emitted_bytes_survive_controller_interruption(self):
        self.config(default=['gate'])
        (self.root / 'fake_run.py').write_text(
            "import sys,time\nprint('stdout before completion',flush=True)\n"
            "print('stderr before completion',file=sys.stderr,flush=True)\ntime.sleep(60)\n")
        with tempfile.TemporaryFile() as live:
            process = subprocess.Popen([sys.executable, '-B', str(SCRIPT)], cwd=self.root,
                                       stdout=live, stderr=live)
            try:
                deadline = time.monotonic() + 10
                paths = []
                while time.monotonic() < deadline:
                    paths = list((self.root / 'build/milestone-runs').glob('*/default.*.log'))
                    if len(paths) == 2 and all(path.stat().st_size > 0 for path in paths):
                        break
                    time.sleep(0.02)
                self.assertIsNone(process.poll(), 'runner must still be active at observation')
                self.assertEqual(len(paths), 2)
                self.assertEqual({path.read_text() for path in paths},
                                 {'stdout before completion\n', 'stderr before completion\n'})
                process.send_signal(signal.SIGINT)
                self.assertNotEqual(process.wait(timeout=10), 0)
                self.assertTrue(all(path.stat().st_size > 0 for path in paths))
                self.assertTrue(all(path.stat().st_mode & 0o777 == 0o600 for path in paths))
            finally:
                if process.poll() is None:
                    process.send_signal(signal.SIGINT)
                    process.wait(timeout=10)


class SealedMetadataTest(MilestoneCase):
    def test_reused_metadata_comes_from_terminal_authority(self):
        self.config(default=['gate'], shared=['load'])
        self.assertEqual(self.run_ms('gate')[0], ms.EXIT_PASSED)
        hint_path = self.root / 'build/milestone-last.json'
        hint = json.loads(hint_path.read_text())
        row = hint['executions']['default:gate']
        row.update(graph='forged', phase='shared', duration_seconds=-999)
        hint_path.write_text(json.dumps(hint))
        self.assertEqual(self.run_ms('load')[0], ms.EXIT_PASSED)
        reused = json.loads(hint_path.read_text())['executions']['default:gate']
        self.assertEqual(reused['graph'], 'gate')
        self.assertEqual(reused['phase'], 'default')
        self.assertEqual(reused['duration_seconds'], 1.5)


class VacuumTest(MilestoneCase):
    def test_no_graphs_configured_is_refused_not_green(self) -> None:
        self.config()
        code, _, err = self.run_ms()
        self.assertEqual(code, ms.EXIT_REFUSED)
        self.assertIn("runs nothing is not green", err)
        self.assertEqual(self.invoked(), [])

    def test_no_graphs_configured_with_force_exits_zero_and_warns(self) -> None:
        self.config()
        code, out, _ = self.run_ms("--force")
        self.assertEqual(code, ms.EXIT_PASSED)
        self.assertIn("nothing run", out)

    def test_missing_config_is_refused(self) -> None:
        code, _, err = self.run_ms()
        self.assertEqual(code, ms.EXIT_REFUSED)
        self.assertIn("no milestone config", err)

    def test_unknown_graph_is_refused(self) -> None:
        self.config(default=["a"])
        code, _, err = self.run_ms("nope")
        self.assertEqual(code, ms.EXIT_REFUSED)
        self.assertIn("nope", err)


class OutcomeTest(MilestoneCase):
    def test_all_green_runs_default_then_shared(self) -> None:
        self.config(default=["a", "b"], shared=["load"])
        code, out, _ = self.run_ms()
        self.assertEqual(code, ms.EXIT_PASSED)
        self.assertEqual(self.invoked(), [["a", "b"], ["load"]])
        self.assertIn("| load | shared | PASSED |", out)
        self.assertFalse(self.lock.exists(), "lock released after the run")

    def test_missing_outcome_json_counts_as_errored(self) -> None:
        self.config(default=["a"])
        os.environ["FAKE_NO_OUTCOME"] = "1"
        code, out, _ = self.run_ms()
        self.assertEqual(code, ms.EXIT_ERRORED)
        self.assertIn("| a | default | ERRORED | no outcome.json", out)

    def test_graph_absent_from_outcome_counts_as_errored(self) -> None:
        self.config(default=["a", "b"])
        os.environ["FAKE_STATUSES"] = json.dumps({"b": "absent"})
        code, out, _ = self.run_ms()
        self.assertEqual(code, ms.EXIT_ERRORED)
        self.assertIn("| b | default | ERRORED | graph missing from outcome.json", out)

    def test_missing_runner_is_errored_not_failed(self) -> None:
        self.config(default=["a"])
        code, out, _ = self.run_ms("--runner", str(self.root / "gone.py"))
        self.assertEqual(code, ms.EXIT_ERRORED)
        self.assertIn("runner not found", out)

    def test_failed_outranks_errored(self) -> None:
        self.config(default=["a", "b"])
        os.environ["FAKE_STATUSES"] = json.dumps({"a": "failed", "b": "errored"})
        code, _, _ = self.run_ms()
        self.assertEqual(code, ms.EXIT_FAILED)

    def test_runner_is_not_execd_so_a_lost_exec_bit_is_harmless(self) -> None:
        self.config(default=["a"])
        os.chmod(self.root / "fake_run.py", 0o644)
        code, _, _ = self.run_ms()
        self.assertEqual(code, ms.EXIT_PASSED)


class SharedDependencyTest(MilestoneCase):
    def test_shared_skipped_while_default_is_red(self) -> None:
        self.config(default=["a"], shared=["load"])
        os.environ["FAKE_STATUSES"] = json.dumps({"a": "failed"})
        code, out, _ = self.run_ms()
        self.assertEqual(code, ms.EXIT_FAILED)
        self.assertEqual(self.invoked(), [["a"]], "shared graph must not run")
        self.assertIn("| load | shared | NOT_RUN | skipped: default set not green", out)

    def test_shared_skipped_while_default_errored(self) -> None:
        self.config(default=["a"], shared=["load"])
        os.environ["FAKE_NO_OUTCOME"] = "1"
        code, _, _ = self.run_ms()
        self.assertEqual(code, ms.EXIT_ERRORED)  # blocked dependents preserve infrastructure classification
        self.assertEqual(self.invoked(), [["a"]])

    def test_force_runs_shared_although_default_red(self) -> None:
        self.config(default=["a"], shared=["load"])
        os.environ["FAKE_STATUSES"] = json.dumps({"a": "failed"})
        code, _, _ = self.run_ms("--force")
        self.assertEqual(code, ms.EXIT_FAILED)
        self.assertEqual(self.invoked(), [["a"], ["load"]])

    def test_targeted_shared_rerun_uses_last_recorded_default(self) -> None:
        self.config(default=["a"], shared=["load"])
        os.environ["FAKE_STATUSES"] = json.dumps({"a": "failed"})
        self.run_ms()
        code, out, _ = self.run_ms("load")
        self.assertEqual(code, ms.EXIT_FAILED)
        self.assertIn("default set not green", out)
        self.assertEqual(self.invoked(), [["a"]])
        os.environ["FAKE_STATUSES"] = "{}"
        self.run_ms("a")
        code, _, _ = self.run_ms("load")
        self.assertEqual(code, ms.EXIT_PASSED)
        self.assertEqual(self.invoked(), [["a"], ["a"], ["load"]])

    def test_targeted_shared_rerun_with_no_record_is_skipped(self) -> None:
        self.config(default=["a"], shared=["load"])
        code, _, _ = self.run_ms("load")
        self.assertEqual(code, ms.EXIT_FAILED)
        self.assertEqual(self.invoked(), [])


class BoundAdmissionTest(MilestoneCase):
    def test_same_graph_names_have_distinct_phase_authorities(self):
        self.config(default=["load"], shared=["load"])
        code, output, _ = self.run_ms()
        self.assertEqual(code, ms.EXIT_PASSED)
        self.assertEqual(self.invoked(), [["load"], ["load"]])
        self.assertIn("| load | default | PASSED", output)
        self.assertIn("| load | shared | PASSED", output)
        last = json.loads((self.root / "build/milestone-last.json").read_text())
        self.assertEqual(set(last["executions"]), {"default:load", "shared:load"})

    def test_architecture_change_refuses_cached_green_then_accepts_fresh(self):
        self.config(default=["a"], shared=["load"])
        self.assertEqual(self.run_ms("a")[0], ms.EXIT_PASSED)
        with mock.patch("evidence.platform.machine", return_value="different-architecture"):
            self.assertEqual(self.run_ms("load")[0], ms.EXIT_FAILED)
            self.assertEqual(self.invoked(), [["a"]])
            self.assertEqual(self.run_ms("a")[0], ms.EXIT_PASSED)
            self.assertEqual(self.run_ms("load")[0], ms.EXIT_PASSED)
        self.assertEqual(self.invoked(), [["a"], ["a"], ["load"]])

    def test_force_receipt_is_not_normal_cached_authority(self):
        self.config(default=["a"], shared=["load"])
        self.assertEqual(self.run_ms("a", "--force")[0], ms.EXIT_PASSED)
        self.assertEqual(self.run_ms("load")[0], ms.EXIT_FAILED)
        self.assertEqual(self.invoked(), [["a"]])

    def test_legacy_unbound_cache_cannot_admit_shared(self):
        self.config(default=["a"], shared=["load"])
        path = self.root / "build/milestone-last.json"
        path.parent.mkdir()
        path.write_text(json.dumps({"graphs": {"a": {"status": "passed"}}}))
        self.assertEqual(self.run_ms("load")[0], ms.EXIT_FAILED)
        self.assertEqual(self.invoked(), [])

    def test_terminal_records_are_unique_and_previous_bytes_retained(self):
        self.config(default=["a"])
        self.assertEqual(self.run_ms()[0], ms.EXIT_PASSED)
        old = next((self.root / "build/milestone-runs").glob("*/result.json"))
        original = old.read_bytes()
        self.assertEqual(self.run_ms()[0], ms.EXIT_PASSED)
        self.assertEqual(old.read_bytes(), original)
        self.assertEqual(len(list((self.root / "build/milestone-runs").glob("*/result.json"))), 2)


class LockTest(MilestoneCase):
    def dead_pid(self) -> int:
        proc = subprocess.Popen([sys.executable, "-c", "pass"])
        proc.wait()
        return proc.pid

    def test_stale_lock_is_reclaimed_and_reported(self) -> None:
        self.config(default=["a"])
        dead = self.dead_pid()
        self.write_lock(dead)
        code, out, _ = self.run_ms()
        self.assertEqual(code, ms.EXIT_PASSED)
        self.assertIn(f"reclaimed stale lock", out)
        self.assertIn(f"pid {dead}", out)
        self.assertFalse(self.lock.exists())

    def test_garbage_lock_is_reclaimed(self) -> None:
        self.config(default=["a"])
        self.lock.parent.mkdir(parents=True)
        self.lock.write_text("not json")
        code, out, _ = self.run_ms()
        self.assertEqual(code, ms.EXIT_PASSED)
        self.assertIn("reclaimed stale lock", out)

    def test_ancestor_reentry_is_refused_at_once(self) -> None:
        self.config(default=["a"])
        self.write_lock(os.getppid())  # an ancestor of this test process
        code, _, err = self.run_ms()
        self.assertEqual(code, ms.EXIT_REFUSED)
        self.assertIn("ANCESTOR", err)
        self.assertEqual(self.invoked(), [])
        self.assertTrue(self.lock.exists(), "an ancestor's lock is never removed")

    def test_ancestor_reentry_from_a_child_process_is_refused(self) -> None:
        """The deadlock shape: the owner spawns a child that calls the runner again."""
        self.config(default=["a"])
        self.write_lock(os.getpid())
        proc = subprocess.run([sys.executable, str(SCRIPT)], cwd=self.root,
                              capture_output=True, text=True, timeout=60)
        self.assertEqual(proc.returncode, ms.EXIT_REFUSED, proc.stderr)
        self.assertIn("ANCESTOR", proc.stderr)
        self.assertEqual(self.invoked(), [])

    def test_ancestor_reentry_with_force_runs_unlocked(self) -> None:
        self.config(default=["a"])
        self.write_lock(os.getppid())
        code, _, _ = self.run_ms("--force")
        self.assertEqual(code, ms.EXIT_PASSED)
        self.assertEqual(json.loads(self.lock.read_text())["pid"], os.getppid())

    def test_live_non_ancestor_owner_is_refused(self) -> None:
        self.config(default=["a"])
        sleeper = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
        self.addCleanup(sleeper.kill)
        self.write_lock(sleeper.pid)
        code, _, err = self.run_ms()
        self.assertEqual(code, ms.EXIT_REFUSED)
        self.assertIn("held by live", err)

    def test_live_owner_taken_over_with_skill_gates_off(self) -> None:
        self.config(default=["a"])
        sleeper = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
        self.addCleanup(sleeper.kill)
        self.write_lock(sleeper.pid)
        os.environ["SKILL_GATES"] = "off"
        code, out, _ = self.run_ms()
        self.assertEqual(code, ms.EXIT_PASSED)
        self.assertIn("taking over", out)

    def test_reused_pid_is_stale(self) -> None:
        sleeper = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
        self.addCleanup(sleeper.kill)
        # The lock claims an owner that started long before this live process.
        state = ms.owner_state({"pid": sleeper.pid, "host": socket.gethostname(),
                                "started_epoch": 1_000_000_000})
        self.assertEqual(state, "stale")


if __name__ == "__main__":
    unittest.main()
