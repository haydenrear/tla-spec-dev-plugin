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


def test_mislabeled_model_cannot_turn_off_review_tools(tmp_path):
    from skt.episode import AgentError, check_route
    provider = tmp_path / "fixture"
    provider.write_text('#!/bin/sh\necho \'[{"model_prefix":"CUSTOM_", "transport":{"kind":"acp_stdio"}}]\'\n')
    provider.chmod(0o700)
    with pytest.raises(AgentError, match="routes to acp_stdio"):
        check_route(str(provider), tmp_path, None, "CUSTOM_review", "http")
