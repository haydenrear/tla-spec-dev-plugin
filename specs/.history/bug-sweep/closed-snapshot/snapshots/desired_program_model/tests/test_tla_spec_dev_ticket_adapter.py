import importlib.util
from pathlib import Path


def load_adapters():
    path = Path(__file__).resolve().parents[1] / "production_adapters.py"
    spec = importlib.util.spec_from_file_location("ticket_cli_004_production_adapters", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_open_ticket_adapter_drives_cli_ticket_workspace(tmp_path: Path) -> None:
    adapters = load_adapters()
    result = adapters.OpenTicketAdapter().apply(tmp_path, spec_root="project_specs", ticket_id="CLI-124")

    assert result["accepted"] is True
    assert result["exit_code"] == 0
    assert str(result["ticket_dir"]).endswith("project_specs/tickets/CLI-124")


def test_close_ticket_adapter_drives_cli_history_promotion(tmp_path: Path) -> None:
    adapters = load_adapters()
    result = adapters.CloseTicketAdapter().apply(tmp_path, spec_root="project_specs", ticket_id="CLI-125")

    assert result["accepted"] is True
    assert result["exit_code"] == 0
    assert str(result["history_dir"]).endswith("project_specs/.history/desired-ticket-workflow/ticket-000-CLI-125")
