"""Spec-unit coverage for the RecordBudgets action.

Scaffolding must establish per-program budgets before any generation action:
the emitted manifest carries the documented defaults, and the scaffold output
tells the agent to negotiate them with the user.
"""

import importlib.util
import sys
from pathlib import Path


def load_adapters():
    path = Path(__file__).resolve().parents[1] / "production_adapters.py"
    spec = importlib.util.spec_from_file_location("mf012_production_adapters", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_budgets_module(adapters):
    sys.path.insert(0, str(adapters.repo_root()))
    from scripts import budgets

    return budgets


def test_record_budgets_adapter_emits_defaults_and_prompt(tmp_path: Path) -> None:
    adapters = load_adapters()
    budgets = load_budgets_module(adapters)

    result = adapters.RecordBudgetsAdapter().apply(tmp_path, spec_root="budget_specs", name="BudgetProg")

    assert result["accepted"] is True, result["stderr"]
    assert result["budgets_block_emitted"] is True
    assert result["defaults_match"] is True
    assert result["prompts_user"] is True
    assert result["budgets"] == budgets.DEFAULT_BUDGETS


def test_scaffold_workflow_also_emits_budgets(tmp_path: Path) -> None:
    adapters = load_adapters()
    budgets = load_budgets_module(adapters)

    adapters.ScaffoldProjectAdapter().apply(tmp_path, spec_root="budget_specs", name="BudgetProg")
    workflow = adapters.ScaffoldWorkflowAdapter().apply(
        tmp_path,
        spec_root="budget_specs",
        ticket_id="BUD-1",
        title="Budget ticket",
    )

    assert workflow["accepted"] is True, workflow["stderr"]
    for manifest in (
        tmp_path / "budget_specs/current/spec_manifest.yaml",
        tmp_path / "budget_specs/desired_program_model/spec_manifest.yaml",
    ):
        assert "budgets:" in manifest.read_text(), manifest
        assert budgets.load_budgets(manifest, warn=False) == budgets.DEFAULT_BUDGETS


def test_missing_budgets_block_falls_back_with_warning(tmp_path: Path, capsys) -> None:
    adapters = load_adapters()
    budgets = load_budgets_module(adapters)

    manifest = tmp_path / "spec_manifest.yaml"
    manifest.write_text("module: NoBudgets\n")

    loaded = budgets.load_budgets(manifest)
    warning = capsys.readouterr().err

    assert loaded == budgets.DEFAULT_BUDGETS
    assert "no budgets block" in warning
