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
    assert review.report({"outcome": "succeeded", "response": response}, [])["status"] == status


def test_failed_episode_cannot_issue_clean_verdict():
    with pytest.raises(ValueError):
        review.report({"outcome": "failed", "response": '{"findings":[],"gaps":[]}'}, [])


def test_review_pins_inputs_and_records_missing_evidence(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    subprocess.run(["git", "init", "-q"], check=True)
    subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "base", "--allow-empty"], check=True)
    def stub(binary, attempt, request, base_url, timeout, config):
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
