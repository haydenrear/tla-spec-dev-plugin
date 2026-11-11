"""MF-032: spec-unit coverage for the adapters given run() by this ticket.

Each of the four newly case-executing adapters -- InstallLocalCli (trivial),
ScaffoldWorkflow, RecordBudgets and OpenTicket (moderate) -- is driven through
its real run() against a model-shaped case (the before/after shape the TLC
corpus emits). materialize_before drives the real CLI, the action runs, and the
projection is compared field by field.

Every adapter carries a NEGATIVE CONTROL proven to FAIL: a check that cannot
fail is not a check (MF-029's structural hazard). Each control derives its
expected value from the before-state and the transition, never from the field
being checked, and corrupts the model's after-state so the projection -- which
is read from the real filesystem -- disagrees.
"""
import copy
import dataclasses
import importlib.util
from pathlib import Path

import pytest


def load_adapters():
    path = Path(__file__).resolve().parents[1] / "production_adapters.py"
    spec = importlib.util.spec_from_file_location("mf032_production_adapters", path)
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


def _state(setup_phase: int, spec_root: str, ticket_state: dict, last: str, nxt: str):
    return {
        "complexity_gate": "unknown",
        "corpus_gate": "unknown",
        "effect_conformance": "unknown",
        "lastCommand": last,
        "result": {"accepted": True, "next": nxt, "reason": "NoReason"},
        "setup_phase": setup_phase,
        "spec_root": spec_root,
        "ticket_state": ticket_state,
    }


def _corrupt(case: _Case, mutate) -> _Case:
    after = copy.deepcopy(case.after)
    mutate(after)
    return dataclasses.replace(case, after=after)


def install_case() -> _Case:
    before = _state(1, "NoRoot", {"cli_entrypoint": 0}, "BuildSkillCli", "tla-spec-dev scaffold project")
    after = _state(2, "NoRoot", {"cli_entrypoint": 0}, "InstallLocalCli", "tla-spec-dev scaffold project")
    return _Case("case_install_local_cli", before, after, _Input("InstallLocalCli", {}))


def scaffold_workflow_case() -> _Case:
    before = _state(4, "default_specs", {"cli_entrypoint": 0}, "RecordBudgets", "tla-spec-dev scaffold workflow")
    after = _state(5, "default_specs", {"cli_entrypoint": 0}, "tla-spec-dev scaffold workflow", "tla-spec-dev open ticket <ticket>")
    return _Case("case_scaffold_workflow", before, after, _Input("ScaffoldWorkflow", {}))


def record_budgets_case() -> _Case:
    before = _state(3, "default_specs", {"cli_entrypoint": 0}, "tla-spec-dev scaffold project", "RecordBudgets")
    after = _state(4, "default_specs", {"cli_entrypoint": 0}, "RecordBudgets", "tla-spec-dev scaffold workflow")
    return _Case("case_record_budgets", before, after, _Input("RecordBudgets", {}))


def open_ticket_case() -> _Case:
    before = _state(5, "default_specs", {"cli_entrypoint": 0}, "tla-spec-dev scaffold workflow", "tla-spec-dev open ticket <ticket>")
    after = _state(5, "default_specs", {"cli_entrypoint": 1}, "tla-spec-dev open ticket", "Update ticket desired TLA+ first")
    return _Case("case_open_ticket", before, after, _Input("OpenTicket", {}))


# --------------------------------------------------------------------------
# InstallLocalCli -- TRIVIAL band
# --------------------------------------------------------------------------
def test_install_local_cli_executes_case_end_to_end(tmp_path: Path) -> None:
    pa = load_adapters()
    adapter = pa.InstallLocalCliAdapter()
    case = install_case()
    accepted, reason = adapter.can_run(case)
    assert accepted, reason
    result = adapter.run(case, work_dir=tmp_path)
    comp = result["semantic_output"]["comparison"]
    assert comp["conformant"], comp["disagreements"]
    assert result["semantic_output"]["projected"]["setup_phase"] == 2


def test_install_local_cli_negative_control_wrong_phase_fails(tmp_path: Path) -> None:
    pa = load_adapters()
    adapter = pa.InstallLocalCliAdapter()
    bad = _corrupt(install_case(), lambda a: a.__setitem__("setup_phase", 3))
    with pytest.raises(AssertionError):
        adapter.run(bad, work_dir=tmp_path)


# --------------------------------------------------------------------------
# ScaffoldWorkflow -- MODERATE band
# --------------------------------------------------------------------------
def test_scaffold_workflow_executes_case_end_to_end(tmp_path: Path) -> None:
    pa = load_adapters()
    adapter = pa.ScaffoldWorkflowAdapter()
    case = scaffold_workflow_case()
    assert adapter.can_run(case)[0]
    result = adapter.run(case, work_dir=tmp_path)
    comp = result["semantic_output"]["comparison"]
    assert comp["conformant"], comp["disagreements"]
    assert result["semantic_output"]["projected"]["setup_phase"] == 5


def test_scaffold_workflow_negative_control_wrong_phase_fails(tmp_path: Path) -> None:
    pa = load_adapters()
    adapter = pa.ScaffoldWorkflowAdapter()
    bad = _corrupt(scaffold_workflow_case(), lambda a: a.__setitem__("setup_phase", 4))
    with pytest.raises(AssertionError):
        adapter.run(bad, work_dir=tmp_path)


# --------------------------------------------------------------------------
# RecordBudgets -- MODERATE band (no CLI command corresponds to the transition)
# --------------------------------------------------------------------------
def test_record_budgets_executes_case_end_to_end(tmp_path: Path) -> None:
    pa = load_adapters()
    adapter = pa.RecordBudgetsAdapter()
    case = record_budgets_case()
    assert adapter.can_run(case)[0]
    result = adapter.run(case, work_dir=tmp_path)
    comp = result["semantic_output"]["comparison"]
    assert comp["conformant"], comp["disagreements"]
    assert result["semantic_output"]["projected"]["setup_phase"] == 4


def test_record_budgets_negative_control_wrong_last_command_fails(tmp_path: Path) -> None:
    pa = load_adapters()
    adapter = pa.RecordBudgetsAdapter()
    bad = _corrupt(record_budgets_case(), lambda a: a.__setitem__("lastCommand", "WrongCommand"))
    with pytest.raises(AssertionError):
        adapter.run(bad, work_dir=tmp_path)


# --------------------------------------------------------------------------
# OpenTicket -- MODERATE band (first setup adapter advancing ticket_state)
# --------------------------------------------------------------------------
def test_open_ticket_executes_case_end_to_end(tmp_path: Path) -> None:
    pa = load_adapters()
    adapter = pa.OpenTicketAdapter()
    case = open_ticket_case()
    accepted, reason = adapter.can_run(case)
    assert accepted, reason
    result = adapter.run(case, work_dir=tmp_path)
    comp = result["semantic_output"]["comparison"]
    assert comp["conformant"], comp["disagreements"]
    assert result["semantic_output"]["ticket"] == "cli_entrypoint"
    assert result["semantic_output"]["projected"]["ticket_state"] == {"cli_entrypoint": 1}


def test_open_ticket_negative_control_wrong_ticket_state_fails(tmp_path: Path) -> None:
    pa = load_adapters()
    adapter = pa.OpenTicketAdapter()
    # Claim the ticket jumped to DesiredReady(2); the adapter observes Opened(1).
    bad = _corrupt(open_ticket_case(), lambda a: a["ticket_state"].__setitem__("cli_entrypoint", 2))
    with pytest.raises(AssertionError):
        adapter.run(bad, work_dir=tmp_path)


def test_open_ticket_can_run_rejects_already_open(tmp_path: Path) -> None:
    pa = load_adapters()
    adapter = pa.OpenTicketAdapter()
    # A ticket already Opened(1) in the before-state is not enabled for
    # OpenTicket. Keep exactly one changed ticket_state index (1 -> 2) so the
    # except-index recovery succeeds and the stage guard is what rejects it.
    case = open_ticket_case()
    before = copy.deepcopy(case.before)
    before["ticket_state"] = {"cli_entrypoint": 1}
    after = copy.deepcopy(case.after)
    after["ticket_state"] = {"cli_entrypoint": 2}
    case = dataclasses.replace(case, before=before, after=after)
    accepted, reason = adapter.can_run(case)
    assert not accepted
    assert "Unopened" in reason
