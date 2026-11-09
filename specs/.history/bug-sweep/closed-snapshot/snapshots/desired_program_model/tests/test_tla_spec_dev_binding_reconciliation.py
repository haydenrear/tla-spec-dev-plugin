"""CD-09 (coverage-audit run 2, gap G5): bindings equal the model's action set.

The audit found `case_adapters.toml` binding 11 of 14 model actions plus
`ValidateTestGraphCli`, which is not a model action -- a desync nothing
checked. These tests are that check: the binding label set must equal the
model's @command action set exactly, in both directions, and every binding
must resolve to a real adapter class whose `action_name` is its label.

`Stutter` is deliberately outside the reconciliation: it carries no @command
annotation (it is the stuttering frame condition, not an observable command),
and the complexity descriptor's action count (14) excludes it for the same
reason.
"""

from __future__ import annotations

import importlib.util
import re
from pathlib import Path

MODEL_DIR = Path(__file__).resolve().parents[1]


def model_actions() -> set[str]:
    """The @command-annotated action set of the TLA+ module."""
    text = (MODEL_DIR / "TlaSpecDevCli.tla").read_text(encoding="utf-8")
    return set(re.findall(r"^\\\* @command (\w+)", text, flags=re.MULTILINE))


def binding_labels() -> set[str]:
    text = (MODEL_DIR / "case_adapters.toml").read_text(encoding="utf-8")
    return set(re.findall(r"^\[adapters\.(\w+)\]", text, flags=re.MULTILINE))


def binding_targets() -> dict[str, str]:
    text = (MODEL_DIR / "case_adapters.toml").read_text(encoding="utf-8")
    targets: dict[str, str] = {}
    label = None
    for line in text.splitlines():
        header = re.match(r"^\[adapters\.(\w+)\]", line)
        if header:
            label = header.group(1)
            continue
        assignment = re.match(r'^adapter\s*=\s*"([^"]+)"', line)
        if assignment and label:
            targets[label] = assignment.group(1)
    return targets


def load_production_adapters():
    path = MODEL_DIR / "production_adapters.py"
    spec = importlib.util.spec_from_file_location("g5_production_adapters", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_model_has_the_expected_command_actions() -> None:
    """RC-01 added GenerateCases and CloseTicketWeakened; 2026-08-04 removed one.

    RC-01 (MF-026 G-6 and the owner's guard-weakening decision): GenerateCases
    -- case-module generation, this epic's flagship feature, which had no
    action, no port and no CLI subcommand at all -- and CloseTicketWeakened,
    the close taken around the precondition TLC proves over the whole state
    space.

    2026-08-04 (owner direction): AnalyzeArchitecture REMOVED with the static
    architecture scanners. The count going DOWN is the first time this figure
    has moved in that direction, and it is asserted here in both directions --
    the action is absent, and the total is asserted -- so a reinstatement is a
    deliberate edit rather than a silent one.

    CA-04 removed RunKillTest with the mutation kill test (RM-03-DF-05), taking
    the count 16 -> 15. That is the SECOND time this figure has gone down. The
    count was updated deliberately and both directions are still asserted: this
    test tracks the model's action set by construction, so an action removed
    from the model must leave it, and the removal is recorded here rather than
    absorbed silently.
    """
    actions = model_actions()
    assert len(actions) == 15, sorted(actions)
    assert "AnalyzeArchitecture" not in actions
    assert "RunKillTest" not in actions
    assert "GenerateCases" in actions
    assert "CloseTicketWeakened" in actions
    assert "Stutter" not in actions


def test_every_model_action_is_bound() -> None:
    missing = model_actions() - binding_labels()
    assert not missing, (
        f"model actions with no case_adapters.toml binding: {sorted(missing)} "
        "-- the audit's G5 desync, reintroduced"
    )


def test_every_binding_is_a_model_action() -> None:
    extra = binding_labels() - model_actions()
    assert not extra, (
        f"case_adapters.toml binds labels that are not model actions: {sorted(extra)} "
        "-- ValidateTestGraphCli was exactly this class of desync (G5)"
    )


def test_every_binding_resolves_to_a_real_adapter_with_matching_action_name() -> None:
    module = load_production_adapters()
    for label, target in binding_targets().items():
        module_name, _, class_name = target.partition(":")
        assert module_name == "production_adapters", (label, target)
        adapter_cls = getattr(module, class_name, None)
        assert adapter_cls is not None, f"{label}: {class_name} does not exist"
        assert getattr(adapter_cls, "action_name", None) == label, (
            f"{label}: bound adapter {class_name} declares "
            f"action_name={getattr(adapter_cls, 'action_name', None)!r}"
        )
        assert callable(getattr(adapter_cls, "run", None)) or callable(
            getattr(adapter_cls, "apply", None)
        ), f"{label}: {class_name} has neither run() nor apply()"
