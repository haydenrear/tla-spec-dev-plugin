"""skt regress: scaffold, verdict and the episode handoff.

meta-harness is replaced by a stub binary that plays the agent: it reads
the episode request and writes whatever the test tells it to. What is
under test is everything around the agent -- above all that the verdict
comes from the graph reports and never from what the agent claims.
"""

import json
import os
import subprocess
import sys
import textwrap
import time
from pathlib import Path

import pytest

CLI = Path(__file__).resolve().parents[1] / "src" / "skt" / "cli.py"


def skt(repo: Path, *args: str, env: dict | None = None) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(CLI), "regress", *args], cwd=repo,
                          capture_output=True, text=True, env={**os.environ, **(env or {})})


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    root = tmp_path / "proj"
    (root / "test_graph").mkdir(parents=True)
    (root / "test_graph" / "keep").write_text("")
    runner = root / "skills" / "test-graph" / "scripts"
    runner.mkdir(parents=True)
    (runner / "run.py").write_text("")
    (runner / "discover.py").write_text("print('graph: alpha')\nprint('graph: beta')\n")
    git = ["git", "-c", "user.name=t", "-c", "user.email=t@t", "-C", str(root)]
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run([*git, "add", "-A"], check=True)
    subprocess.run([*git, "commit", "-qm", "init"], check=True)
    return root


def stub_harness(tmp_path: Path, behaviour: str) -> Path:
    """A fake `meta-harness`: `serve` idles, `episode` runs ``behaviour``.

    ``behaviour`` is Python with ``request`` (the episode request), ``brief``
    (its prompt), ``write_summary(graph, status, mode='full')`` and
    ``commit(relative_path, text)`` (a fix commit in the worktree) in scope.
    """
    path = tmp_path / "meta-harness"
    path.write_text("#!" + sys.executable + "\n" + textwrap.dedent("""
        import http.server, json, re, sys, time
        from pathlib import Path
        argv = sys.argv[1:]
        if "serve" in argv:
            port = int(argv[argv.index("--port") + 1])
            http.server.HTTPServer(("127.0.0.1", port), http.server.SimpleHTTPRequestHandler).serve_forever()
        request = json.loads(Path(argv[argv.index("--request") + 1]).read_text())
        brief = request["messages"][0]["content"]
        tg = re.search(r"Test graph project: (.+)", brief).group(1)
        agent_report = Path(re.search(r"nothing else, to:\\n  (.+)", brief).group(1))
        wt = request["workingDirectory"]
        def commit(rel, text):
            import subprocess
            (Path(wt) / rel).parent.mkdir(parents=True, exist_ok=True)
            (Path(wt) / rel).write_text(text)
            g = ["git", "-c", "user.name=t", "-c", "user.email=t@t", "-C", wt]
            time.sleep(1.1)  # commit times are whole seconds
            subprocess.run([*g, "add", "-A", rel], check=True)
            subprocess.run([*g, "commit", "-qm", "regress: fix"], check=True)
            time.sleep(1.1)
        counter = [0]
        def write_summary(graph, status, mode="full", age=0):
            counter[0] += 1
            d = Path(tg) / "build" / "validation-reports" / f"run-{counter[0]}"
            d.mkdir(parents=True)
            (d / "summary.json").write_text(json.dumps(
                {"runId": d.name, "status": status,
                 "execution": {"graphName": graph, "mode": mode, "complete": True}}))
            if age:
                import os
                os.utime(d / "summary.json", (time.time() - age, time.time() - age))
            time.sleep(0.02)
        def trace(*events):
            d = Path(argv[argv.index("--project-root") + 1]) / ".meta-harness" / "evidence" / "e-1"
            d.mkdir(parents=True, exist_ok=True)
            with open(d / "events.jsonl", "a") as f:
                for kind, data in events:
                    f.write(json.dumps({"kind": kind, "ts": "t", "data": data}) + chr(10))
        outcome = "succeeded"
    """) + textwrap.dedent(behaviour) + textwrap.dedent("""
        Path(argv[argv.index("--output") + 1]).write_text(json.dumps(
            {"outcome": outcome, "executionId": "e-1", "conversationId": "c-1"}))
    """))
    path.chmod(0o755)
    return path


def new(repo: Path, run_id: str = "r1") -> dict:
    proc = skt(repo, "new", "HEAD", "--id", run_id)
    assert proc.returncode == 0, proc.stderr
    state = Path(subprocess.run(["git", "-C", str(repo), "rev-parse", "--path-format=absolute",
                                 "--git-common-dir"], capture_output=True, text=True).stdout.strip())
    return json.loads((state / "skt-regress" / run_id / "run.json").read_text())


def test_new_makes_a_worktree_on_its_own_branch_outside_the_tree(repo):
    record = new(repo)
    worktree = Path(record["worktree"])
    assert worktree.is_dir() and worktree.parent == repo.parent
    head = subprocess.run(["git", "-C", str(worktree), "symbolic-ref", "--short", "HEAD"],
                          capture_output=True, text=True)
    assert head.stdout.strip() == "regress/r1" == record["branch"]
    assert subprocess.run(["git", "-C", str(repo), "status", "--porcelain"],
                          capture_output=True, text=True).stdout == ""


def test_new_refuses_an_unknown_ref_and_a_duplicate_id(repo):
    assert skt(repo, "new", "no-such-ref").returncode == 2
    new(repo)
    again = skt(repo, "new", "HEAD", "--id", "r1")
    assert again.returncode == 2 and "already exists" in again.stderr


def test_dry_run_writes_the_request_and_starts_nothing(repo):
    record = new(repo)
    proc = skt(repo, "run", "r1", "alpha", "--dry-run", "--model", "CLAUDE_x")
    assert proc.returncode == 0, proc.stderr
    request = json.loads((Path(record["state"]) / "attempt-1" / "request.json").read_text())
    assert request["model"] == "CLAUDE_x"
    assert request["workingDirectory"] == record["worktree"]
    assert "- alpha" in request["messages"][0]["content"]


def test_all_expands_through_discovery(repo):
    new(repo)
    proc = skt(repo, "run", "r1", "--all", "--dry-run")
    assert proc.returncode == 0 and "alpha, beta" in proc.stdout


def test_run_needs_graphs_or_all(repo):
    new(repo)
    assert skt(repo, "run", "r1").returncode == 2
    assert skt(repo, "run", "r1", "alpha", "--all").returncode == 2


def test_green_when_every_graph_report_passed(repo, tmp_path):
    new(repo)
    harness = stub_harness(tmp_path, """
        write_summary("alpha", "passed"); write_summary("beta", "passed")
        agent_report.write_text(json.dumps({"graphs": [{"graph": "alpha", "status": "passed"}]}))
    """)
    proc = skt(repo, "run", "r1", "alpha", "beta", "--meta-harness", str(harness), "--json")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert json.loads(proc.stdout)["verdict"] == "green"


def test_the_agent_cannot_talk_a_red_graph_green(repo, tmp_path):
    new(repo)
    harness = stub_harness(tmp_path, """
        write_summary("alpha", "failed")
        agent_report.write_text(json.dumps({"graphs": [{"graph": "alpha", "status": "passed"}]}))
    """)
    proc = skt(repo, "run", "r1", "alpha", "--meta-harness", str(harness), "--json")
    assert proc.returncode == 1
    assert json.loads(proc.stdout)["verdict"] == "red"


def test_a_graph_with_no_fresh_report_is_incomplete_not_green(repo, tmp_path):
    record = new(repo)
    stale = Path(record["test_graph_root"]) / "build" / "validation-reports" / "old"
    stale.mkdir(parents=True)
    (stale / "summary.json").write_text(json.dumps(
        {"runId": "old", "status": "passed", "execution": {"graphName": "beta", "mode": "full"}}))
    past = time.time() - 3600
    os.utime(stale / "summary.json", (past, past))
    harness = stub_harness(tmp_path, """
        write_summary("alpha", "passed")
        agent_report.write_text(json.dumps({"graphs": [{"graph": "beta", "status": "passed"}]}))
    """)
    proc = skt(repo, "run", "r1", "alpha", "beta", "--meta-harness", str(harness), "--json")
    assert proc.returncode == 3
    result = json.loads(proc.stdout)
    assert result["verdict"] == "incomplete"
    assert {g["graph"]: g["status"] for g in result["graphs"]} == {"alpha": "passed", "beta": "not_run"}


def test_a_resume_that_passes_is_green_and_says_it_was_a_resume(repo, tmp_path):
    new(repo)
    harness = stub_harness(tmp_path, """
        write_summary("alpha", "errored"); write_summary("alpha", "passed", mode="resume-from-node")
    """)
    proc = skt(repo, "run", "r1", "alpha", "--meta-harness", str(harness), "--json")
    assert proc.returncode == 0
    row = json.loads(proc.stdout)["graphs"][0]
    assert row["runs"] == 2 and row["via_resume"] is True


def test_a_failed_episode_with_no_reports_is_incomplete(repo, tmp_path):
    new(repo)
    harness = stub_harness(tmp_path, "outcome = 'failed'")
    proc = skt(repo, "run", "r1", "alpha", "--meta-harness", str(harness))
    assert proc.returncode == 3
    assert "failed: " in proc.stdout and "wrote no report" in proc.stdout


def test_close_removes_the_worktree_and_the_state(repo):
    record = new(repo)
    proc = skt(repo, "close", "r1")
    assert proc.returncode == 0, proc.stderr
    assert not Path(record["worktree"]).exists() and not Path(record["state"]).exists()
    assert "no regression worktrees" in skt(repo, "list").stdout


# ---- fix rights, isolation, escalation, attribution

ROW = {"graph": "alpha", "node": "n.one", "origin": "instrument", "area": "the fixture's port handling",
       "effect": "false red", "observed": "bind: address already in use", "fix": "abc123"}


def test_fix_is_refused_without_an_isolation_statement(repo):
    new(repo)
    proc = skt(repo, "run", "r1", "alpha", "--fix", "--dry-run")
    assert proc.returncode == 2 and "--isolated" in proc.stderr
    assert skt(repo, "run", "r1", "alpha", "--fix", "--isolated", "  ", "--dry-run").returncode == 2


def test_the_brief_changes_with_the_mode_and_the_env_reaches_the_agent(repo):
    record = new(repo)
    attempt = Path(record["state"])
    assert skt(repo, "run", "r1", "alpha", "--dry-run").returncode == 0
    report_only = (attempt / "attempt-1" / "brief.md").read_text()
    assert "YOU DO NOT FIX ANYTHING" in report_only and "ATTRIBUTION" in report_only
    proc = skt(repo, "run", "r1", "alpha", "--dry-run", "--fix", "--isolated", "k3d cluster regress-r1",
               "--env", "KUBECONFIG=/tmp/private")
    assert proc.returncode == 0, proc.stderr
    request = json.loads((attempt / "attempt-1" / "request.json").read_text())
    brief = request["messages"][0]["content"]
    assert "k3d cluster regress-r1" in brief and "STOP AND ESCALATE" in brief
    assert request["env"] == {"KUBECONFIG": "/tmp/private", "TEST_GRAPH_FEATURE_BRANCH": "regress-r1"}


def test_declared_effects_beyond_this_machine_are_named(repo):
    node = repo / "test_graph" / "sources" / "n.py"
    node.parent.mkdir()
    node.write_text('SPEC = NodeSpec("n").side_effects("fs:tmp", "net:external")\n')
    (repo / "skills" / "test-graph" / "scripts" / "discover.py").write_text(
        "print('graph: alpha')\nprint('  - test_graph/sources/n.py')\n")
    git = ["git", "-c", "user.name=t", "-c", "user.email=t@t", "-C", str(repo)]
    subprocess.run([*git, "add", "-A"], check=True)
    subprocess.run([*git, "commit", "-qm", "node"], check=True)
    new(repo)
    proc = skt(repo, "run", "r1", "alpha", "--dry-run", "--fix", "--isolated", "scratch")
    assert "beyond this machine: net:external" in proc.stderr
    assert "fs:tmp, net:external" in proc.stdout


def test_a_small_committed_fix_then_a_full_pass_is_green_and_carries_the_patch(repo, tmp_path):
    record = new(repo)
    harness = stub_harness(tmp_path, f"""
        write_summary("alpha", "failed")
        commit("test_graph/fixture.txt", "fixed\\n")
        write_summary("alpha", "passed")
        agent_report.write_text(json.dumps({{"graphs": [], "attribution": [{ROW!r}]}}))
    """)
    proc = skt(repo, "run", "r1", "alpha", "--fix", "--isolated", "local temp only",
               "--meta-harness", str(harness), "--json")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    result = json.loads(proc.stdout)
    assert result["verdict"] == "green" and result["attribution_gaps"] == []
    assert result["fixes"]["lines"] == 1 and len(result["fixes"]["commits"]) == 1
    assert "fixed" in Path(result["fixes"]["patch"]).read_text()
    assert "origin: \"instrument\"" in Path(result["attribution"]).read_text()
    # the fix branch outlives the worktree
    assert "kept (1 fix commit(s))" in skt(repo, "close", "r1").stdout
    assert subprocess.run(["git", "-C", str(repo), "rev-parse", "--verify", "-q", record["branch"]],
                          capture_output=True).returncode == 0


def test_a_pass_older_than_the_fix_or_only_a_resume_is_not_green(repo, tmp_path):
    new(repo)
    harness = stub_harness(tmp_path, """
        write_summary("alpha", "passed")
        commit("test_graph/fixture.txt", "fixed\\n")
        commit("test_graph/other.txt", "fixed\\n")
        write_summary("beta", "passed", mode="resume-from-node")
    """)
    proc = skt(repo, "run", "r1", "alpha", "beta", "--fix", "--isolated", "x",
               "--meta-harness", str(harness), "--json")
    assert proc.returncode == 3
    assert {g["status"] for g in json.loads(proc.stdout)["graphs"]} == {"needs_full_run"}


def test_a_fix_over_budget_is_escalated_even_when_the_graphs_are_green(repo, tmp_path):
    new(repo)
    harness = stub_harness(tmp_path, """
        commit("test_graph/big.txt", "x\\n" * 80)
        write_summary("alpha", "passed")
    """)
    proc = skt(repo, "run", "r1", "alpha", "--fix", "--isolated", "x",
               "--meta-harness", str(harness), "--json")
    assert proc.returncode == 4
    result = json.loads(proc.stdout)
    assert result["verdict"] == "escalated" and "80 changed lines" in result["over_budget"][0]


def test_a_change_in_a_report_only_run_is_escalated(repo, tmp_path):
    new(repo)
    harness = stub_harness(tmp_path, """
        commit("src/product.py", "x = 1\\n")
        write_summary("alpha", "passed")
    """)
    proc = skt(repo, "run", "r1", "alpha", "--meta-harness", str(harness), "--json")
    assert proc.returncode == 4
    result = json.loads(proc.stdout)
    assert result["fixes"]["outside_test_graph"] == ["src/product.py"]


def test_the_agents_escalation_ends_the_run_as_escalated(repo, tmp_path):
    new(repo)
    harness = stub_harness(tmp_path, f"""
        write_summary("alpha", "failed")
        agent_report.write_text(json.dumps({{"graphs": [], "attribution": [{ {**ROW, 'origin': 'product', 'fix': 'escalated'}!r}],
            "escalation": {{"graph": "alpha", "node": "n.one", "reason": "needs a schema change",
                           "needed": "add the field", "files": ["src/a.py"], "evidence": "KeyError"}}}}))
    """)
    proc = skt(repo, "run", "r1", "alpha", "beta", "--fix", "--isolated", "x",
               "--meta-harness", str(harness))
    assert proc.returncode == 4
    assert "ESCALATED" in proc.stdout and "needs a schema change" in proc.stdout
    assert "needed: add the field" in proc.stdout


def test_a_red_with_no_attribution_row_is_named_as_a_gap(repo, tmp_path):
    new(repo)
    harness = stub_harness(tmp_path, f"""
        write_summary("alpha", "errored"); write_summary("alpha", "passed")
        write_summary("beta", "failed")
        agent_report.write_text(json.dumps({{"graphs": [], "attribution": [{ {**ROW, 'graph': 'beta', 'area': ''}!r}]}}))
    """)
    proc = skt(repo, "run", "r1", "alpha", "beta", "--meta-harness", str(harness), "--json")
    assert proc.returncode == 1
    gaps = json.loads(proc.stdout)["attribution_gaps"]
    assert any("row 1 lacks: area" in g for g in gaps)
    assert any(g.startswith("alpha went red") for g in gaps)


# ---- found by review and by hand (REGRESS-REVIEW-*, REGRESS-MAN-* in the attribution record)

def test_an_untracked_file_is_a_change_and_close_will_not_delete_it(repo, tmp_path):
    record = new(repo)
    harness = stub_harness(tmp_path, """
        (Path(wt) / "src").mkdir(exist_ok=True)
        (Path(wt) / "src" / "new_product.py").write_text("x = 1\\n" * 100)
        write_summary("alpha", "passed")
    """)
    proc = skt(repo, "run", "r1", "alpha", "--meta-harness", str(harness), "--json")
    assert proc.returncode == 4, proc.stdout
    result = json.loads(proc.stdout)
    assert result["fixes"]["untracked"] == ["src/new_product.py"] and result["fixes"]["lines"] == 100
    refused = skt(repo, "close", "r1")
    assert refused.returncode == 2 and "src/new_product.py" in refused.stderr
    assert (Path(record["worktree"]) / "src" / "new_product.py").exists()


def test_a_rerun_is_not_blamed_for_the_previous_attempts_fix(repo, tmp_path):
    new(repo)
    first = stub_harness(tmp_path, """
        commit("test_graph/fixture.txt", "fixed\\n")
    """)
    assert skt(repo, "run", "r1", "alpha", "--fix", "--isolated", "x", "--meta-harness", str(first)).returncode == 3
    second = stub_harness(tmp_path, """
        write_summary("alpha", "passed")
    """)
    proc = skt(repo, "run", "r1", "alpha", "--meta-harness", str(second), "--json")
    assert proc.returncode == 0, proc.stdout
    result = json.loads(proc.stdout)
    assert result["attempt"] == 2 and result["over_budget"] == []
    assert len(result["fixes"]["commits"]) == 1  # the branch still carries attempt 1's fix


def test_a_stale_report_in_a_reused_attempt_directory_is_not_read(repo, tmp_path):
    record = new(repo)
    assert skt(repo, "run", "r1", "alpha", "--dry-run").returncode == 0
    (Path(record["state"]) / "attempt-1" / "agent-report.json").write_text(
        json.dumps({"graphs": [], "escalation": {"reason": "left over"}}))
    harness = stub_harness(tmp_path, 'write_summary("alpha", "passed")')
    proc = skt(repo, "run", "r1", "alpha", "--meta-harness", str(harness), "--json")
    assert proc.returncode == 0, proc.stdout
    assert json.loads(proc.stdout)["agent_report_problem"] == "the agent wrote no report"


def test_only_an_escalation_object_escalates(repo, tmp_path):
    new(repo)
    harness = stub_harness(tmp_path, """
        write_summary("alpha", "passed")
        agent_report.write_text(json.dumps({"graphs": [], "attribution": [], "escalation": "none"}))
    """)
    assert skt(repo, "run", "r1", "alpha", "--meta-harness", str(harness)).returncode == 0


def test_one_node_run_alone_is_not_a_pass(repo, tmp_path):
    new(repo)
    harness = stub_harness(tmp_path, """
        write_summary("alpha", "errored"); write_summary("alpha", "passed", mode="run-only-node")
    """)
    proc = skt(repo, "run", "r1", "alpha", "--meta-harness", str(harness), "--json")
    assert proc.returncode == 3
    assert json.loads(proc.stdout)["graphs"][0]["status"] == "needs_full_run"


def test_running_a_graph_more_often_than_the_limit_is_escalated(repo, tmp_path):
    new(repo)
    harness = stub_harness(tmp_path, """
        for _ in range(3): write_summary("alpha", "failed")
        write_summary("alpha", "passed")
    """)
    proc = skt(repo, "run", "r1", "alpha", "--fix", "--isolated", "x", "--max-runs", "3",
               "--meta-harness", str(harness), "--json")
    assert proc.returncode == 4
    assert "run 4 times" in json.loads(proc.stdout)["over_budget"][0]


def test_no_test_graph_project_is_one_line_not_a_traceback_or_a_red(repo):
    subprocess.run(["git", "-C", str(repo), "rm", "-rq", "test_graph"], check=True)
    subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", "-C", str(repo),
                    "commit", "-qm", "no graphs"], check=True)
    new(repo)
    proc = skt(repo, "run", "r1", "alpha", "--dry-run")
    assert proc.returncode == 2 and "Traceback" not in proc.stderr
    assert "no test graph project" in proc.stderr


def test_flags_may_come_before_or_between_the_positionals(repo):
    new(repo)
    proc = skt(repo, "run", "r1", "--fix", "--isolated", "x", "alpha", "--dry-run", "beta")
    assert proc.returncode == 0, proc.stderr
    assert "alpha, beta" in proc.stdout


def test_close_refuses_to_run_from_inside_its_own_worktree(repo):
    record = new(repo)
    proc = skt(Path(record["worktree"]), "close", "r1")
    assert proc.returncode == 2 and "inside the worktree" in proc.stderr
    assert Path(record["worktree"]).is_dir()


def test_declared_effects_reads_nested_calls_and_bare_names(tmp_path):
    sys.path.insert(0, str(CLI.parents[1]))
    from skt import regress
    node = tmp_path / "n.py"
    node.write_text('S.side_effects(SideEffect.environment("provision"), "net:external", "browser")\n')
    assert regress.declared_effects([str(node)]) == ["browser", "environment:provision", "net:external"]


def test_a_second_run_is_refused_while_an_unisolated_one_is_live(repo, tmp_path):
    harness = stub_harness(tmp_path, "write_summary('alpha', 'passed')")
    env = {"META_HARNESS_BIN": str(harness)}
    assert skt(repo, "new", "HEAD", "--id", "one").returncode == 0
    assert skt(repo, "new", "HEAD", "--id", "two").returncode == 0
    state = Path(subprocess.run(["git", "-C", str(repo), "rev-parse", "--path-format=absolute",
                                 "--git-common-dir"], capture_output=True, text=True).stdout.strip())
    marker = state / "skt-regress" / "one" / "running.json"
    marker.write_text(json.dumps({"id": "one", "pid": os.getpid(), "graphs": ["beta"], "isolated": None}))

    refused = skt(repo, "run", "two", "alpha", env=env)
    assert refused.returncode == 2, refused.stdout + refused.stderr
    assert "regress one is running" in refused.stderr
    same = skt(repo, "run", "one", "alpha", env=env)
    assert same.returncode == 2 and "already running" in same.stderr
    assert "RUNNING" in skt(repo, "list").stdout

    # Both isolated: they may overlap.
    marker.write_text(json.dumps({"id": "one", "pid": os.getpid(), "graphs": ["beta"],
                                  "isolated": "its own cluster"}))
    half = skt(repo, "run", "two", "alpha", env=env)
    assert half.returncode == 2, "an unisolated run must not join an isolated one"
    both = skt(repo, "run", "two", "alpha", "--isolated", "its own temp dir", env=env)
    assert both.returncode == 0, both.stdout + both.stderr

    # A marker whose process is gone is swept, not obeyed.
    marker.write_text(json.dumps({"id": "one", "pid": 2 ** 22 + 12345, "graphs": [], "isolated": None}))
    swept = skt(repo, "run", "two", "alpha", env=env)
    assert "is running" not in swept.stderr and swept.returncode != 2
    assert not marker.exists()
    assert not (state / "skt-regress" / "two" / "running.json").exists()


def test_an_agent_that_never_started_is_named_as_that(repo, tmp_path):
    harness = stub_harness(tmp_path, """
        # What a rejected credential really leaves: one empty closing message.
        trace(("execution.started", {}),
              ("agent.message.complete", {"content": [{"type": "text", "text": ""}]}),
              ("turn.ended", {"stop_reason": "error"}))
        outcome = "failed"
    """)
    assert skt(repo, "new", "HEAD", "--id", "auth").returncode == 0
    out = skt(repo, "run", "auth", "alpha", env={"META_HARNESS_BIN": str(harness)})
    assert out.returncode == 3, out.stdout + out.stderr
    assert "AGENT DID NOT START" in out.stdout and "log in" in out.stdout
    state = subprocess.run(["git", "-C", str(repo), "rev-parse", "--path-format=absolute",
                            "--git-common-dir"], capture_output=True, text=True).stdout.strip()
    result = json.loads((Path(state) / "skt-regress" / "auth" / "attempt-1" / "result.json").read_text())
    assert result["agent_started"] is False


def test_the_agent_keeps_its_credentials_but_not_the_parent_session(monkeypatch):
    sys.path.insert(0, str(CLI.parent))
    import regress
    monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", "t")
    monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", "s")
    monkeypatch.setenv("CLAUDECODE", "1")
    env = regress._agent_env()
    assert env.get("CLAUDE_CODE_OAUTH_TOKEN") == "t"
    assert "CLAUDE_CODE_SESSION_ID" not in env and "CLAUDECODE" not in env


def _result(repo: Path, run_id: str, attempt: int = 1) -> dict:
    state = subprocess.run(["git", "-C", str(repo), "rev-parse", "--path-format=absolute",
                            "--git-common-dir"], capture_output=True, text=True).stdout.strip()
    return json.loads((Path(state) / "skt-regress" / run_id / f"attempt-{attempt}" / "result.json").read_text())


def test_an_agent_that_ran_tools_and_then_hung_is_not_called_a_login_problem(repo, tmp_path):
    harness = stub_harness(tmp_path, """
        trace(("tool.call", {"name": "Bash"}), ("tool.call", {"name": "ScheduleWakeup"}),
              ("turn.ended", {"usage": {"session_total_tokens": 1234}}))
        outcome = "failed"
    """)
    assert skt(repo, "new", "HEAD", "--id", "hung").returncode == 0
    out = skt(repo, "run", "hung", "alpha", env={"META_HARNESS_BIN": str(harness)})
    assert out.returncode == 3, out.stdout + out.stderr
    assert "AGENT DID NOT START" not in out.stdout and "log in" not in out.stdout
    assert "AGENT STOPPED WITHOUT REPORTING" in out.stdout
    assert "WAIT TOOL USED  ScheduleWakeup" in out.stdout
    result = _result(repo, "hung")
    assert result["agent_started"] is True
    assert result["trace"]["tool_calls"] == 2 and result["trace"]["tokens"]["total_tokens"] == 1234


def test_without_a_trace_nothing_is_claimed_about_the_login(repo, tmp_path):
    harness = stub_harness(tmp_path, "outcome = 'failed'")
    assert skt(repo, "new", "HEAD", "--id", "blind").returncode == 0
    out = skt(repo, "run", "blind", "alpha", env={"META_HARNESS_BIN": str(harness)})
    assert out.returncode == 3
    assert "AGENT DID NOT START" not in out.stdout and "unknown" in out.stdout
    assert _result(repo, "blind")["agent_started"] is None


def test_a_silent_episode_is_stopped(repo, tmp_path):
    harness = stub_harness(tmp_path, "trace(('tool.call', {'name': 'Bash'})); time.sleep(60)")
    assert skt(repo, "new", "HEAD", "--id", "quiet").returncode == 0
    began = time.time()
    out = skt(repo, "run", "quiet", "alpha", "--stall-timeout", "3", env={"META_HARNESS_BIN": str(harness)})
    assert time.time() - began < 40
    assert out.returncode == 3, out.stdout + out.stderr
    assert "recorded nothing for" in out.stdout and "AGENT DID NOT START" not in out.stdout


def test_adopt_runs_in_an_existing_worktree_and_close_leaves_it(repo, tmp_path):
    ticket = tmp_path / "proj-TICKET-1"
    subprocess.run(["git", "-C", str(repo), "worktree", "add", "-q", "-b", "ticket-1", str(ticket)], check=True)
    (ticket / ".skill-manager").mkdir()            # setup that git does not track
    (repo / ".git" / "info").mkdir(exist_ok=True)
    (repo / ".git" / "info" / "exclude").write_text(".skill-manager/\n")
    harness = stub_harness(tmp_path, """
        assert (Path(wt) / ".skill-manager").is_dir()
        write_summary("alpha", "passed")
    """)
    adopted = skt(repo, "adopt", str(ticket), "--id", "t1")
    assert adopted.returncode == 0, adopted.stderr
    out = skt(repo, "run", "t1", "alpha", env={"META_HARNESS_BIN": str(harness)})
    assert out.returncode == 0, out.stdout + out.stderr
    assert skt(repo, "close", "t1").returncode == 0
    assert ticket.is_dir() and (ticket / ".skill-manager").is_dir()
    branches = subprocess.run(["git", "-C", str(repo), "branch", "--list", "ticket-1"],
                              capture_output=True, text=True).stdout
    assert "ticket-1" in branches

    (ticket / "scratch.txt").write_text("x")
    dirty = skt(repo, "adopt", str(ticket), "--id", "t2")
    assert dirty.returncode == 2 and "uncommitted" in dirty.stderr
    assert skt(repo, "adopt", str(tmp_path), "--id", "t3").returncode == 2


def test_the_graph_command_blocks_briefly_and_rejoins_the_same_run(tmp_path, monkeypatch):
    sys.path.insert(0, str(CLI.parent))
    import regress
    monkeypatch.setattr(regress, "GRAPH_WAIT", 3)
    runner = tmp_path / "run.py"
    runner.write_text("import sys, time\ntime.sleep(5)\nprint('ran', sys.argv[1:])\nsys.exit(7)\n")
    script = regress.write_graph_script(tmp_path, runner, str(tmp_path / "tg"))
    first = subprocess.run(["bash", str(script), "alpha"], capture_output=True, text=True)
    assert "STARTED alpha" in first.stdout and "STILL RUNNING alpha" in first.stdout
    second = subprocess.run(["bash", str(script), "alpha"], capture_output=True, text=True)
    assert "STARTED" not in second.stdout, "the second call must rejoin, not start another run"
    assert "FINISHED alpha  (runner exit 7," in second.stdout
    assert "--test-graph-root" in second.stdout
    third = subprocess.run(["bash", str(script), "alpha"], capture_output=True, text=True)
    assert "STARTED alpha" in third.stdout, "after FINISHED the same command is a new run"


def test_the_brief_forbids_setup_background_work_and_timers(repo, tmp_path):
    assert skt(repo, "new", "HEAD", "--id", "brief").returncode == 0
    assert skt(repo, "run", "brief", "alpha", "--dry-run").returncode == 0
    brief = Path(_result.__globals__["subprocess"].run(
        ["git", "-C", str(repo), "rev-parse", "--path-format=absolute", "--git-common-dir"],
        capture_output=True, text=True).stdout.strip()) / "skt-regress" / "brief" / "attempt-1" / "brief.md"
    text = brief.read_text()
    assert "graph.sh alpha" not in text and "graph.sh <graph>" in text
    assert "NO setup of any kind" in text and "NO background work and NO timers" in text
    assert "in the background and wait" not in text
    assert "run.py" not in text, "the agent is given the wrapper, never the runner"
