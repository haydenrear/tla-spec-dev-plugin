# /// script
# requires-python = ">=3.10"
# dependencies = ["testgraphsdk"]
#
# [tool.uv.sources]
# testgraphsdk = { path = "../sdk/python", editable = true }
# ///
from __future__ import annotations

import ctypes
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

from testgraphsdk import NodeResult, NodeSpec, node, procs


SPEC = (
    NodeSpec("spec.workflow.failure_cleanup_probe")
    .kind("assertion")
    .depends_on("spec.workflow.close")
    .tags("spec-workflow", "failure-probe", "finalizer")
    .timeout("180s")
    .side_effects("fs:tmp")
)


PROBE_BUILD = """plugins {
    id("com.hayden.testgraphsdk.graph")
}

validationGraph {
    sourcesDir("sources")

    testGraph("cleanupFailureProbe") {
        node("sources/tla_spec_dev_cli_install.py")
        node("sources/spec_workflow_create_repo.py")
        node("sources/spec_workflow_force_failure.py")
        node("sources/spec_workflow_cleanup.py").dependsOn("spec.workflow.force_failure")
    }
}
"""


def copy_probe_project(source: Path, target: Path) -> None:
    if target.exists():
        shutil.rmtree(target)
    ignore = shutil.ignore_patterns("build", ".gradle", "__pycache__", "*.pyc")
    # `support` IS REQUIRED even though this probe registers only four nodes.
    # The SDK indexes EVERY script under a configured sourcesDir (GraphAssembler:
    # "Index every remaining script under the configured sourcesDirs"), so the
    # nested build describes all 17 sources, not the 4 it runs. Five of them --
    # skt_check_cached, skt_hook_contract, skt_status_tiers, skt_ticket_roundtrip,
    # skt_wrapper_installed -- do `sys.path.insert(..., parents[1] / "support")`
    # and `from skt_fixture import ...` at MODULE level, so the import runs at
    # describe time. Omitting this directory made every one of them exit 1 with
    # `ModuleNotFoundError: No module named 'skt_fixture'`, which surfaced as
    # `describe failed for skt_check_cached.py (exit=1)` and took the whole
    # specWorkflow graph red. Those five arrived with SI-16's skt demotion
    # (4caab479); before it there was no source here that needed `support`, which
    # is why this list was complete for as long as it was.
    for name in ["settings.gradle.kts", "gradlew", "gradle", "build-logic", "sdk", "sources", "support"]:
        src = source / "test_graph" / name
        dst = target / name
        if src.is_dir():
            shutil.copytree(src, dst, ignore=ignore)
        else:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
    (target / "build.gradle.kts").write_text(PROBE_BUILD, encoding="utf-8")


def latest_probe_run(probe_root: Path) -> Path | None:
    reports = probe_root / "build" / "validation-reports"
    if not reports.exists():
        return None
    candidates = [
        path
        for path in reports.iterdir()
        if path.is_dir() and (path / "summary.json").is_file()
    ]
    return max(candidates, key=lambda path: path.stat().st_mtime, default=None)


def node_by_id(summary: dict, node_id: str) -> dict:
    for node_summary in summary.get("nodes", []):
        if node_summary.get("nodeId") == node_id:
            return node_summary
    return {}


def process_table() -> tuple[dict[int, tuple[int, str]], int]:
    """``(pid -> (ppid, command line), pid of the ps that produced it)``.

    The executor's process-ownership contract is enforced with
    ``ProcessHandle.descendants()``; this is the same inventory read
    through the POSIX ``ps`` the SDK already requires on macOS/Linux.
    ``ps`` is itself a child of this node, so its own pid is returned
    and excluded rather than counted as residue. An unavailable ``ps``
    yields an empty table, which reads as "nothing observed" — the
    executor stays the authority either way.
    """
    try:
        proc = subprocess.Popen(
            ["ps", "-eo", "pid=,ppid=,args="],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
        )
    except (OSError, subprocess.SubprocessError):
        return {}, -1
    try:
        stdout, _ = proc.communicate(timeout=20)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.communicate()
        return {}, proc.pid
    table: dict[int, tuple[int, str]] = {}
    for line in (stdout or "").splitlines():
        fields = line.split(None, 2)
        if len(fields) < 2:
            continue
        try:
            pid, ppid = int(fields[0]), int(fields[1])
        except ValueError:
            continue
        table[pid] = (ppid, fields[2] if len(fields) > 2 else "")
    return table, proc.pid


def live_descendants(root_pid: int) -> dict[int, str]:
    """Every currently-live descendant of ``root_pid``, pid -> command."""
    table, observer_pid = process_table()
    children: dict[int, list[int]] = {}
    for pid, (ppid, _) in table.items():
        children.setdefault(ppid, []).append(pid)
    found: dict[int, str] = {}
    stack = list(children.get(root_pid, []))
    while stack:
        pid = stack.pop()
        if pid in found or pid == observer_pid:
            continue
        found[pid] = table.get(pid, (0, ""))[1]
        stack.extend(children.get(pid, []))
    return found


def await_no_descendants(
    root_pid: int, budget_seconds: float = 20.0
) -> dict[int, str]:
    """Wait up to ``budget_seconds`` for this node's tree to drain.

    Returns whatever is *still* alive at the end. The wait exists for
    processes that are genuinely shutting down when the nested build
    returns (Gradle's single-use daemon closes its sockets before the
    launcher's exit is observable); it is bounded and its residue is
    reported, so nothing that actually outlives the node is hidden.
    """
    deadline = time.monotonic() + budget_seconds
    while True:
        # A detached Gradle daemon can exit between the wrapper returning and
        # this poll. Reap children only after procs.run has waited for its own
        # subprocess. A still-running descendant remains visible below.
        try:
            while os.waitpid(-1, os.WNOHANG)[0]:
                pass
        except ChildProcessError:
            pass
        lingering = live_descendants(root_pid)
        if not lingering or time.monotonic() >= deadline:
            return lingering
        time.sleep(0.5)


@node(SPEC)
def main(ctx):
    source_repo = Path(ctx.get("spec.workflow.repo", "sourceRepo") or "").resolve()
    probe_root = ctx.report_dir / "cleanup-failure-probe-test-graph"
    copy_probe_project(source_repo, probe_root)

    env = dict(os.environ)
    gradle_opts = env.get("GRADLE_OPTS", "")
    # `org.gradle.daemon=false` keeps the nested build off a reusable daemon.
    # `kotlin.compiler.execution.strategy=in-process` is the other half of the
    # same requirement and is NOT optional: the probe recopies the project on
    # every run, so the nested build always compiles `build-logic` from
    # scratch, and the Kotlin Gradle plugin's default `daemon` strategy forks
    # `KotlinCompileDaemon --daemon-autoshutdownIdleSeconds=7200`. That daemon
    # is a deliberately persistent user-scoped service, but it is spawned as a
    # descendant of this node's launcher, so it survives the node and the
    # executor's process-ownership contract correctly reports it as a leak
    # ("node launcher exited with live descendants"). Compiling in-process
    # keeps the nested toolchain inside the tree this node owns and can reap.
    env["GRADLE_OPTS"] = " ".join(
        part
        for part in (
            gradle_opts,
            "-Dorg.gradle.daemon=false",
            "-Dkotlin.compiler.execution.strategy=in-process",
        )
        if part
    )
    env["TLA_SPEC_DEV_SOURCE_REPO"] = str(source_repo)

    result = NodeResult.pass_(SPEC.id)
    if sys.platform == "linux":
        # Retain ownership when the nested Gradle wrapper detaches its JVM.
        # Otherwise the daemon is reparented outside this node, so the local
        # drain reports success while the executor still observes its PID.
        pr_set_child_subreaper = 36
        if ctypes.CDLL(None, use_errno=True).prctl(pr_set_child_subreaper, 1, 0, 0, 0):
            raise OSError(ctypes.get_errno(), "cannot adopt the probe's child processes")
    record = procs.run(
        ctx,
        "cleanup-failure-probe",
        [
            str(probe_root / "gradlew"),
            "--console=plain",
            # Command-line project properties propagate into included builds
            # (`build-logic`), which the GRADLE_OPTS system property alone does
            # not guarantee. Both channels are set on purpose.
            "-Pkotlin.compiler.execution.strategy=in-process",
            "cleanupFailureProbe",
        ],
        cwd=probe_root,
        env=env,
    )
    result.process(record).assertion("probe graph failed as expected", record.exit_code != 0)

    # This node owns everything the nested build started. Assert that here,
    # where the residue can be named, instead of letting the executor discover
    # it afterwards and report an opaque node error with bare PIDs.
    lingering = await_no_descendants(os.getpid())
    if lingering:
        residue = "; ".join(
            f"{pid}: {command[:200]}" for pid, command in sorted(lingering.items())
        )
        (ctx.report_dir / "node-logs").mkdir(parents=True, exist_ok=True)
        residue_log = ctx.report_dir / "node-logs" / f"{SPEC.id}.lingering-descendants.log"
        residue_log.write_text(residue + "\n", encoding="utf-8")
        result.artifact("cleanup-failure-probe-lingering-descendants", str(residue_log))
    result.assertion(
        "nested probe build left no live descendants", not lingering
    )

    run_dir = latest_probe_run(probe_root)
    summary_path = run_dir / "summary.json" if run_dir else None
    summary = json.loads(summary_path.read_text(encoding="utf-8")) if summary_path and summary_path.exists() else {}
    repo_node = node_by_id(summary, "spec.workflow.repo")
    failure_node = node_by_id(summary, "spec.workflow.force_failure")
    cleanup_node = node_by_id(summary, "spec.workflow.cleanup")
    repo_path = Path(repo_node.get("published", {}).get("repoPath") or "")

    if run_dir:
        result.artifact("cleanup-failure-probe-report", str(run_dir / "report.md"))
        result.artifact("cleanup-failure-probe-summary", str(run_dir / "summary.json"))

    return (
        result
        .assertion("probe report was written", bool(summary))
        .assertion("repo allocation node passed", repo_node.get("status") == "passed")
        .assertion("forced downstream failure was captured", failure_node.get("status") == "failed")
        .assertion("cleanup finalizer ran after failure", cleanup_node.get("status") == "passed")
        .assertion("allocated fixture repo removed after failure", bool(str(repo_path)) and not repo_path.exists())
        .artifact("cleanup-failure-probe-root", str(probe_root))
    )


if __name__ == "__main__":
    main()
