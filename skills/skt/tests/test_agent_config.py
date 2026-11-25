from argparse import Namespace
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from skt.agent_config import resolve
from skt.episode import AgentError


def test_roles_and_invocation_override(tmp_path, monkeypatch):
    (tmp_path / "skt-agents.toml").write_text(
        '[roles]\nreview="fast"\n[profiles.fast]\nmodel="CUSTOM_fast"\ntransport="http"\n')
    monkeypatch.setenv("SKT_REVIEW_MODEL", "environment")
    assert resolve("review", tmp_path, Namespace(profile=None, model="once"))["settings"]["model"] == "once"
    plan = resolve("review", tmp_path, Namespace(profile=None))
    assert plan["settings"]["model"] == "CUSTOM_fast" and plan["sources"]["model"] == "profile fast"
    with pytest.raises(AgentError, match="shell"):
        resolve("regress", tmp_path, Namespace(profile="fast"))
    with pytest.raises(AgentError, match="unknown profile"):
        resolve("review", tmp_path, Namespace(profile="missing"))
    with pytest.raises(AgentError, match="embedded credentials"):
        resolve("review", tmp_path, Namespace(profile=None, base_url="http://secret@localhost"))
