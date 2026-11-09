import importlib.util
from pathlib import Path


def load_adapters():
    path = Path(__file__).resolve().parents[1] / "production_adapters.py"
    spec = importlib.util.spec_from_file_location("ticket_cli_003_production_adapters", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_scaffold_project_and_workflow_adapters_use_cli(tmp_path: Path) -> None:
    adapters = load_adapters()

    project = adapters.ScaffoldProjectAdapter().apply(tmp_path, spec_root="project_specs", name="CliProject")
    workflow = adapters.ScaffoldWorkflowAdapter().apply(
        tmp_path,
        spec_root="project_specs",
        ticket_id="CLI-123",
        title="CLI scaffold ticket",
    )

    assert project["accepted"] is True, project["stderr"]
    assert workflow["accepted"] is True, workflow["stderr"]
    assert (tmp_path / "project_specs/program_model/Internal.tla").exists()
    assert (tmp_path / "project_specs/current/Internal.tla").exists()
    assert (tmp_path / "project_specs/desired_program_model/ticket_plan.yaml").exists()
