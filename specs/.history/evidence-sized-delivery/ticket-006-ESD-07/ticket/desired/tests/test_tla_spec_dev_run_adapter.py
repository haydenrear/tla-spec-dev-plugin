import importlib.util
from pathlib import Path


def load_adapters():
    path = Path(__file__).resolve().parents[1] / "production_adapters.py"
    spec = importlib.util.spec_from_file_location("ticket_cli_005_production_adapters", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_run_spec_unit_tests_adapter_drives_cli_validation(tmp_path: Path) -> None:
    adapters = load_adapters()
    result = adapters.RunSpecUnitTestsAdapter().apply(tmp_path, spec_root="project_specs", ticket_id="CLI-126")

    assert result["accepted"] is True
    assert result["exit_code"] == 0
    assert str(result["ticket_current"]).endswith("project_specs/tickets/CLI-126/current")
