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
        args = parser.parse_args(values)
        plan = agent_config.resolve("summary", tmp_path, args)
        request = agent_config.request("fixture-1", args.text, tmp_path, plan)
        result, _ = episode.run_episode(str(harness), tmp_path, request, "http://localhost:12345")
        print(result["response"])
        return 0
    monkeypatch.setitem(agents.ROLE_COMMANDS, "summary", summarize)
    assert cli.main(["agent", "list"]) == 0 and "summary" in capsys.readouterr().out
    assert cli.main(["agent", "run", "summary", "hello"]) == 0
    assert capsys.readouterr().out.strip() == "HELLO"
