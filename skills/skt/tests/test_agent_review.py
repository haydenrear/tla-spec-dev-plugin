import json
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from skt import cli, review


@pytest.mark.parametrize("response,status", [
    ('{"findings":[],"gaps":[]}', "clean"),
    ('{"findings":[{"location":"code:3","finding":"guard removed"}],"gaps":[]}', "findings"),
    ('{"findings":[],"gaps":["missing log"]}', "incomplete"),
])
def test_completed_review(response, status):
    assert review.report({"outcome": "succeeded", "response": response, "executionId": "e"}, [])["status"] == status


def test_failed_episode_cannot_issue_clean_verdict():
    with pytest.raises(ValueError):
        review.report({"outcome": "failed", "response": '{"findings":[],"gaps":[]}'}, [])


def test_review_pins_inputs_and_records_missing_evidence(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    subprocess.run(["git", "init", "-q"], check=True)
    subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "base", "--allow-empty"], check=True)
    def stub(binary, attempt, request, base_url, timeout, config, **options):
        assert request["allowTools"] == ["Read"]
        assert not (Path(request["workingDirectory"]) / ".git").exists()
        return {"outcome": "succeeded", "response": '{"findings":[],"gaps":[]}', "executionId": "e"}, "url"
    monkeypatch.setattr(review, "run_episode", stub)
    monkeypatch.setattr(review, "find_meta_harness", lambda _: "stub")
    args = ["agent", "run", "review", "--base", "HEAD", "--head", "HEAD", "--evidence", "missing"]
    assert cli.main(args) == 3
    first = json.loads(capsys.readouterr().out)
    assert first["base"] == first["head"] and first["gaps"] == ["Unavailable evidence: missing"]
    assert first["executionId"] == "e" and Path(first["artifact"]).is_file()
    assert cli.main(args) == 3
    assert json.loads(capsys.readouterr().out)["attempt"] != first["attempt"]
    assert not subprocess.check_output(["git", "status", "--porcelain"]).strip()


def test_plugin_can_register_another_role_with_its_own_result_reader(tmp_path, monkeypatch, capsys):
    import argparse
    from skt import agents, agent_config, episode
    harness = tmp_path / "fixture-harness"
    harness.write_text("#!" + sys.executable + """
import json, sys
from pathlib import Path
args = sys.argv[1:]
request = json.loads(Path(args[args.index("--request") + 1]).read_text())
response = request["messages"][0]["content"].upper()
Path(args[args.index("--output") + 1]).write_text(json.dumps(
    {"outcome":"succeeded","response":response,"executionId":"fixture-execution"}))
""")
    harness.chmod(0o700)
    def summarize(values, _):
        parser = argparse.ArgumentParser()
        agent_config.add_options(parser)
        parser.add_argument("text")
        parser.add_argument("--dry-run", action="store_true")
        args = parser.parse_args(values)
        plan = agent_config.resolve("summary", tmp_path, args, model_env="SKT_SUMMARY_MODEL")
        request = agent_config.request("fixture-1", args.text, tmp_path, plan)
        if args.dry_run:
            print(json.dumps(request))
            return 0
        result, _ = episode.run_episode(str(harness), tmp_path, request, "http://localhost:12345")
        print(result["response"])
        return 0
    monkeypatch.setitem(agents.ROLE_COMMANDS, "summary", summarize)
    monkeypatch.setenv("SKT_REVIEW_MODEL", "unrelated-review-model")
    assert cli.main(["agent", "list"]) == 0 and "summary" in capsys.readouterr().out
    assert cli.main(["agent", "run", "summary", "--dry-run", "hello"]) == 0
    assert json.loads(capsys.readouterr().out)["model"] == "CLAUDE_haiku"
    monkeypatch.setenv("SKT_SUMMARY_MODEL", "summary-model")
    assert cli.main(["agent", "run", "summary", "--dry-run", "hello"]) == 0
    assert json.loads(capsys.readouterr().out)["model"] == "summary-model"
    assert cli.main(["agent", "run", "summary", "hello"]) == 0
    assert capsys.readouterr().out.strip() == "HELLO"


def test_termination_cancels_caller_owned_episode(tmp_path):
    import os
    import signal
    import time
    harness = tmp_path / "fixture-client"
    harness.write_text("#!" + sys.executable + """
import os, signal, time
from pathlib import Path
def cancel(*args):
    Path("cancelled").touch()
    raise SystemExit(0)
signal.signal(signal.SIGTERM, cancel)
Path("started").write_text(str(os.getpid()))
time.sleep(30)
""")
    harness.chmod(0o700)
    code = """from pathlib import Path
from skt.episode import run_episode
run_episode(str(Path('fixture-client').resolve()),Path.cwd(),{'timeoutSeconds':30},'http://localhost:1')
"""
    owner = subprocess.Popen([sys.executable, "-c", code], cwd=tmp_path,
                             env={**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src")})
    try:
        for _ in range(100):
            if (tmp_path / "started").exists():
                break
            time.sleep(.05)
        assert (tmp_path / "started").exists()
        owner.send_signal(signal.SIGTERM)
        assert owner.wait(timeout=5) == 143 and (tmp_path / "cancelled").exists()
    finally:
        if owner.poll() is None:
            owner.kill()
            owner.wait()
