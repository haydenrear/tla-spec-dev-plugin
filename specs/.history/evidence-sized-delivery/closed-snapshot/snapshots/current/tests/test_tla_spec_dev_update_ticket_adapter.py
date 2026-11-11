"""MF-031: spec-unit coverage for the two new ticket-segment adapters.

Drives each adapter's run() against a synthetic-but-model-shaped case (the same
before/after shape the TLC corpus emits) end to end -- materialize_before drives
the real CLI -- and proves each adapter's negative control FAILS. A check that
cannot fail is not a check (MF-029's structural hazard).
"""
import copy
import dataclasses
import importlib.util
from pathlib import Path

import pytest


def load_adapters():
    path = Path(__file__).resolve().parents[1] / "production_adapters.py"
    spec = importlib.util.spec_from_file_location("mf031_production_adapters", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@dataclasses.dataclass(frozen=True)
class _Input:
    action: str
    params: dict


@dataclasses.dataclass(frozen=True)
class _Case:
    name: str
    before: dict
    after: dict
    input: _Input


def _base_state(ticket_stage: int):
    return {
        "complexity_gate": "unknown",
        "corpus_gate": "unknown",
        "effect_conformance": "unknown",
        "lastCommand": "tla-spec-dev open ticket",
        "result": {"accepted": True, "next": "next", "reason": "NoReason"},
        "setup_phase": 5,
        "spec_root": "default_specs",
        "ticket_state": {"cli_entrypoint": ticket_stage},
    }


def desired_case() -> _Case:
    before = _base_state(1)
    after = copy.deepcopy(before)
    after["ticket_state"] = {"cli_entrypoint": 2}
    after["lastCommand"] = "UpdateTicketDesired"
    after["result"] = {"accepted": True, "next": "Implement ticket and update current", "reason": "NoReason"}
    return _Case("case_desired", before, after, _Input("UpdateTicketDesired", {"ticket": "cli_entrypoint"}))


def current_case() -> _Case:
    before = _base_state(2)
    before["lastCommand"] = "UpdateTicketDesired"
    after = copy.deepcopy(before)
    after["ticket_state"] = {"cli_entrypoint": 3}
    after["lastCommand"] = "UpdateTicketCurrent"
    after["result"] = {"accepted": True, "next": "tla-spec-dev run spec-unit-tests", "reason": "NoReason"}
    return _Case("case_current", before, after, _Input("UpdateTicketCurrent", {"ticket": "cli_entrypoint"}))


def _corrupt(case: _Case, mutate) -> _Case:
    after = copy.deepcopy(case.after)
    mutate(after)
    return dataclasses.replace(case, after=after)


def test_update_ticket_desired_executes_case_end_to_end(tmp_path: Path) -> None:
    pa = load_adapters()
    adapter = pa.UpdateTicketDesiredAdapter()
    case = desired_case()
    accepted, reason = adapter.can_run(case)
    assert accepted, reason
    result = adapter.run(case, work_dir=tmp_path)
    comp = result["semantic_output"]["comparison"]
    assert comp["conformant"], comp["disagreements"]
    assert result["semantic_output"]["ticket"] == "cli_entrypoint"
    assert result["semantic_output"]["projected"]["ticket_state"] == {"cli_entrypoint": 2}
    assert "ticket_state" in comp["agreements"]


def test_update_ticket_current_executes_case_end_to_end(tmp_path: Path) -> None:
    pa = load_adapters()
    adapter = pa.UpdateTicketCurrentAdapter()
    case = current_case()
    assert adapter.can_run(case)[0]
    result = adapter.run(case, work_dir=tmp_path)
    comp = result["semantic_output"]["comparison"]
    assert comp["conformant"], comp["disagreements"]
    assert result["semantic_output"]["projected"]["ticket_state"] == {"cli_entrypoint": 3}


def test_desired_negative_control_wrong_value_fails(tmp_path: Path) -> None:
    pa = load_adapters()
    adapter = pa.UpdateTicketDesiredAdapter()
    # Claim the ticket jumped to CURRENT_READY(3); the adapter observes 2.
    bad = _corrupt(desired_case(), lambda a: a["ticket_state"].__setitem__("cli_entrypoint", 3))
    with pytest.raises(AssertionError):
        adapter.run(bad, work_dir=tmp_path)


def test_desired_negative_control_wrong_last_command_fails(tmp_path: Path) -> None:
    pa = load_adapters()
    adapter = pa.UpdateTicketDesiredAdapter()
    bad = _corrupt(desired_case(), lambda a: a.__setitem__("lastCommand", "WrongCommand"))
    with pytest.raises(AssertionError):
        adapter.run(bad, work_dir=tmp_path)


def test_current_negative_control_wrong_value_fails(tmp_path: Path) -> None:
    pa = load_adapters()
    adapter = pa.UpdateTicketCurrentAdapter()
    bad = _corrupt(current_case(), lambda a: a["ticket_state"].__setitem__("cli_entrypoint", 2))
    # after==before for ticket_state -> the argument is not recoverable, which is
    # itself a refusal: the check cannot be satisfied by a non-transition.
    with pytest.raises((AssertionError, pa.BeforeStateUnreachable)):
        adapter.run(bad, work_dir=tmp_path)


def test_can_run_rejects_wrong_stage(tmp_path: Path) -> None:
    pa = load_adapters()
    adapter = pa.UpdateTicketDesiredAdapter()
    # A ticket already at DesiredReady(2) is not enabled for UpdateTicketDesired.
    case = current_case()
    case = dataclasses.replace(case, input=_Input("UpdateTicketDesired", {"ticket": "cli_entrypoint"}))
    accepted, reason = adapter.can_run(case)
    assert not accepted
    assert "enabled only" in reason
